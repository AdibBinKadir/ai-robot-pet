#!/usr/bin/env python3
"""
pi_client_standalone.py

Standalone script that continuously polls for voice input and controls GPIO pins.

Capabilities:
- Record from microphone continuously
- Upload audio to Gemini for transcription (file-based)
- Use Gemini to classify input as light control command or conversation
- Control GPIO pins (17, 18, 23, 27) for 4 LED lights
- Generate TTS via ElevenLabs and play it (pygame/pydub/system fallbacks)

Usage:
    python pi_client_standalone.py            # continuous polling mode

Environment:
    Place API keys in environment variables or a keys.env file in the same dir:
      GEMINI_API_KEY=...
      ELEVENLABS_API_KEY=...

GPIO PIN CONFIGURATION:
- Light 1: GPIO 17 (turn on first light)
- Light 2: GPIO 18 (turn on second light)
- Light 3: GPIO 23 (turn on third light)
- Light 4: GPIO 27 (turn on fourth light)

Notes:
 - Requires RPi.GPIO on Raspberry Pi
 - Falls back to simulation mode if GPIO not available
"""

import os
import sys
import time
import json
import io
import tempfile
from pathlib import Path
from datetime import datetime

try:
    import google.generativeai as genai
except Exception:
    genai = None

import requests

from dotenv import load_dotenv

# GPIO control imports
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO = None
    GPIO_AVAILABLE = False

# Optional audio libraries
try:
    import sounddevice as sd
    import soundfile as sf
    SOUNDDEVICE_AVAILABLE = True
except Exception:
    SOUNDDEVICE_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False

try:
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
    PYDUB_AVAILABLE = True
except Exception:
    PYDUB_AVAILABLE = False

load_dotenv()


def read_api_key(key_name='GEMINI_API_KEY', env_file='keys.env'):
    api_key = os.environ.get(key_name)
    if api_key:
        return api_key

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith(key_name + '='):
                    return line.strip().split('=', 1)[1]
    return None


class RobotCommandProcessor:
    """Processes voice commands and controls GPIO pins for LED lights."""
    def __init__(self, api_key=None):
        self.api_key = api_key
        if genai and api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None

        # GPIO pin mapping for each light
        self.gpio_pins = {1: 17, 2: 18, 3: 23, 4: 27}
        
        self.actions = {0: 'do nothing', 1: 'turn on first light', 2: 'turn on second light', 3: 'turn on third light', 4: 'turn on fourth light'}
        self.voice_responses = {0: 'I understand.', 1: 'Turning on the first light.', 2: 'Turning on the second light.', 3: 'Turning on the third light.', 4: 'Turning on the fourth light.'}
        
        # Initialize GPIO
        self._setup_gpio()
    
    def _setup_gpio(self):
        """Initialize GPIO pins for LED control."""
        if GPIO_AVAILABLE and GPIO is not None:
            try:
                GPIO.setmode(GPIO.BCM)
                for action, pin in self.gpio_pins.items():
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)  # Start with all lights off
                print(f"✅ GPIO initialized: pins {list(self.gpio_pins.values())}")
            except Exception as e:
                print(f"❌ GPIO setup failed: {e}")
        else:
            print("💡 Running in GPIO simulation mode")
    
    def _set_light_state(self, light_number, state):
        """Set GPIO pin state for specific light.
        
        Args:
            light_number (int): Light number (1-4)
            state (bool): True for ON (HIGH), False for OFF (LOW)
        """
        if light_number not in self.gpio_pins:
            return
        
        pin = self.gpio_pins[light_number]
        
        if GPIO_AVAILABLE and GPIO is not None:
            try:
                GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
                state_text = "ON" if state else "OFF"
                print(f"💡 GPIO pin {pin} (Light {light_number}) set {state_text}")
            except Exception as e:
                print(f"❌ GPIO control failed: {e}")
        else:
            state_text = "ON" if state else "OFF"
            print(f"💡 [SIMULATION] Light {light_number} (pin {pin}) would be {state_text}")

    def create_command_detection_prompt(self, user_input):
        return f"""
You are a friendly assistant that can control LED lights and have conversations.

Analyze the user's input and determine if they want:
1. To turn on a specific light (first light, second light, third light, fourth light)
2. Just a normal conversation

Return only a JSON object like:
{{"action": <number>, "response": "<text>", "is_command": <true|false>}}

Actions:
0 = do nothing
1 = turn on first light
2 = turn on second light
3 = turn on third light
4 = turn on fourth light

User input: "{user_input}"
"""

    def process_input(self, user_input):
        # Try model-based classification
        try:
            if self.model:
                prompt = self.create_command_detection_prompt(user_input)
                response = self.model.generate_content(prompt)
                text = response.text.strip()
                # extract json
                if '{' in text and '}' in text:
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_text = text[start:end]
                    result = json.loads(json_text)
                else:
                    result = json.loads(text)

                action = int(result.get('action', 0))
                resp = result.get('response', self.voice_responses.get(action, 'I understand.'))
                is_cmd = bool(result.get('is_command', False))
                return {'type': 'command' if is_cmd else 'conversation', 'action_number': action, 'voice_output': resp, 'is_command': is_cmd}

        except Exception:
            pass

        # Fallback keyword matching
        lower = user_input.lower()
        if any(w in lower for w in ['first light', 'light 1', 'light one', '1st light']):
            return {'type': 'command', 'action_number': 1, 'voice_output': self.voice_responses[1], 'is_command': True}
        if any(w in lower for w in ['second light', 'light 2', 'light two', '2nd light']):
            return {'type': 'command', 'action_number': 2, 'voice_output': self.voice_responses[2], 'is_command': True}
        if any(w in lower for w in ['third light', 'light 3', 'light three', '3rd light']):
            return {'type': 'command', 'action_number': 3, 'voice_output': self.voice_responses[3], 'is_command': True}
        if any(w in lower for w in ['fourth light', 'light 4', 'light four', '4th light']):
            return {'type': 'command', 'action_number': 4, 'voice_output': self.voice_responses[4], 'is_command': True}

        # Default conversation
        return {'type': 'conversation', 'action_number': 0, 'voice_output': "I'm here to help!", 'is_command': False}


