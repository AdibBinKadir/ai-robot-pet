#!/usr/bin/env python3
"""
STANDALONE PI CLIENT - Monitors Supabase database and executes robot actions
Runs independently on Raspberry Pi, continuously polls for command changes
Executes GPIO commands and plays TTS responses directly

REQUIREMENTS FOR PI:
pip install supabase python-dotenv requests RPi.GPIO pygame

REQUIRED .env FILE:
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

USAGE:
python pi_client.py

GPIO PIN CONFIGURATION:
- Modify self.gpio_pin in __init__ method to change control pin
- Default is GPIO pin 18 (BCM numbering)
- Pin goes HIGH during robot actions, LOW when idle

TARGET USER ID:
- Monitors user ID: a877a877-5a68-407f-bf18-6b3f4e69d59d
- Change self.target_user_id in __init__ if needed
"""

import time
import json
import requests
import os
import io
import threading
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# GPIO control imports (will be available on Pi)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("⚠️ RPi.GPIO not available - running in simulation mode")
    GPIO_AVAILABLE = False

# Audio playback imports
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    try:
        import pydub
        from pydub.playback import play
        PYDUB_AVAILABLE = True
        PYGAME_AVAILABLE = False
    except ImportError:
        print("⚠️ Neither pygame nor pydub available - TTS will be silent")
        PYDUB_AVAILABLE = False
        PYGAME_AVAILABLE = False

# Load environment variables
load_dotenv()

