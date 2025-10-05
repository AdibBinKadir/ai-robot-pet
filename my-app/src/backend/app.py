#!/usr/bin/env python3
"""
UNIFIED FLASK BACKEND SERVER
Combines image upload functionality and robot command processing
Serves as the main API gateway connecting React frontend to Supabase database
"""

import os
import json
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from supabase import create_client
from storage3.exceptions import StorageApiError
from dotenv import load_dotenv

# Import robot processing modules
from main_processor import MainRobotProcessor

# Load environment variables
load_dotenv()

app = Flask(__name__)

# CORS Configuration
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',') if o.strip()]
CORS(app, resources={
    r"/api/*": {"origins": ALLOWED_ORIGINS}, 
    r"/images": {"origins": ALLOWED_ORIGINS}
}, supports_credentials=True)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm', 'm4a', 'flac', 'jpg', 'jpeg', 'png', 'gif', 'bmp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
BUCKET = os.environ.get('BUCKET_NAME', 'images')
SAVE_PHOTO_METADATA = os.environ.get('SAVE_PHOTO_METADATA', 'false').lower() in ('1', 'true', 'yes')

# Initialize Supabase client
supabase = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("✅ Supabase connected successfully")
        print(f"🔗 Database URL: {SUPABASE_URL}")
        
        # Test database connection with existing tables
        try:
            test_query = supabase.table('photos').select('count').execute()
            print("✅ Database tables accessible")
        except Exception as test_e:
            print(f"⚠️ Database tables not accessible: {test_e}")
            
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        supabase = None
else:
    print("⚠️ Supabase configuration missing")
    print(f"   SUPABASE_URL: {'✅ Set' if SUPABASE_URL else '❌ Missing'}")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ Set' if SUPABASE_SERVICE_ROLE_KEY else '❌ Missing'}")

# Initialize Robot AI Processor
try:
    processor = MainRobotProcessor()
    print("🤖 Robot AI Processor initialized")
except Exception as e:
    print(f"❌ Robot AI Processor failed to initialize: {e}")
    processor = None

# Command history for in-memory storage (fallback)
command_history = []

# Pi configuration
PI_SERVER_URL = os.environ.get('PI_SERVER_URL', "http://192.168.1.100:8080")

