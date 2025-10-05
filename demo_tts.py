#!/usr/bin/env python3
"""
DEMO TTS - Test ElevenLabs text-to-speech functionality
Interactive demo to test your TTS with different sentences
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
import requests

class DemoTTS:
    def __init__(self):
        """Initialize demo TTS with API key loading."""
        self.api_key = self._get_api_key()
        self.audio_dir = Path('demo_audio')
        self.audio_dir.mkdir(exist_ok=True)
        
        print("🎤 ElevenLabs TTS Demo")
        print("=" * 40)
        
        if self.api_key:
            print("✅ API Key loaded")
        else:
            print("⚠️ No API key found - will create placeholder files")
            print("💡 Add ELEVENLABS_API_KEY to keys.env for real TTS")
        
        print(f"📁 Audio files saved to: {self.audio_dir}")
        print()

    def _get_api_key(self):
        """Get ElevenLabs API key from environment or keys.env file."""
        # Try environment variable first
        api_key = os.environ.get('ELEVENLABS_API_KEY')
        if api_key:
            return api_key
        
        # Try keys.env file in multiple locations
        env_files = ['keys.env', 'backend/keys.env', '../keys.env']
        
        for env_file in env_files:
            try:
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('ELEVENLABS_API_KEY='):
                                key = line.split('=', 1)[1].strip().strip('"\'')
                                if key and key != "demo_api_key_here":
                                    return key
            except Exception as e:
                print(f"⚠️ Error reading {env_file}: {e}")
        
        return None

    def generate_tts(self, text, voice_id='21m00Tcm4TlvDq8ikWAM'):
        """
        Generate TTS audio from text.
        
        Args:
            text (str): Text to convert to speech
            voice_id (str): ElevenLabs voice ID
            
        Returns:
            str: Path to generated audio file or None if failed
        """
        if not text.strip():
            print("❌ Empty text provided")
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"demo_{timestamp}.mp3"
        file_path = self.audio_dir / filename

        print(f"🔄 Generating TTS for: '{text}'")
        
        if self.api_key and self.api_key != "demo_api_key_here":
            try:
                # Real ElevenLabs API call
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {
                    'xi-api-key': self.api_key,
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
                
                print("📡 Calling ElevenLabs API...")
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = len(response.content)
                    print(f"✅ TTS generated: {filename} ({file_size:,} bytes)")
                    return str(file_path)
                else:
                    print(f"❌ ElevenLabs API error {response.status_code}: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ Error calling ElevenLabs API: {e}")
                return None
        else:
            # Demo mode - create placeholder file
            with open(file_path, 'w') as f:
                f.write(f"Demo TTS file for: {text}\nGenerated: {datetime.now()}")
            
            print(f"📝 Demo file created: {filename}")
            print("💡 Add real API key to keys.env for actual audio")
            return str(file_path)

    def interactive_demo(self):
        """Run interactive TTS demo."""
        print("🎯 Interactive TTS Demo")
        print("Commands:")
        print("  - Type any text to generate TTS")
        print("  - 'quit' or 'exit' to stop")
        print("  - 'test' for sample sentences")
        print()

        while True:
            try:
                user_input = input("💬 Enter text (or 'quit'): ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                    
                if user_input.lower() == 'test':
                    self._run_test_sentences()
                    continue
                
                # Generate TTS
                start_time = time.time()
                audio_path = self.generate_tts(user_input)
                elapsed = time.time() - start_time
                
                if audio_path:
                    print(f"⏱️  Generated in {elapsed:.2f} seconds")
                    print(f"📄 File: {audio_path}")
                else:
                    print("❌ TTS generation failed")
                
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def _run_test_sentences(self):
        """Generate TTS for sample test sentences."""
        test_sentences = [
            "Hello! I am your AI robot pet.",
            "Moving forward as requested.",
            "Turning left to explore new areas.",
            "I understand your command perfectly.",
            "Robot systems are fully operational.",
            "Ready to assist you with any task."
        ]
        
        print("🧪 Generating test sentences...")
        print()
        
        for i, sentence in enumerate(test_sentences, 1):
            print(f"Test {i}/{len(test_sentences)}: {sentence}")
            audio_path = self.generate_tts(sentence)
            if audio_path:
                print(f"✅ Saved to: {os.path.basename(audio_path)}")
            print()
            time.sleep(0.5)  # Brief pause between requests

    def batch_test(self, sentences):
        """Generate TTS for a list of sentences."""
        print(f"🔄 Batch processing {len(sentences)} sentences...")
        results = []
        
        for i, sentence in enumerate(sentences, 1):
            print(f"[{i}/{len(sentences)}] Processing: {sentence}")
            audio_path = self.generate_tts(sentence)
            results.append({
                'text': sentence,
                'audio_path': audio_path,
                'success': audio_path is not None
            })
            time.sleep(0.3)  # Rate limiting
        
        # Summary
        successful = sum(1 for r in results if r['success'])
        print(f"\n📊 Batch Results: {successful}/{len(sentences)} successful")
        
        return results


def main():
    """Main demo function."""
    demo = DemoTTS()
    
    if len(sys.argv) > 1:
        # Command line mode
        text = ' '.join(sys.argv[1:])
        print(f"🎯 Single TTS generation: '{text}'")
        audio_path = demo.generate_tts(text)
        if audio_path:
            print(f"✅ Generated: {audio_path}")
        else:
            print("❌ Generation failed")
    else:
        # Interactive mode
        demo.interactive_demo()


if __name__ == "__main__":
    main()