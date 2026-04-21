import sys

import pygame
import asyncio
import edge_tts
import os
import re
import unicodedata
import logging
import time
import glob
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, Callable, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Global variable to track last cleanup time
_last_cleanup_time = 0

def clean_text(text: str) -> str:
    """
    Thoroughly cleans text for speech synthesis by removing emojis and 
    normalizing special characters while preserving speech-relevant punctuation.
    """
    if not text or not isinstance(text, str):
        return ""
    
    # First normalize unicode characters
    normalized_text = unicodedata.normalize('NFKD', text)
    
    # Remove emojis and other symbol characters
    cleaned_text = ''.join(
        char for char in normalized_text
        if not unicodedata.category(char).startswith('So') and
           not unicodedata.category(char).startswith('Cs') and
           not unicodedata.category(char).startswith('Co')
    )
    
    # Keep only alphanumeric, spaces, and punctuation important for speech
    cleaned_text = re.sub(r'[^\w\s.,!?:;\'"-]', '', cleaned_text)
    
    # Normalize whitespace
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    return cleaned_text

def cleanup_old_audio_files(max_age_minutes=15, workspace_dir="data"):
    """
    Remove audio files older than specified minutes
    """
    global _last_cleanup_time
    
    current_time = time.time()
    # Only run cleanup every 5 minutes to avoid excessive file operations
    if current_time - _last_cleanup_time < 300:  # 5 minutes
        return
        
    _last_cleanup_time = current_time
    
    try:
        audio_dir = Path(workspace_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all audio files
        audio_files = glob.glob(str(audio_dir / "TTS_*.mp3"))
        current_time = time.time()
        max_age_seconds = max_age_minutes * 60
        
        files_deleted = 0
        for file_path in audio_files:
            try:
                file_age = current_time - os.path.getctime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    files_deleted += 1
                    logger.debug(f"Deleted old audio file: {file_path}")
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not delete file {file_path}: {e}")
            except Exception as e:
                logger.warning(f"Error processing file {file_path}: {e}")
                
        if files_deleted > 0:
            logger.info(f"Cleaned up {files_deleted} old audio files")
            
    except Exception as e:
        logger.error(f"Error in audio file cleanup: {e}")

async def text_to_audio_file(text: str, workspace_dir: str = "data") -> Optional[str]:
    """
    Converts text to speech audio file using edge-tts with unique filename.
    """
    if not text:
        logger.warning("Empty text provided for TTS conversion")
        return None
        
    # Use timestamp and random number to create unique filename
    timestamp = int(time.time() * 1000)
    file_path = str(Path(workspace_dir) / "audio" / f"TTS_{timestamp}.mp3")
    
    try:
        # Ensure the directory exists
        audio_dir = Path(file_path).parent
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up old files before creating new one
        cleanup_old_audio_files(15)  # 15 minutes retention
        
        # Get voice from environment or use default
        voice = os.environ.get('Voice', 'en-US-AriaNeural')
        
        # Convert text to speech
        communicate = edge_tts.Communicate(text, voice, pitch='+0Hz', rate='+0%')
        await communicate.save(file_path)
        
        logger.info(f"Audio file created: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to convert text to audio: {e}")
        return None

def text_to_speech(text: str, callback_func: Optional[Callable[[Any], bool]] = None, workspace_dir: str = "data") -> bool:
    """
    Plays text as speech using pygame.
    """
    # Create a default callback if none provided
    def default_callback(*args):
        return True
        
    callback_func = callback_func or default_callback
        
    if not text:
        logger.warning("Empty text provided for TTS playback")
        return False
        
    try:
        # Initialize pygame mixer if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
            if not pygame.mixer.get_init():
                logger.error("Failed to initialize pygame mixer")
                return False

        # Generate the audio file with unique filename
        audio_file = asyncio.run(text_to_audio_file(text, workspace_dir))
        
        if not audio_file or not os.path.exists(audio_file):
            logger.error("Failed to generate audio file")
            return False

        # Play the audio
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # Set a timeout to prevent infinite waiting
        max_wait_time = 300  # 5 minutes maximum
        wait_interval = 0.1  # Check every 100ms
        elapsed_time = 0

        # Wait while audio is playing
        while pygame.mixer.music.get_busy() and elapsed_time < max_wait_time:
            if not callback_func(True):
                break
            pygame.time.wait(int(wait_interval * 1000))
            elapsed_time += wait_interval
            
        if elapsed_time >= max_wait_time:
            logger.warning("TTS playback timed out")
            pygame.mixer.music.stop()
            return False
            
        return True

    except Exception as e:
        logger.error(f"Text-to-speech error: {e}")
        return False

    finally:
        # Clean up
        try:
            callback_func(False)
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                # Unload the music to release the file handle
                pygame.mixer.music.unload()
        except Exception as e:
            logger.error(f"Error during TTS cleanup: {e}")
            
        # Schedule cleanup for the next run
        try:
            cleanup_old_audio_files(15, workspace_dir)
        except:
            pass

def SpeakJARVIS(text: str, callback_func: Optional[Callable[[Any], bool]] = None, workspace_dir: str = "data") -> bool:
    """
    Smart text-to-speech function that handles long text appropriately.
    """
    def default_callback(*args):
        return True
        
    callback_func = callback_func or default_callback
        
    if not text:
        logger.warning("Empty text provided to SpeakJARVIS")
        return False
        
    # Clean the input text
    cleaned_text = clean_text(text)
    
    if not cleaned_text:
        logger.warning("Text cleaned to empty string")
        return False
    
    # For long text, speak only the beginning
    if len(cleaned_text) >= 1000:
        sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
        
        if len(sentences) > 2:
            shortened_text = ' '.join(sentences[:2])
            shortened_text += " The rest is available on screen."
            return text_to_speech(shortened_text, callback_func, workspace_dir)
        else:
            return text_to_speech(cleaned_text, callback_func, workspace_dir)
    else:
        return text_to_speech(cleaned_text, callback_func, workspace_dir)

# Add a function to manually trigger cleanup if needed
def cleanup_all_audio_files(workspace_dir: str = "data"):
    """Remove all audio files (use with caution)"""
    try:
        audio_dir = Path(workspace_dir) / "audio"
        audio_files = glob.glob(str(audio_dir / "TTS_*.mp3"))
        
        files_deleted = 0
        for file_path in audio_files:
            try:
                os.remove(file_path)
                files_deleted += 1
            except:
                pass
                
        logger.info(f"Removed {files_deleted} audio files")
        return files_deleted
    except Exception as e:
        logger.error(f"Error in complete cleanup: {e}")
        return 0

# Add these functions to your TTS.py file

class TanglishProcessor:
    def __init__(self):
        self.tanglish_responses = {
            # Greetings
            'hello': ['Vanakkam sir!', 'Hi boss!', 'Hello ana!'],
            'greeting': ['Vanakkam, epdi irukinga?', 'Hi, how are you?'],
            
            # Time responses
            'time': ['Sir time {time} irukku', 'Current time {time}'],
            'what time': ['Time {time} sir', 'Sir, ippo {time}'],
            
            # Weather responses
            'weather': ['Today weather {weather} irukku', 
                       'Sir, inniku {weather} weather'],
            'how weather': ['Weather report solren sir... {weather}'],
            
            # Actions
            'open': ['Opening {app} sir', '{app} open pannen sir'],
            'search': ['Searching for {query}', '{query} search pannen'],
            
            # Confirmations
            'okay': ['Seri sir', 'Okay boss', 'Nalla sir'],
            'thank you': ['Welcome sir', 'Sarithanam sir', 'My pleasure'],
            
            # Errors
            'not_understand': ['Mannikanum sir, puriyala', 
                             'Sorry, again sollunga', 
                             'Puriyala sir, repeat pannunga']
        }
        
        # Tanglish word conversions for natural speech
        self.english_to_tanglish = {
            'is': 'irukku',
            'are': 'irukka', 
            'good': 'nalla',
            'very good': 'romba nalla',
            'okay': 'seri',
            'thank you': 'nandri',
            'please': 'dayavuse',
            'sorry': 'mannikanum',
            'what': 'enna',
            'how': 'epdi',
            'why': 'edhukku',
            'when': 'eppo',
            'where': 'enge',
            'brother': 'machi',
            'friend': 'nanba',
            'today': 'inniku',
            'tomorrow': 'naala',
            'yesterday': 'netru'
        }
    
    def generate_tanglish_response(self, processed_input, context_data=None):
        """Generate natural Tanglish response based on input"""
        if not processed_input:
            return self._get_random_response('not_understand')
        
        command = processed_input['processed']
        is_tanglish = processed_input['is_tanglish']
        
        # Determine response type based on command
        response_type = self._classify_command(command)
        
        # Get base response
        base_response = self._get_random_response(response_type)
        
        # Fill in context data
        if context_data:
            base_response = base_response.format(**context_data)
        
        # Convert to Tanglish if input was in Tanglish
        if is_tanglish:
            base_response = self._convert_to_tanglish(base_response)
        
        return base_response
    
    def _classify_command(self, command):
        """Classify the type of command"""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ['time', 'maniku', 'neram']):
            return 'time'
        elif any(word in command_lower for word in ['weather', 'vanalai']):
            return 'weather'
        elif any(word in command_lower for word in ['open', 'tharu']):
            return 'open'
        elif any(word in command_lower for word in ['search', 'thedu']):
            return 'search'
        elif any(word in command_lower for word in ['hello', 'hi', 'vanakkam']):
            return 'hello'
        elif any(word in command_lower for word in ['thank', 'nandri']):
            return 'thank you'
        else:
            return 'not_understand'
    
    def _get_random_response(self, response_type):
        """Get a random response from available options"""
        import random
        responses = self.tanglish_responses.get(response_type, 
                                               self.tanglish_responses['not_understand'])
        return random.choice(responses) if isinstance(responses, list) else responses
    
    def _convert_to_tanglish(self, text):
        """Convert English text to natural Tanglish"""
        converted_text = text
        for eng, tang in self.english_to_tanglish.items():
            # Replace whole words only
            converted_text = re.sub(r'\b' + eng + r'\b', tang, converted_text, flags=re.IGNORECASE)
        return converted_text


def SpeakTanglish(text, context_data=None, callback_func=None):
    """
    Enhanced TTS function that speaks in Tanglish naturally
    """
    processor = TanglishProcessor()
    
    # If text is a processed input dict, generate Tanglish response
    if isinstance(text, dict) and 'processed' in text:
        tanglish_response = processor.generate_tanglish_response(text, context_data)
    else:
        # Convert regular text to Tanglish
        tanglish_response = processor._convert_to_tanglish(str(text))
    
    print(f"🤖 Jarvis (Tanglish): {tanglish_response}")
    return SpeakJARVIS(tanglish_response, callback_func)

def main():
    # Test the TTS functionality
    test_text = "Hello, this is a test of the text-to-speech system. How does it sound?"
    success = SpeakJARVIS(test_text)
    print(f"TTS test {'succeeded' if success else 'failed'}")

    # Clean up any test files immediately
    cleanup_all_audio_files()
    return 0


if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ultron import main as ultron_main

    sys.exit(ultron_main(["tts-test"]))
