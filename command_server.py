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

# In-memory command queue (replace with database later)
command_queue = []
command_history = []

# ElevenLabs Configuration (demo values - replace with real API key)
ELEVENLABS_API_KEY = "demo_api_key_here"  # TODO: Replace with real API key
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Demo voice ID

def text_to_speech_elevenlabs(text, voice_id=None):
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        text (str): Text to convert
        voice_id (str): Voice ID to use
        
    Returns:
        bytes: Audio data or None if failed
    """
    if not voice_id:
        voice_id = ELEVENLABS_VOICE_ID
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    try:
        # TODO: Uncomment when real API key is provided
        # response = requests.post(url, json=data, headers=headers)
        # if response.status_code == 200:
        #     return response.content
        # else:
        #     print(f"ElevenLabs API error: {response.status_code}")
        #     return None
        
        # Demo mode - return placeholder
        print(f"🔊 DEMO: Would generate speech for: '{text}'")
        return None
        
    except Exception as e:
        print(f"Error generating speech: {e}")
        return None

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
            # Add to command queue for Pi client (Pi will handle TTS/audio)
            command_id = str(uuid.uuid4())
            command_entry = {
                'id': command_id,
                'action_number': result['action_number'],
                'voice_response': result['voice_response'],
                'command_type': result['command_type'],
                'timestamp': result['timestamp'],
                'processed': False,
                'transcription': result['transcription']
            }

            command_queue.append(command_entry)
            command_history.append(command_entry.copy())

            # TODO: Save to database here (their job)
            # database.save_command(command_entry)

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

@app.route('/api/text-command', methods=['POST'])
def text_command():
    """
    Process text command directly.
    Returns: {success, result, command_id}
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'No text provided'}), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({'success': False, 'error': 'Empty text'}), 400
        
        # Process through AI
        result = processor.process_text_command(text)
        
        if result['success']:
            # Generate speech audio
            audio_data = text_to_speech_elevenlabs(result['voice_response'])
            
            # Add to command queue for Pi client
            command_id = str(uuid.uuid4())
            command_entry = {
                'id': command_id,
                'action_number': result['action_number'],
                'voice_response': result['voice_response'],
                'command_type': result['command_type'],
                'timestamp': result['timestamp'],
                'processed': False,
                'transcription': result['transcription'],
                'has_audio': audio_data is not None
            }
            
            command_queue.append(command_entry)
            command_history.append(command_entry.copy())
            
            # TODO: Save to database here (their job)
            # database.save_command(command_entry)
            
            return jsonify({
                'success': True,
                'result': result,
                'command_id': command_id,
                'has_audio': audio_data is not None
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Processing failed')}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-commands', methods=['GET'])
def get_commands():
    """
    Get pending commands for Pi client.
    Returns: {commands: [...]}
    """
    try:
        # Return unprocessed commands
        pending = [cmd for cmd in command_queue if not cmd['processed']]
        return jsonify({'commands': pending})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-processed', methods=['POST'])
def mark_processed():
    """
    Mark command as processed by Pi client.
    Body: {command_id: "..."}
    """
    try:
        data = request.get_json()
        if not data or 'command_id' not in data:
            return jsonify({'success': False, 'error': 'No command_id provided'}), 400
        
        command_id = data['command_id']
        
        # Find and mark command as processed
        for cmd in command_queue:
            if cmd['id'] == command_id:
                cmd['processed'] = True
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Command not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        pending_count = len([cmd for cmd in command_queue if not cmd['processed']])
        
        return jsonify({
            'status': 'online',
            'pending_commands': pending_count,
            'total_commands': len(command_history),
            'supported_formats': processor.get_supported_formats(),
            'elevenlabs_configured': ELEVENLABS_API_KEY != "demo_api_key_here",
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