class SpeechToText:
    """File-based STT using Gemini upload_file if available, or local fallback."""
    def __init__(self, api_key=None):
        self.api_key = api_key
        if genai and api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            self.model = None

    def transcribe_file(self, file_path):
        file_path = str(file_path)
        if not os.path.exists(file_path):
            return '[Error: file not found]'

        if self.model:
            try:
                uploaded = genai.upload_file(path=file_path)
                while uploaded.state.name == 'PROCESSING':
                    time.sleep(1)
                    uploaded = genai.get_file(uploaded.name)

                if uploaded.state.name == 'FAILED':
                    return '[Error: audio processing failed]'

                prompt = "Please transcribe the audio content accurately. Return only the transcribed text."
                response = self.model.generate_content([prompt, uploaded])
                genai.delete_file(uploaded.name)
                return response.text.strip()
            except Exception as e:
                print(f"STT error: {e}")
                return '[Transcription failed]'

        # Local fallback: try to read text from a .txt placeholder or filename
        if file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()

        return '[Transcription unavailable - no API]'

    def record_from_mic(self, duration=5, sample_rate=16000, out_path=None):
        if not SOUNDDEVICE_AVAILABLE:
            return None, '[Microphone not available]'

        try:
            print(f"🎙️  Recording {duration}s from microphone...")
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            if not out_path:
                out_path = tempfile.mktemp(suffix='.wav')
            sf.write(out_path, recording, sample_rate)
            return out_path, None
        except Exception as e:
            return None, str(e)


