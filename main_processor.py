#!/usr/bin/env python3
"""
MAIN ROBOT PROCESSOR - Single clean interface
Reads audio → converts to text → processes through AI → returns result
"""

import os
import json
from datetime import datetime
from api_endpoint import RobotCommandProcessor, read_api_key
from speech_to_text import SpeechToTextProcessor


class MainRobotProcessor:
    """
    Single processor for the complete audio → action workflow.
    """
    
    def __init__(self):
        """Initialize with Gemini API components."""
        self.api_key = read_api_key()
        self.command_ai = RobotCommandProcessor(self.api_key)
        self.speech_processor = SpeechToTextProcessor(self.api_key)
        
        print("🤖 Main Robot Processor Ready!")
    
    def process_audio_command(self, audio_file_path):
        """
        MAIN FUNCTION: Complete audio processing pipeline
        
        Args:
            audio_file_path (str): Path to audio file saved by frontend
            
        Returns:
            dict: {
                'success': bool,
                'transcription': str,          # What user said
                'action_number': int,          # 0-4 for robot
                'voice_response': str,         # Response to play/show user  
                'command_type': str,           # 'command' or 'conversation'
                'timestamp': str,              # When processed
                'audio_file': str              # Original file path
            }
        """
        
        try:
            print(f"🎤 Processing audio: {audio_file_path}")
            
            # Step 1: Audio file → Text
            transcription = self.speech_processor.transcribe_audio_file(audio_file_path)
            
            # Handle transcription errors
            if transcription.startswith("[Error:") or transcription == "[Transcription failed]":
                return self._create_error_response(f"Transcription failed: {transcription}", audio_file_path)
            
            if transcription == "[No clear speech detected]":
                return self._create_error_response("No clear speech detected in audio", audio_file_path)
            
            print(f"📝 User said: '{transcription}'")
            
            # Step 2: Text → Robot Command
            ai_result = self.command_ai.process_input(transcription)
            
            # Step 3: Create complete result
            result = {
                'success': True,
                'transcription': transcription,
                'action_number': ai_result['action_number'],
                'voice_response': ai_result['voice_output'],
                'command_type': ai_result['type'],
                'timestamp': datetime.now().isoformat(),
                'audio_file': audio_file_path
            }
            
            print(f"✅ Action {result['action_number']}: {result['voice_response']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing audio: {e}")
            return self._create_error_response(str(e), audio_file_path)
    
    def process_text_command(self, text):
        """
        Alternative: Process text command directly (for testing)
        
        Args:
            text (str): User's text command
            
        Returns:
            dict: Same format as process_audio_command
        """
        try:
            print(f"📝 Processing text: '{text}'")
            
            # Process through AI
            ai_result = self.command_ai.process_input(text)
            
            result = {
                'success': True,
                'transcription': text,
                'action_number': ai_result['action_number'],
                'voice_response': ai_result['voice_output'],
                'command_type': ai_result['type'],
                'timestamp': datetime.now().isoformat(),
                'audio_file': None  # No audio file for text input
            }
            
            print(f"✅ Action {result['action_number']}: {result['voice_response']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing text: {e}")
            return self._create_error_response(str(e), None)
    
    def _create_error_response(self, error_message, audio_file=None):
        """Create standardized error response."""
        return {
            'success': False,
            'error': error_message,
            'transcription': None,
            'action_number': None,
            'voice_response': None,
            'command_type': None,
            'timestamp': datetime.now().isoformat(),
            'audio_file': audio_file
        }
    
    def get_supported_formats(self):
        """Get supported audio formats."""
        return self.speech_processor.supported_formats
    
    def validate_audio_file(self, file_path):
        """Validate audio file before processing."""
        return self.speech_processor.validate_audio_file(file_path)
    



def demo_main_processor():
    """Demo the main processor."""
    try:
        processor = MainRobotProcessor()
        
        print("\n" + "="*60)
        print("🤖 MAIN ROBOT PROCESSOR DEMO")
        print("="*60)
        print(f"Supported formats: {', '.join(processor.get_supported_formats())}")
        
        while True:
            print("\nOptions:")
            print("1. Process audio file")
            print("2. Process text command") 
            print("3. Validate audio file")
            print("4. Quit")
            
            choice = input("\nChoice: ").strip()
            
            if choice == '1':
                file_path = input("Enter audio file path: ").strip().strip('"')
                if file_path:
                    if os.path.exists(file_path):
                        result = processor.process_audio_command(file_path)
                        print(f"\n📤 Result:")
                        print(json.dumps(result, indent=2))
                    else:
                        print("❌ File not found")
                        
            elif choice == '2':
                text = input("Enter command: ").strip()
                if text:
                    result = processor.process_text_command(text)
                    print(f"\n📤 Result:")
                    print(json.dumps(result, indent=2))
                    
            elif choice == '3':
                file_path = input("Enter audio file path: ").strip().strip('"')
                if file_path:
                    is_valid, message = processor.validate_audio_file(file_path)
                    if is_valid:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ {message}")
                        
            elif choice == '4':
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    demo_main_processor()