@app.after_request
def add_cors_headers(response):
    """Ensure CORS headers on all responses"""
    origin = request.headers.get('Origin')
    if origin and origin in ALLOWED_ORIGINS:
        response.headers.setdefault('Access-Control-Allow-Origin', origin)
        response.headers.setdefault('Access-Control-Allow-Credentials', 'true')
    else:
        response.headers.setdefault('Access-Control-Allow-Origin', '*')
    response.headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
    response.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, x-user-id')
    response.headers.setdefault('Access-Control-Max-Age', '3600')
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler with CORS support"""
    app.logger.exception('Unhandled exception: %s', e)
    resp = jsonify({'error': 'internal server error', 'detail': str(e)})
    resp.status_code = 500
    return resp

def allowed_file(filename, file_type='audio'):
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if file_type == 'audio':
        return extension in {'wav', 'mp3', 'ogg', 'webm', 'm4a', 'flac'}
    elif file_type == 'image':
        return extension in {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
    
    return extension in ALLOWED_EXTENSIONS

# ======================
# IMAGE UPLOAD ENDPOINTS
# ======================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'supabase': 'connected' if supabase else 'disconnected',
        'robot_ai': 'ready' if processor else 'error'
    })

@app.route('/images', methods=['OPTIONS'])
def images_options():
    """Preflight response for image upload"""
    resp = jsonify({'ok': True})
    resp.status_code = 204
    return resp

@app.route('/images', methods=['POST'])
def upload_images():
    """Upload images to Supabase storage"""
    if supabase is None:
        return jsonify({'error': 'Server not configured: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing'}), 500
    
    user_id = request.headers.get('x-user-id') or 'anonymous'
    
    # Accept files under either "images" or "photos"
    files = []
    for key in ('images', 'photos'):
        found = request.files.getlist(key) or []
        files.extend(found)
    
    # Filter out empty entries and require a filename
    files = [f for f in files if f and getattr(f, 'filename', None) and allowed_file(f.filename, 'image')]
    
    if not files:
        return jsonify({'error': 'no valid image files uploaded', 'hint': 'send multipart files under form key "images" or "photos"'}), 400
    
    # Limit to first 3 files
    files = files[:3]
    app.logger.info("Received %d image file(s) for user=%s", len(files), user_id)
    
    uploaded_urls = []
    for f in files:
        ext = os.path.splitext(f.filename)[1] or ''
        key = f"{user_id}/images/{uuid.uuid4().hex}{ext}"
        data = f.read()
        
        try:
            res = supabase.storage.from_(BUCKET).upload(key, data, {'content-type': f.content_type})
            
            # Get public URL
            public = supabase.storage.from_(BUCKET).get_public_url(key)
            url = public.get('publicURL') if isinstance(public, dict) else public
            uploaded_urls.append(url)
            
            # Save metadata to database if enabled
            if SAVE_PHOTO_METADATA:
                try:
                    resp = supabase.table('photos').insert({
                        'user_id': user_id, 
                        'url': url,
                        'filename': f.filename,
                        'upload_time': datetime.now().isoformat()
                    }).execute()
                except Exception as e:
                    app.logger.exception('DB insert failed: %s', e)
                    
        except StorageApiError as e:
            app.logger.exception('Storage upload failed: %s', e)
            return jsonify({'error': 'storage_upload_failed', 'detail': str(e)}), 500
        except Exception as e:
            app.logger.exception('Unexpected error during storage upload: %s', e)
            return jsonify({'error': 'unexpected_storage_error', 'detail': str(e)}), 500

    return jsonify({'uploaded': uploaded_urls}), 200

# =========================
# ROBOT COMMAND ENDPOINTS
# =========================

@app.route('/')
def index():
    """Serve basic status page"""
    return jsonify({
        'service': 'AI Robot Pet Backend',
        'status': 'running',
        'endpoints': {
            'images': '/images',
            'microphone': '/microphone',
            'audio_commands': '/api/upload-audio',
            'command_history': '/api/history',
            'health': '/health'
        }
    })

@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    """Upload and process audio file for robot commands"""
    if processor is None:
        return jsonify({'success': False, 'error': 'Robot AI processor not available'}), 500
    
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename, 'audio'):
            return jsonify({'success': False, 'error': f'Invalid audio file type'}), 400
        
        # Get user info
        user_id = request.headers.get('x-user-id') or 'anonymous'
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process through AI
        try:
            result = processor.process_audio_command(file_path)
        except Exception as e:
            print(f"❌ AI processing failed: {e}")
            # Fallback response for testing
            result = {
                'success': True,
                'transcription': '[Audio received - AI processing unavailable]',
                'action_number': 0,
                'voice_response': 'Audio received successfully, but AI processing is currently unavailable.',
                'command_type': 'conversation',
                'timestamp': datetime.now().isoformat(),
                'audio_file': file_path
            }
        
        if result['success']:
            # Create command entry
            command_id = str(uuid.uuid4())
            command_entry = {
                'id': command_id,
                'user_id': user_id,
                'action_number': result['action_number'],
                'voice_response': result['voice_response'],
                'command_type': result['command_type'],
                'timestamp': result['timestamp'],
                'transcription': result['transcription'],
                'status': 'pending'
            }

            # Save to in-memory storage (robot_commands table not created yet)
            print(f"✅ Command processed and saved to memory: {command_id}")
            command_history.append(command_entry.copy())

            # Clean up uploaded file
            try:
                os.remove(file_path)
            except:
                pass

            return jsonify({
                'success': True,
                'result': result,
                'command_id': command_id
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Processing failed')}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_command_history():
    """Get command history from database or fallback"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        limit = request.args.get('limit', 10, type=int)
        
        # Using in-memory storage since robot_commands table doesn't exist yet
        print("📝 Using in-memory storage for command history")
        
        # Fallback to in-memory history
        recent_history = command_history[-limit:] if len(command_history) > limit else command_history
        print(f"📝 Using in-memory fallback: {len(recent_history)} commands")
        return jsonify({
            'history': list(reversed(recent_history)),
            'source': 'memory_fallback',
            'note': 'Configure Supabase for persistent storage'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/pending', methods=['GET'])
def get_pending_commands():
    """Get pending commands for Pi client to fetch"""
    try:
        if supabase:
            try:
                response = supabase.table('robot_commands')\
                    .select('*')\
                    .eq('status', 'pending')\
                    .order('timestamp', desc=False)\
                    .execute()
                
                return jsonify({'commands': response.data})
            except Exception as e:
                print(f"⚠️ Database query failed: {e}")
                return jsonify({'error': 'Database unavailable'}), 500
        else:
            # Fallback to in-memory commands
            pending = [cmd for cmd in command_history if cmd.get('status') == 'pending']
            return jsonify({'commands': pending})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/<command_id>/status', methods=['PUT'])
def update_command_status(command_id):
    """Update command execution status (called by Pi client)"""
    try:
        data = request.get_json()
        new_status = data.get('status', 'completed')
        
        # Update in-memory storage since robot_commands table doesn't exist yet
        for cmd in command_history:
            if cmd['id'] == command_id:
                cmd['status'] = new_status
                cmd['completed_at'] = datetime.now().isoformat()
                break
            
            return jsonify({'success': True, 'status': new_status})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/status', methods=['GET'])
def get_server_status():
    """Get comprehensive server status"""
    try:
        return jsonify({
            'status': 'online',
            'services': {
                'supabase': 'connected' if supabase else 'disconnected',
                'robot_ai': 'ready' if processor else 'error',
                'pi_server': PI_SERVER_URL
            },
            'stats': {
                'total_commands': len(command_history),
                'upload_folder': UPLOAD_FOLDER
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Unified AI Robot Pet Backend...")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"🔗 Supabase: {'✅ Connected' if supabase else '❌ Not configured'}")
    print(f"🤖 Robot AI: {'✅ Ready' if processor else '❌ Error'}")
    print(f"🌐 Server starting on http://0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)