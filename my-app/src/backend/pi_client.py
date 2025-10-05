#!/usr/bin/env python3
"""
STANDALONE PI CLIENT - Monitors Supabase database and executes robot actions
Runs independently on Raspberry Pi, continuously polls for command changes
Executes GPIO commands and plays TTS responses directly

REQUIREMENTS FOR PI:
pip install supabase python-dotenv requests RPi.GPIO

OPTIONAL AUDIO (choose one):
pip install pygame  # Preferred method
# OR
sudo apt-get install mpg123  # System audio player
# OR
sudo apt-get install mplayer  # Alternative player

REQUIRED .env FILE:
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

USAGE:
python pi_client.py

GPIO PIN CONFIGURATION FOR LED BREADBOARD:
- Action 1 (Forward): GPIO 17 -> LED + Resistor -> Ground
- Action 2 (Backward): GPIO 18 -> LED + Resistor -> Ground  
- Action 3 (Left): GPIO 23 -> LED + Resistor -> Ground
- Action 4 (Right): GPIO 27 -> LED + Resistor -> Ground
- LEDs stay ON indefinitely after action is triggered
- Use 220-330 ohm resistors for LED current limiting

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
import tempfile
import subprocess
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

def load_env_manual():
    """Manual fallback to load .env file if dotenv fails"""
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"📄 Loading {env_file} manually...")
        with open(env_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')  # Remove quotes
                        if key and value:
                            os.environ[key] = value
                            print(f"   ✅ Set {key}")
                    except Exception as e:
                        print(f"   ❌ Error parsing line {line_num}: {e}")
    else:
        print(f"❌ {env_file} file not found!")

class StandalonePiClient:
    """
    Standalone Pi client that monitors database for command changes
    and executes robot actions with TTS responses.
    """
    
    def __init__(self):
        """Initialize the standalone Pi client"""
        
        # Target user ID to monitor
        self.target_user_id = "a877a877-5a68-407f-bf18-6b3f4e69d59d"
        
        # GPIO pins for LED actions (4 different pins for 4 actions)
        self.gpio_pins = {
            1: 17,  # Action 1: Move Forward
            2: 18,  # Action 2: Move Backward  
            3: 23,  # Action 3: Turn Left
            4: 27   # Action 4: Turn Right
        }
        
        # Get Supabase credentials from environment
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        # If not found, try manual env loading
        if not self.supabase_url or not self.supabase_key:
            print("🔄 Environment variables not found, trying manual .env loading...")
            load_env_manual()
            self.supabase_url = os.getenv('SUPABASE_URL')
            self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
        
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
        
        # Load ElevenLabs API key with debugging
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        
        # Debug environment loading
        print(f"🔍 Environment check:")
        print(f"   - Current working directory: {os.getcwd()}")
        print(f"   - .env file exists: {os.path.exists('.env')}")
        print(f"   - ELEVENLABS_API_KEY found: {'Yes' if self.elevenlabs_api_key else 'No'}")
        if self.elevenlabs_api_key:
            print(f"   - API key preview: {self.elevenlabs_api_key[:10]}...")
        
        if not self.elevenlabs_api_key:
            print("⚠️ ELEVENLABS_API_KEY not found - TTS will be disabled")
            print("💡 Make sure .env file is in the same directory as this script")
            print("💡 .env file should contain: ELEVENLABS_API_KEY=your_key_here")
            print("💡 Example .env content:")
            print("   SUPABASE_URL=https://your-project.supabase.co")
            print("   SUPABASE_SERVICE_ROLE_KEY=your_service_key")
            print("   ELEVENLABS_API_KEY=your_elevenlabs_key")
        
        print(f"🤖 Standalone Pi Client initialized")
        print(f"🎯 Monitoring user: {self.target_user_id}")
        print(f"📌 GPIO pins: {self.gpio_pins}")
        print(f"🌐 Supabase: {self.supabase_url}")
        
        # Test database connection
        self._test_database_connection()
    
    def _setup_gpio(self):
        """Initialize GPIO for LED control (4 pins for 4 actions)"""
        if GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                # Setup all 4 pins as outputs
                for action, pin in self.gpio_pins.items():
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)  # Start with all LEDs off
                    print(f"✅ GPIO pin {pin} (Action {action}) initialized")
                
                print("🔴🟡🟢🔵 All LED pins ready")
            except Exception as e:
                print(f"❌ GPIO setup failed: {e}")
        else:
            print("💡 Running in GPIO simulation mode (4 LEDs)")
    
    def _setup_audio(self):
        """Initialize audio playback system"""
        self.pygame_working = False
        
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self.pygame_working = True
                print("✅ Pygame audio system initialized")
            except Exception as e:
                print(f"❌ Pygame init failed: {e}")
                print("💡 Falling back to system audio commands")
                self.pygame_working = False
        elif PYDUB_AVAILABLE:
            print("✅ Pydub audio system available")
        else:
            print("⚠️ No Python audio libraries - will use system commands")
    
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
        Turns on corresponding LED and leaves it on indefinitely.
        
        Args:
            action_number (int): 0-4 robot action
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"🎯 Executing action {action_number}")
            
            if action_number == 0:
                print("💬 Conversational response - no LED action")
                return True
            elif action_number in self.gpio_pins:
                # Turn on the corresponding LED for this action
                if action_number == 1:
                    print("➡️ MOVE FORWARD - LED ON")
                elif action_number == 2:
                    print("⬅️ MOVE BACKWARD - LED ON") 
                elif action_number == 3:
                    print("↩️ TURN LEFT - LED ON")
                elif action_number == 4:
                    print("↪️ TURN RIGHT - LED ON")
                
                return self._set_led_state(action_number, True)
            else:
                print(f"❌ Unknown action number: {action_number}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing action {action_number}: {e}")
            return False
    
    def _set_led_state(self, action_number, state):
        """
        Set LED state for specific action (ON stays ON indefinitely)
        
        Args:
            action_number (int): Action number (1-4)
            state (bool): True for ON, False for OFF
        
        Returns:
            bool: True if successful
        """
        try:
            if action_number not in self.gpio_pins:
                print(f"❌ Invalid action number: {action_number}")
                return False
                
            pin = self.gpio_pins[action_number]
            
            if GPIO_AVAILABLE:
                GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
                state_text = "ON" if state else "OFF"
                led_colors = {1: "🔴", 2: "🟡", 3: "🟢", 4: "🔵"}
                color = led_colors.get(action_number, "💡")
                print(f"{color} GPIO pin {pin} (Action {action_number}) set {state_text}")
            else:
                state_text = "ON" if state else "OFF"
                led_colors = {1: "🔴 RED", 2: "🟡 YELLOW", 3: "🟢 GREEN", 4: "🔵 BLUE"}
                color = led_colors.get(action_number, "💡")
                print(f"💡 [SIMULATION] {color} LED (pin {pin}) would be {state_text}")
            
            return True
        except Exception as e:
            print(f"❌ GPIO LED control failed: {e}")
            return False
    
    def turn_off_all_leds(self):
        """Turn off all LEDs"""
        try:
            print("🔴🟡🟢🔵 Turning off all LEDs")
            for action_number in self.gpio_pins:
                self._set_led_state(action_number, False)
            return True
        except Exception as e:
            print(f"❌ Failed to turn off LEDs: {e}")
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
        Tries multiple methods: pygame, pydub, or system commands (aplay/mpg123)
        
        Args:
            audio_bytes (bytes): MP3 audio data
            
        Returns:
            bool: True if successful
        """
        try:
            if PYGAME_AVAILABLE and self.pygame_working:
                # Use pygame for playback
                try:
                    audio_buffer = io.BytesIO(audio_bytes)
                    pygame.mixer.music.load(audio_buffer)
                    pygame.mixer.music.play()
                    
                    # Wait for playback to complete
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    
                    print("✅ Audio played via pygame")
                    return True
                except Exception as e:
                    print(f"❌ Pygame playback failed: {e}")
                    print("💡 Switching to system commands")
                    self.pygame_working = False  # Don't try pygame again
                    return self._play_audio_system_command(audio_bytes)
                
            elif PYDUB_AVAILABLE:
                # Use pydub for playback
                from pydub import AudioSegment
                audio_buffer = io.BytesIO(audio_bytes)
                audio = AudioSegment.from_mp3(audio_buffer)
                play(audio)
                
                print("✅ Audio played via pydub")
                return True
            else:
                # Fallback to system audio commands (common on Pi)
                return self._play_audio_system_command(audio_bytes)
                
        except Exception as e:
            print(f"❌ Primary audio playback failed: {e}")
            # Try system command as fallback
            try:
                return self._play_audio_system_command(audio_bytes)
            except Exception as e2:
                print(f"❌ System audio fallback also failed: {e2}")
                return False
    
    def _play_audio_system_command(self, audio_bytes):
        """
        Play audio using system commands (mpg123, aplay, etc.)
        
        Args:
            audio_bytes (bytes): MP3 audio data
            
        Returns:
            bool: True if successful
        """
        try:
            import tempfile
            import subprocess
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            # Try different audio players (common on Pi)
            audio_commands = [
                ['mpg123', '-q', tmp_path],  # Common MP3 player
                ['mplayer', '-quiet', tmp_path],  # Alternative player
                ['cvlc', '--intf', 'dummy', '--play-and-exit', tmp_path],  # VLC
                ['omxplayer', '-o', 'local', tmp_path],  # Pi-specific player
                ['aplay', tmp_path]  # Basic ALSA player (may not work with MP3)
            ]
            
            for cmd in audio_commands:
                try:
                    print(f"🎵 Trying: {cmd[0]}")
                    result = subprocess.run(cmd, 
                                          stdout=subprocess.DEVNULL, 
                                          stderr=subprocess.DEVNULL, 
                                          timeout=30)
                    
                    if result.returncode == 0:
                        print(f"✅ Audio played via {cmd[0]}")
                        # Cleanup temp file
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                        return True
                        
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            print("❌ No working audio player found")
            print("💡 Install one of: mpg123, mplayer, vlc, or omxplayer")
            
            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"❌ System audio command failed: {e}")
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