class ElevenLabsTTS:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def generate_tts_bytes(self, text, voice_id='21m00Tcm4TlvDq8ikWAM'):
        if not self.api_key:
            return None
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        headers = {'xi-api-key': self.api_key, 'Accept': 'audio/mpeg', 'Content-Type': 'application/json'}
        payload = {'text': text, 'model_id': 'eleven_monolingual_v1', 'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5}}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.content
            else:
                print(f"ElevenLabs error {r.status_code}: {r.text}")
                return None
        except Exception as e:
            print(f"ElevenLabs request failed: {e}")
            return None

    def play_audio_bytes(self, audio_bytes):
        if not audio_bytes:
            return False
        # Try pygame
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                buf = io.BytesIO(audio_bytes)
                pygame.mixer.music.load(buf)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                return True
            except Exception:
                pass

        # Try pydub
        if PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format='mp3')
                pydub_play(audio)
                return True
            except Exception:
                pass

        # Fallback to saving temp file and using system player
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name
            players = [['mpg123', '-q', tmp], ['mplayer', '-quiet', tmp], ['cvlc', '--intf', 'dummy', '--play-and-exit', tmp]]
            for cmd in players:
                try:
                    res = __import__('subprocess').run(cmd, stdout=__import__('subprocess').DEVNULL, stderr=__import__('subprocess').DEVNULL, timeout=20)
                    if res.returncode == 0:
                        try:
                            os.unlink(tmp)
                        except Exception:
                            pass
                        return True
                except Exception:
                    continue
            try:
                os.unlink(tmp)
            except Exception:
                pass
        except Exception:
            pass

        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Standalone Pi client: continuously polls for voice input and controls GPIO lights')
    parser.add_argument('--duration', '-d', type=int, default=5, help='Recording duration (seconds) for each voice capture')
    args = parser.parse_args()

    gem_api = read_api_key('GEMINI_API_KEY')
    eleven_key = read_api_key('ELEVENLABS_API_KEY')

    stt = SpeechToText(api_key=gem_api)
    proc = RobotCommandProcessor(api_key=gem_api)
    tts = ElevenLabsTTS(api_key=eleven_key)

    print('🤖 Standalone Pi Client - Light Control System')
    print('='*60)
    print('Commands: "turn on first light", "turn on second light", etc.')
    print('GPIO Pins: Light 1→17, Light 2→18, Light 3→23, Light 4→27')
    print('Press Ctrl+C to quit')
    print('='*60)

    try:
        while True:
            # Continuously poll for voice input
            if SOUNDDEVICE_AVAILABLE:
                print(f'\n🎙️  Listening for {args.duration} seconds...')
                out_path, err = stt.record_from_mic(duration=args.duration)
                if err:
                    print(f'❌ Record error: {err}')
                    time.sleep(1)
                    continue
                
                print(f'🔄 Transcribing audio...')
                transcription = stt.transcribe_file(out_path)
                try:
                    os.unlink(out_path)
                except Exception:
                    pass
            else:
                # No mic - fallback to typed input
                user_text = input('\n💬 Type command (or "quit"): ').strip()
                if not user_text:
                    continue
                if user_text.lower() in ('quit', 'exit', 'q'):
                    break
                transcription = user_text

            print(f'📝 You said: "{transcription}"')

            # Process through command detector
            result = proc.process_input(transcription)
            action_num = result['action_number']
            
            print(f"🔎 Command type: {result['type']}")

            # Generate and play voice response
            voice_text = result.get('voice_output') or ''
            if voice_text:
                print(f'🗣️  Response: "{voice_text}"')
                audio_bytes = tts.generate_tts_bytes(voice_text) if eleven_key else None
                if audio_bytes:
                    tts.play_audio_bytes(audio_bytes)
                else:
                    print('⚠️  (TTS not available)')

            # If command, control GPIO pin
            if result.get('is_command') and action_num > 0:
                print(f"🎯 Executing: {proc.actions.get(action_num)}")
                # Turn OFF all lights first
                for light in range(1, 5):
                    proc._set_light_state(light, False)
                # Turn ON the requested light
                proc._set_light_state(action_num, True)

            print('-' * 60)
            time.sleep(0.5)

    except KeyboardInterrupt:
        print('\n\n🛑 Shutting down...')
        # Turn off all lights on exit
        if GPIO_AVAILABLE and GPIO is not None:
            try:
                for light in range(1, 5):
                    proc._set_light_state(light, False)
                GPIO.cleanup()
                print('✅ GPIO cleaned up')
            except Exception:
                pass
        print('👋 Goodbye!')


if __name__ == '__main__':
    main()
