import os
import time
from pathlib import Path
import google.generativeai as genai

class SpeechToTextProcessor:
    def __init__(self, api_key):
        """Initialize the Speech-to-Text processor with Gemini API for file-based processing."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Supported audio formats
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.webm', '.mp4', '.mpga', '.mpeg']

    
    def validate_audio_file(self, file_path):
        """Validate that the audio file exists and has a supported format."""
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.supported_formats:
            return False, f"Unsupported format: {file_ext}. Supported: {', '.join(self.supported_formats)}"
        
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, "File is empty"
            if file_size > 25 * 1024 * 1024:  # 25MB limit for Gemini
                return False, "File too large (max 25MB)"
        except Exception as e:
            return False, f"Error checking file: {e}"
        
        return True, "File is valid"
    

    
    def transcribe_audio_file(self, file_path):
        """Transcribe an audio file using Gemini API."""
        # Validate file first
        is_valid, message = self.validate_audio_file(file_path)
        if not is_valid:
            return f"[Error: {message}]"
        
        try:
            print(f"🔄 Processing audio file: {file_path}")
            
            # Upload audio file to Gemini
            uploaded_file = genai.upload_file(path=file_path)
            
            # Wait for processing
            while uploaded_file.state.name == "PROCESSING":
                print("⏳ Transcribing...")
                time.sleep(1)
                uploaded_file = genai.get_file(uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                raise ValueError("❌ Audio processing failed")
            
            # Create transcription prompt
            prompt = """
            Please transcribe the audio content accurately. 
            Return only the transcribed text without any additional comments or explanations.
            If the audio is unclear or empty, respond with: "[No clear speech detected]"
            """
            
            response = self.model.generate_content([prompt, uploaded_file])
            
            # Clean up uploaded file
            genai.delete_file(uploaded_file.name)
            
            transcription = response.text.strip()
            print(f"✅ Transcription complete: {transcription}")
            return transcription
            
        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            return "[Transcription failed]"
    

    


def read_api_key(env_file='backend/keys.env', key_name='GEMINI_API_KEY'):
    """Read API key from environment file."""
    try:
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith(key_name + '='):
                    return line.strip().split('=', 1)[1]
        raise ValueError(f"{key_name} not found in {env_file}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Environment file {env_file} not found")

def demo_file_transcription():
    """Demo function to test file-based speech-to-text functionality."""
    try:
        # Initialize
        api_key = read_api_key()
        stt = SpeechToTextProcessor(api_key)
        
        print("📁 File-Based Speech-to-Text Demo")
        print("=" * 50)
        print(f"Supported formats: {', '.join(stt.supported_formats)}")
        
        while True:
            print("\nChoose an option:")
            print("1. Transcribe audio file")
            print("2. Validate audio file")
            print("3. Quit")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == '1':
                file_path = input("Enter audio file path: ").strip().strip('"')
                if file_path:
                    print("\n" + "="*30)
                    transcription = stt.transcribe_audio_file(file_path)
                    print(f"📝 Transcription: {transcription}")
                else:
                    print("❌ Please provide a file path.")
                
            elif choice == '2':
                file_path = input("Enter audio file path to validate: ").strip().strip('"')
                if file_path:
                    is_valid, message = stt.validate_audio_file(file_path)
                    if is_valid:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ {message}")
                else:
                    print("❌ Please provide a file path.")
                    
            elif choice == '3':
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please try again.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    demo_file_transcription()
