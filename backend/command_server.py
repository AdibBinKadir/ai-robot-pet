#!/usr/bin/env python3
"""
COMMAND SERVER - Flask API for robot commands
Receives audio files, processes through AI, stores commands for Pi client
"""

import os
import json
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from main_processor import MainRobotProcessor

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm', 'm4a', 'flac'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the AI processor
processor = MainRobotProcessor()

# Command history for database team
command_history = []

# Pi configuration - update with your Pi's IP address
PI_SERVER_URL = "http://192.168.1.100:8080"  # TODO: Update with actual Pi IP

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the web interface."""
    return send_from_directory('web', 'index.html')

@app.route('/web/<path:filename>')
def web_files(filename):
    """Serve web assets."""
    return send_from_directory('web', filename)

@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    """
    Upload and process audio file.
    Returns: {success, result, command_id}
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process through AI
        result = processor.process_audio_command(file_path)
        
        if result['success']:
            # Create command entry for history/database
            command_id = str(uuid.uuid4())
            command_entry = {
                'id': command_id,
                'action_number': result['action_number'],
                'voice_response': result['voice_response'],
                'command_type': result['command_type'],
                'timestamp': result['timestamp'],
                'transcription': result['transcription']
            }

            # Save to history and database
            command_history.append(command_entry.copy())
            # TODO: Save to database here (database team job)
            # database.save_command(command_entry)

            # Send command directly to Pi
            pi_success = send_command_to_pi(command_entry)
            
            # Clean up uploaded file
            try:
                os.remove(file_path)
            except:
                pass

            return jsonify({
                'success': True,
                'result': result,
                'command_id': command_id,
                'pi_notified': pi_success
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Processing failed')}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def send_command_to_pi(command_entry):
    """
    Send command directly to Pi server.
    
    Args:
        command_entry (dict): Command to send to Pi
        
    Returns:
        bool: True if Pi was notified successfully
    """
    try:
        # Send POST request to Pi
        response = requests.post(
            f"{PI_SERVER_URL}/execute-command",
            json=command_entry,
            timeout=5  # 5 second timeout
        )
        
        if response.status_code == 200:
            print(f"✅ Command sent to Pi: {command_entry['id']}")
            return True
        else:
            print(f"❌ Pi responded with {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to reach Pi: {e}")
        return False
    except Exception as e:
        print(f"❌ Error sending to Pi: {e}")
        return False

@app.route('/api/history', methods=['GET'])
def get_history():
    """
    Get command history.
    Returns: {history: [...]}
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        recent_history = command_history[-limit:] if len(command_history) > limit else command_history
        return jsonify({'history': list(reversed(recent_history))})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-audio/<command_id>', methods=['GET'])
def get_audio(command_id):
    """
    Get generated audio for a command.
    Returns audio file or 404 if not found.
    """
    try:
        # TODO: Get from database (their job)
        # audio_data = database.get_audio(command_id)
        
        # Demo: Find command in memory
        command = None
        for cmd in command_history:
            if cmd['id'] == command_id:
                command = cmd
                break
        
        if not command:
            return jsonify({'error': 'Command not found'}), 404
            
        if not command.get('has_audio', False):
            return jsonify({'error': 'No audio available for this command'}), 404
        
        # TODO: Return actual audio file (their job)
        # return send_file(audio_path, mimetype='audio/mpeg')
        
        # Demo response
        return jsonify({
            'message': 'Audio would be served here',
            'text': command['voice_response'],
            'command_id': command_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/users', methods=['GET', 'POST'])
def manage_users():
    """
    Database endpoint for user management (their job to implement).
    """
    if request.method == 'GET':
        # TODO: Get users from database (their job)
        return jsonify({
            'users': [
                {'id': 1, 'name': 'Demo User', 'created': '2025-01-01T00:00:00Z'}
            ],
            'message': 'TODO: Connect to real database'
        })
    
    elif request.method == 'POST':
        # TODO: Create user in database (their job)
        data = request.get_json()
        return jsonify({
            'success': True,
            'message': 'TODO: User would be created in database',
            'data': data
        })

@app.route('/api/database/commands', methods=['GET'])
def get_database_commands():
    """
    Get commands from database (their job to implement).
    """
    try:
        # TODO: Query database (their job)
        # commands = database.get_commands(user_id=request.args.get('user_id'), 
        #                                 limit=request.args.get('limit', 50))
        
        return jsonify({
            'commands': command_history[-10:],  # Demo: return recent in-memory commands
            'total': len(command_history),
            'message': 'TODO: Connect to real database'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """
    Get server status and stats.
    """
    try:
        return jsonify({
            'status': 'online',
            'total_commands': len(command_history),
            'supported_formats': processor.get_supported_formats(),
            'pi_server_url': PI_SERVER_URL,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Robot Command Server...")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📱 Web interface: http://localhost:5000")
    print(f"🤖 AI Processor ready!")
    
    app.run(host='0.0.0.0', port=5000, debug=True)