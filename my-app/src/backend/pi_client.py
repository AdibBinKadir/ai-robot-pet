#!/usr/bin/env python3
"""
PI CLIENT - Polls command server and executes robot actions
Runs on Raspberry Pi, connects to Flask server for commands
"""

import time
import json
import requests
from datetime import datetime
import os
from pathlib import Path
import base64
import threading

class PiRobotClient:
    """
    Client that runs on Raspberry Pi to execute robot commands.
    Polls the Flask server for new commands and executes them.
    """
    
    def __init__(self, server_url="http://localhost:5000"):
        """
        Initialize Pi client.
        
        Args:
            server_url (str): URL of the Flask command server
        """
        self.server_url = server_url.rstrip('/')
        self.poll_interval = 1.0  # seconds
        self.running = False
        
        print(f"🤖 Pi Robot Client initialized")
        print(f"🌐 Server: {self.server_url}")
        # Load local keys.env if present
        self._load_keys_env()

        # Optional pigpio setup (initialized lazily)
        self.pi = None
    
    def execute_robot_action(self, action_number):
        """
        Execute robot action based on action number.
        
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
                print("➡️  MOVE FORWARD")
                return self._move_forward()
            elif action_number == 2:
                print("⬅️  MOVE BACKWARD")
                return self._move_backward()
            elif action_number == 3:
                print("⬅️  TURN LEFT")
                return self._turn_left()
            elif action_number == 4:
                print("➡️  TURN RIGHT")
                return self._turn_right()
            else:
                print(f"❌ Unknown action number: {action_number}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing action {action_number}: {e}")
            return False

    def _load_keys_env(self, env_file='keys.env'):
        """Load simple KEY=VALUE pairs from env_file into os.environ if present."""
        try:
            if not os.path.exists(env_file):
                return
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip('"')
                    if k and v and k not in os.environ:
                        os.environ[k] = v
        except Exception as e:
            print(f"⚠️ Could not load {env_file}: {e}")

    def _read_key_from_env_file(self, key_name, env_file='keys.env'):
        """Read a single key from env file without modifying env.
        Returns the value or None."""
        try:
            if not os.path.exists(env_file):
                return None
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip().startswith(key_name + '='):
                        return line.strip().split('=', 1)[1].strip().strip('"')
        except Exception:
            return None
        return None

    def _ensure_pigpio(self):
        """Lazily initialize pigpio and store client in self.pi. Returns True if available."""
        if self.pi is not None:
            return True
        try:
            import pigpio
            self.pi = pigpio.pi()
            if not self.pi.connected:
                print("⚠️ pigpio daemon not running or cannot connect")
                self.pi = None
                return False
            return True
        except Exception as e:
            # pigpio not available; fallback to simulation
            print(f"⚠️ pigpio unavailable: {e}")
            self.pi = None
            return False

    # Movement stubs - use pigpio when available, otherwise simulate
    def _move_forward(self):
        if self._ensure_pigpio():
            try:
                # Example: set motor pins - replace with your wiring
                # self.pi.write(MOTOR_LEFT_FORWARD_PIN, 1)
                # self.pi.write(MOTOR_RIGHT_FORWARD_PIN, 1)
                time.sleep(0.5)
                return True
            except Exception as e:
                print(f"❌ pigpio move_forward error: {e}")
                return False
        else:
            time.sleep(0.5)
            return True

    def _move_backward(self):
        if self._ensure_pigpio():
            try:
                time.sleep(0.5)
                return True
            except Exception as e:
                print(f"❌ pigpio move_backward error: {e}")
                return False
        else:
            time.sleep(0.5)
            return True

    def _turn_left(self):
        if self._ensure_pigpio():
            try:
                time.sleep(0.4)
                return True
            except Exception as e:
                print(f"❌ pigpio turn_left error: {e}")
                return False
        else:
            time.sleep(0.4)
            return True

    def _turn_right(self):
        if self._ensure_pigpio():
            try:
                time.sleep(0.4)
                return True
            except Exception as e:
                print(f"❌ pigpio turn_right error: {e}")
                return False
        else:
            time.sleep(0.4)
            return True

    # Pi client intentionally keeps no AI/TTS responsibilities.
    # It only polls the server for command dicts and executes actions locally.
    def elevenlabs_tts(self, text, voice_id=None):
        """
        ElevenLabs TTS helper for the Pi. If ELEVENLABS_API_KEY is set in environment
        or in a local `keys.env`, this will attempt to call the ElevenLabs API and save
        an MP3 under `pi_audio/`. Otherwise it will write a placeholder file.
        Returns: path to saved audio file or None on failure.
        """
        try:
            # Try env var first
            api_key = os.environ.get('ELEVENLABS_API_KEY')
            # Fallback: try reading keys.env in repo root
            if not api_key:
                env_key = self._read_key_from_env_file('ELEVENLABS_API_KEY')
                if env_key:
                    api_key = env_key
            audio_dir = Path('pi_audio')
            audio_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_tts.mp3"
            file_path = audio_dir / filename

            if api_key:
                try:
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id or '21m00Tcm4TlvDq8ikWAM'}"
                    headers = { 'xi-api-key': api_key, 'Accept': 'audio/mpeg', 'Content-Type': 'application/json' }
                    payload = { 'text': text, 'model_id': 'eleven_monolingual_v1' }
                    resp = requests.post(url, json=payload, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(resp.content)
                        return str(file_path)
                    else:
                        print(f"ElevenLabs returned {resp.status_code}: {resp.text}")
                except Exception as e:
                    print(f"ElevenLabs request failed: {e}")

            # Fallback/demo behavior: create a small placeholder file so other systems can find it
            with open(file_path, 'wb') as f:
                f.write(b'')

            return str(file_path)

        except Exception as e:
            print(f"❌ TTS error on Pi: {e}")
            return None
    
    def poll_for_commands(self):
        """
        Poll server for new commands and execute them.
        """
        try:
            response = requests.get(f"{self.server_url}/api/get-commands", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            commands = data.get('commands', [])
            
            for command in commands:
                try:
                    print(f"\n📨 New command: {command['id']}")
                    print(f"🎤 User said: '{command['transcription']}'")
                    print(f"💭 Response: '{command['voice_response']}'")
                    # Synthesize TTS on Pi (ElevenLabs) and optionally play/save audio
                    try:
                        audio_path = self.elevenlabs_tts(command['voice_response'])
                        if audio_path:
                            print(f"🔊 TTS saved to: {audio_path}")
                            # TODO: Add platform playback code here (e.g., mpg123/aplay)
                    except Exception as e:
                        print(f"⚠️ TTS generation failed: {e}")

                    # Execute the robot action
                    success = self.execute_robot_action(command['action_number'])
                    
                    if success:
                        # Mark command as processed
                        mark_response = requests.post(
                            f"{self.server_url}/api/mark-processed",
                            json={'command_id': command['id']},
                            timeout=5
                        )
                        mark_response.raise_for_status()
                        print(f"✅ Command {command['id']} completed")
                    else:
                        print(f"❌ Failed to execute command {command['id']}")
                        
                except Exception as e:
                    print(f"❌ Error processing command {command.get('id', 'unknown')}: {e}")
            
            return len(commands)
            
        except requests.exceptions.RequestException as e:
            print(f"🌐 Connection error: {e}")
            return 0
        except Exception as e:
            print(f"❌ Error polling for commands: {e}")
            return 0
    
    def check_server_status(self):
        """
        Check if server is reachable.
        
        Returns:
            bool: True if server is online
        """
        try:
            response = requests.get(f"{self.server_url}/api/status", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            print(f"🟢 Server online - {data.get('pending_commands', 0)} pending commands")
            return True
            
        except Exception as e:
            print(f"🔴 Server unreachable: {e}")
            return False
    
    def run(self):
        """
        Main run loop - polls for commands continuously.
        """
        print(f"🚀 Starting Pi Robot Client...")
        
        # Check server connection
        if not self.check_server_status():
            print("❌ Cannot connect to server. Exiting.")
            return
        
        self.running = True
        print(f"🔄 Polling every {self.poll_interval} seconds...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                commands_processed = self.poll_for_commands()
                
                if commands_processed > 0:
                    print(f"📊 Processed {commands_processed} commands")
                
                time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Pi Robot Client...")
            self.running = False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            self.running = False


def main():
    """
    Main function - create and run Pi client.
    """
    import sys
    
    # Get server URL from command line or use default
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    # Create and run client
    client = PiRobotClient(server_url)
    client.run()


if __name__ == "__main__":
    main()