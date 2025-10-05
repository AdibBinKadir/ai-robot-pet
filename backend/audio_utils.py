#!/usr/bin/env python3
"""
AUDIO UTILITIES - Optional helper functions for saving audio
Frontend team can use these if they want, or implement their own
"""

import os
import wave
import time
from pathlib import Path


class AudioSaver:
    """
    Simple audio file saving utilities.
    Frontend can use this or implement their own solution.
    """
    
    def __init__(self):
        # Standard audio settings that work well with Gemini
        self.channels = 1  # Mono
        self.sample_width = 2  # 16-bit
        self.frame_rate = 16000  # 16kHz (good for speech)
    
    def save_audio_data(self, audio_frames, filename=None, format='wav'):
        """
        Save raw audio frames to a file.
        
        Args:
            audio_frames (list): List of raw audio data frames
            filename (str): Output filename (auto-generated if None)
            format (str): Audio format ('wav' recommended)
            
        Returns:
            str: Path to saved file, or None if error
        """
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = int(time.time() * 1000)
                filename = f"audio_{timestamp}.wav"
            
            # Ensure .wav extension for wave module
            if format == 'wav' and not filename.lower().endswith('.wav'):
                filename += '.wav'
            
            # Create directory if needed
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            
            # Save as WAV file
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.sample_width)
                wf.setframerate(self.frame_rate)
                wf.writeframes(b''.join(audio_frames))
            
            file_size = os.path.getsize(filename)
            print(f"✅ Audio saved: {filename} ({file_size} bytes)")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error saving audio: {e}")
            return None
    
    def create_audio_filename(self, prefix="audio", user_id=None, extension="wav"):
        """
        Generate a unique audio filename.
        
        Args:
            prefix (str): Filename prefix
            user_id (str): Optional user identifier
            extension (str): File extension
            
        Returns:
            str: Generated filename
        """
        timestamp = int(time.time() * 1000)
        
        if user_id:
            filename = f"{prefix}_{user_id}_{timestamp}.{extension}"
        else:
            filename = f"{prefix}_{timestamp}.{extension}"
        
        return filename
    
    def get_audio_info(self, filename):
        """
        Get information about an audio file.
        
        Args:
            filename (str): Path to audio file
            
        Returns:
            dict: Audio file information or None if error
        """
        try:
            if not os.path.exists(filename):
                return None
            
            info = {
                'filename': filename,
                'size_bytes': os.path.getsize(filename),
                'exists': True
            }
            
            # Try to get WAV file details
            if filename.lower().endswith('.wav'):
                try:
                    with wave.open(filename, 'rb') as wf:
                        info.update({
                            'channels': wf.getnchannels(),
                            'sample_width': wf.getsampwidth(),
                            'frame_rate': wf.getframerate(),
                            'frames': wf.getnframes(),
                            'duration_seconds': wf.getnframes() / wf.getframerate()
                        })
                except:
                    # Not a valid WAV, but that's ok
                    pass
            
            return info
            
        except Exception as e:
            print(f"❌ Error getting audio info: {e}")
            return None
    
    def cleanup_old_files(self, directory=".", max_age_hours=24, pattern="audio_*.wav"):
        """
        Clean up old audio files (optional housekeeping).
        
        Args:
            directory (str): Directory to clean
            max_age_hours (int): Delete files older than this
            pattern (str): File pattern to match
            
        Returns:
            int: Number of files deleted
        """
        try:
            import glob
            deleted_count = 0
            max_age_seconds = max_age_hours * 3600
            current_time = time.time()
            
            for filepath in glob.glob(os.path.join(directory, pattern)):
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > max_age_seconds:
                        os.remove(filepath)
                        deleted_count += 1
                        print(f"🗑️ Cleaned up: {filepath}")
            
            if deleted_count > 0:
                print(f"✅ Cleaned up {deleted_count} old audio files")
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            return 0


def demo_audio_saver():
    """Demo the audio saver functionality."""
    saver = AudioSaver()
    
    print("🎵 Audio Saver Demo")
    print("=" * 40)
    
    # Generate sample filename
    filename = saver.create_audio_filename(user_id="test_user")
    print(f"📝 Generated filename: {filename}")
    
    # Get info about existing files
    print(f"\n📁 Current directory audio files:")
    import glob
    for audio_file in glob.glob("*.wav") + glob.glob("*.mp3"):
        info = saver.get_audio_info(audio_file)
        if info:
            print(f"  📄 {info['filename']} - {info['size_bytes']} bytes")
            if 'duration_seconds' in info:
                print(f"      Duration: {info['duration_seconds']:.1f}s")


if __name__ == "__main__":
    demo_audio_saver()