class StandalonePiClient:
    """
    Standalone Pi client that monitors database for command changes
    and executes robot actions with TTS responses.
    """
    
    def __init__(self):
        """Initialize the standalone Pi client"""
        
        # Target user ID to monitor
        self.target_user_id = "a877a877-5a68-407f-bf18-6b3f4e69d59d"
        
        # GPIO pin for robot control (modify as needed)
        self.gpio_pin = 18  # Change this to your desired GPIO pin
        
        # Get Supabase credentials from environment
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")
        
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Polling settings
        self.poll_interval = 2.0  # seconds between database checks
        self.running = False
        
        # Track last seen command to detect changes
        self.last_action = None
        self.last_response = None
        self.last_is_command = None
        
        # Initialize GPIO
        self._setup_gpio()
        
        # Initialize audio system
        self._setup_audio()
        
        # Load ElevenLabs API key
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        if not self.elevenlabs_api_key:
            print("⚠️ ELEVENLABS_API_KEY not found - TTS will be disabled")
        
        print(f"🤖 Standalone Pi Client initialized")
        print(f"🎯 Monitoring user: {self.target_user_id}")
        print(f"📌 GPIO pin: {self.gpio_pin}")
        print(f"🌐 Supabase: {self.supabase_url}")
        
        # Test database connection
        self._test_database_connection()
    
    def _setup_gpio(self):
        """Initialize GPIO for robot control"""
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.gpio_pin, GPIO.OUT)
                GPIO.output(self.gpio_pin, GPIO.LOW)  # Start with pin low
                print(f"✅ GPIO pin {self.gpio_pin} initialized")
            except Exception as e:
                print(f"❌ GPIO setup failed: {e}")
        else:
            print("💡 Running in GPIO simulation mode")
    
    def _setup_audio(self):
        """Initialize audio playback system"""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                print("✅ Pygame audio system initialized")
            except Exception as e:
                print(f"❌ Pygame init failed: {e}")
        elif PYDUB_AVAILABLE:
            print("✅ Pydub audio system available")
        else:
            print("⚠️ No audio playback system available")
    
    def _test_database_connection(self):
        """Test connection to Supabase database"""
        try:
            # Try to fetch user profile to test connection
            response = self.supabase.table('user_profiles').select('*').eq('user_id', self.target_user_id).execute()
            if response.data:
                print("✅ Database connection successful")
                # Store initial state
                profile = response.data[0]
                self.last_action = profile.get('action')
                self.last_response = profile.get('response')
                self.last_is_command = profile.get('is_command')
                print(f"📊 Initial state - Action: {self.last_action}, Command: {self.last_is_command}")
            else:
                print(f"⚠️ No profile found for user {self.target_user_id}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def execute_robot_action(self, action_number):
        """
        Execute robot action based on action number.
        Sets GPIO pin high for the duration of the action.
        
        Args:
            action_number (int): 0-4 robot action
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"🎯 Executing action {action_number}")
            
            if action_number == 0:
                print("💬 Conversational response - no robot movement")
                return True
            elif action_number == 1:
                print("➡️ MOVE FORWARD")
                return self._trigger_gpio_action(0.8)  # 800ms pulse
            elif action_number == 2:
                print("⬅️ MOVE BACKWARD") 
                return self._trigger_gpio_action(0.8)  # 800ms pulse
            elif action_number == 3:
                print("↩️ TURN LEFT")
                return self._trigger_gpio_action(0.6)  # 600ms pulse
            elif action_number == 4:
                print("↪️ TURN RIGHT")
                return self._trigger_gpio_action(0.6)  # 600ms pulse
            else:
                print(f"❌ Unknown action number: {action_number}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing action {action_number}: {e}")
            return False
    
    def _trigger_gpio_action(self, duration):
        """
        Trigger GPIO pin for specified duration
        
        Args:
            duration (float): Duration in seconds to keep pin high
        
        Returns:
            bool: True if successful
        """
        try:
            if GPIO_AVAILABLE:
                GPIO.output(self.gpio_pin, GPIO.HIGH)
                print(f"📌 GPIO pin {self.gpio_pin} set HIGH for {duration}s")
                time.sleep(duration)
                GPIO.output(self.gpio_pin, GPIO.LOW)
                print(f"📌 GPIO pin {self.gpio_pin} set LOW")
            else:
                print(f"💡 [SIMULATION] GPIO pin {self.gpio_pin} would be HIGH for {duration}s")
                time.sleep(duration)
            
            return True
        except Exception as e:
            print(f"❌ GPIO action failed: {e}")
            return False

    def elevenlabs_tts_and_play(self, text, voice_id=None):
        """
        Generate TTS using ElevenLabs API and play it directly (no file saving).
        
        Args:
            text (str): Text to convert to speech
            voice_id (str): ElevenLabs voice ID (optional)
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.elevenlabs_api_key:
                print("⚠️ No ElevenLabs API key - skipping TTS")
                return False
            
            print(f"🔊 Generating TTS for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            # Make API request to ElevenLabs
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id or '21m00Tcm4TlvDq8ikWAM'}"
            headers = {
                'xi-api-key': self.elevenlabs_api_key,
                'Accept': 'audio/mpeg',
                'Content-Type': 'application/json'
            }
            payload = {
                'text': text,
                'model_id': 'eleven_monolingual_v1',
                'voice_settings': {
                    'stability': 0.5,
                    'similarity_boost': 0.5
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Play audio directly from memory
                return self._play_audio_from_bytes(response.content)
            else:
                print(f"❌ ElevenLabs API error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ TTS generation failed: {e}")
            return False
    
    def _play_audio_from_bytes(self, audio_bytes):
        """
        Play audio from byte data using available audio system.
        
        Args:
            audio_bytes (bytes): MP3 audio data
            
        Returns:
            bool: True if successful
        """
        try:
            if PYGAME_AVAILABLE:
                # Use pygame for playback
                audio_buffer = io.BytesIO(audio_bytes)
                pygame.mixer.music.load(audio_buffer)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                print("✅ Audio played via pygame")
                return True
                
            elif PYDUB_AVAILABLE:
                # Use pydub for playback
                from pydub import AudioSegment
                audio_buffer = io.BytesIO(audio_bytes)
                audio = AudioSegment.from_mp3(audio_buffer)
                play(audio)
                
                print("✅ Audio played via pydub")
                return True
            else:
                print("⚠️ No audio playback system available")
                return False
                
        except Exception as e:
            print(f"❌ Audio playback failed: {e}")
            return False
    
    def check_for_command_changes(self):
        """
        Check database for changes in user profile commands.
        
        Returns:
            bool: True if changes detected and processed
        """
        try:
            # Query the user profile for the target user
            response = self.supabase.table('user_profiles').select('*').eq('user_id', self.target_user_id).execute()
            
            if not response.data:
                print(f"⚠️ No profile found for user {self.target_user_id}")
                return False
            
            profile = response.data[0]
            current_action = profile.get('action')
            current_response = profile.get('response') 
            current_is_command = profile.get('is_command')
            
            # Check if anything has changed
            if (current_action != self.last_action or 
                current_response != self.last_response or 
                current_is_command != self.last_is_command):
                
                print(f"\n� Change detected!")
                print(f"📊 Action: {self.last_action} → {current_action}")
                print(f"💭 Response: {self.last_response} → {current_response}")
                print(f"🤖 Is Command: {self.last_is_command} → {current_is_command}")
                
                # Process the new command
                success = self._process_command_change(current_action, current_response, current_is_command)
                
                if success:
                    # Update our tracking variables
                    self.last_action = current_action
                    self.last_response = current_response
                    self.last_is_command = current_is_command
                
                return success
            
            return False  # No changes detected
            
        except Exception as e:
            print(f"❌ Error checking for changes: {e}")
            return False
    
    def _process_command_change(self, action, response, is_command):
        """
        Process a detected command change.
        
        Args:
            action (int): Action number (0-4)
            response (str): TTS response text
            is_command (bool): Whether this is a command or conversation
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"\n🎯 Processing new command:")
            print(f"📋 Action: {action}")
            print(f"💬 Response: '{response}'")
            print(f"🤖 Is Command: {is_command}")
            
            # Play TTS response if available
            if response and response.strip():
                tts_success = self.elevenlabs_tts_and_play(response)
                if not tts_success:
                    print("⚠️ TTS playback failed, continuing with action...")
            
            # Execute robot action if it's a command
            if is_command and action is not None:
                action_success = self.execute_robot_action(int(action))
                if action_success:
                    print(f"✅ Command processed successfully")
                else:
                    print(f"❌ Command execution failed")
                return action_success
            else:
                print("� Conversational response only - no robot action")
                return True
            
        except Exception as e:
            print(f"❌ Error processing command: {e}")
            return False
    
    def run(self):
        """
        Main run loop - continuously monitors database for changes.
        """
        print(f"🚀 Starting Standalone Pi Robot Client...")
        print(f"🎯 Monitoring user: {self.target_user_id}")
        print(f"📌 GPIO control pin: {self.gpio_pin}")
        print(f"🔄 Checking every {self.poll_interval} seconds...")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        
        try:
            while self.running:
                changes_detected = self.check_for_command_changes()
                
                if not changes_detected:
                    # Print a small status indicator every 30 seconds
                    if int(time.time()) % 30 == 0:
                        print("� No changes detected... (monitoring)")
                
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Standalone Pi Client...")
            self.running = False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.running = False
        finally:
            # Cleanup GPIO
            if GPIO_AVAILABLE:
                try:
                    GPIO.cleanup()
                    print("🧹 GPIO cleaned up")
                except:
                    pass


def main():
    """
    Main function - create and run standalone Pi client.
    No command line arguments needed - all config from .env file.
    """
    try:
        print("🤖 Initializing Standalone Pi Robot Client...")
        
        # Create and run client
        client = StandalonePiClient()
        client.run()
        
    except Exception as e:
        print(f"❌ Failed to start client: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())