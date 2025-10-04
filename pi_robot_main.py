#!/usr/bin/env python3
"""
PI ROBOT MAIN - Complete robot system integration
Combines all components: AI processing + server polling + robot control
"""

import os
import sys
import time
import threading
from datetime import datetime

# Import your AI processing components
from main_processor import MainRobotProcessor
from pi_client import PiRobotClient

class RobotSystem:
    """
    Complete robot system that integrates AI processing with robot control.
    """
    
    def __init__(self, server_url="http://localhost:5000"):
        """
        Initialize the complete robot system.
        
        Args:
            server_url (str): URL of the command server
        """
        self.server_url = server_url
        self.running = False
        
        print("🤖 Initializing Robot System...")
        
        # Initialize AI processor (for local processing if needed)
        try:
            self.ai_processor = MainRobotProcessor()
            print("✅ AI Processor initialized")
        except Exception as e:
            print(f"❌ Failed to initialize AI processor: {e}")
            self.ai_processor = None
        
        # Initialize Pi client (for server communication)
        try:
            self.pi_client = PiRobotClient(server_url)
            print("✅ Pi Client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Pi client: {e}")
            sys.exit(1)
        
        print("🚀 Robot System ready!")
    
    def process_local_audio(self, audio_file_path):
        """
        Process audio file locally (bypass server).
        
        Args:
            audio_file_path (str): Path to audio file
            
        Returns:
            dict: Processing result
        """
        if not self.ai_processor:
            return {'success': False, 'error': 'AI processor not available'}
        
        try:
            print(f"🔄 Processing audio locally: {audio_file_path}")
            result = self.ai_processor.process_audio_command(audio_file_path)
            
            if result['success']:
                # Execute robot action directly
                action_number = result['action_number']
                success = self.pi_client.execute_robot_action(action_number)
                
                if success:
                    print(f"✅ Local command executed: {result['voice_response']}")
                else:
                    print(f"❌ Failed to execute local command")
                    
                result['robot_executed'] = success
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing local audio: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_local_text(self, text):
        """
        Process text command locally (bypass server).
        
        Args:
            text (str): Text command
            
        Returns:
            dict: Processing result
        """
        if not self.ai_processor:
            return {'success': False, 'error': 'AI processor not available'}
        
        try:
            print(f"🔄 Processing text locally: '{text}'")
            result = self.ai_processor.process_text_command(text)
            
            if result['success']:
                # Execute robot action directly
                action_number = result['action_number']
                success = self.pi_client.execute_robot_action(action_number)
                
                if success:
                    print(f"✅ Local command executed: {result['voice_response']}")
                else:
                    print(f"❌ Failed to execute local command")
                    
                result['robot_executed'] = success
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing local text: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_server_mode(self):
        """
        Run in server mode - poll server for commands.
        """
        print("🌐 Running in SERVER MODE - polling for commands...")
        self.pi_client.run()
    
    def run_local_mode(self):
        """
        Run in local mode - process commands locally.
        """
        if not self.ai_processor:
            print("❌ Cannot run local mode - AI processor not available")
            return
        
        print("💻 Running in LOCAL MODE - interactive commands...")
        print("Commands: 'audio <file>', 'text <command>', 'quit'")
        
        self.running = True
        
        try:
            while self.running:
                command = input("\n🤖 Enter command: ").strip().lower()
                
                if command == 'quit' or command == 'exit':
                    break
                elif command.startswith('audio '):
                    audio_file = command[6:].strip().strip('"\'')
                    if os.path.exists(audio_file):
                        result = self.process_local_audio(audio_file)
                        print(f"📤 Result: {result}")
                    else:
                        print(f"❌ File not found: {audio_file}")
                elif command.startswith('text '):
                    text = command[5:].strip()
                    if text:
                        result = self.process_local_text(text)
                        print(f"📤 Result: {result}")
                    else:
                        print("❌ Empty text command")
                else:
                    print("❌ Unknown command. Use 'audio <file>', 'text <command>', or 'quit'")
        
        except KeyboardInterrupt:
            print("\n🛑 Stopping local mode...")
        
        self.running = False
    
    def run_hybrid_mode(self):
        """
        Run in hybrid mode - both server polling AND local processing.
        """
        print("🔄 Running in HYBRID MODE - server polling + local commands...")
        
        # Start server polling in background thread
        server_thread = threading.Thread(target=self.pi_client.run, daemon=True)
        server_thread.start()
        
        # Run local mode in foreground
        self.run_local_mode()


def main():
    """
    Main function with command-line options.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Robot System Controller')
    parser.add_argument('--mode', choices=['server', 'local', 'hybrid'], 
                       default='server', help='Operating mode')
    parser.add_argument('--server-url', default='http://localhost:5000',
                       help='Server URL for server/hybrid modes')
    
    args = parser.parse_args()
    
    print("🤖 ROBOT SYSTEM STARTING")
    print(f"📋 Mode: {args.mode.upper()}")
    print(f"🌐 Server: {args.server_url}")
    print("="*50)
    
    # Create robot system
    robot = RobotSystem(args.server_url)
    
    # Run in selected mode
    try:
        if args.mode == 'server':
            robot.run_server_mode()
        elif args.mode == 'local':
            robot.run_local_mode()
        elif args.mode == 'hybrid':
            robot.run_hybrid_mode()
    except Exception as e:
        print(f"❌ System error: {e}")
    
    print("👋 Robot System shutdown complete")


if __name__ == "__main__":
    main()