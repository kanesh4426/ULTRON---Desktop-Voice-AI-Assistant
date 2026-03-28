import speech_recognition as sr
import re


def recognize_speech():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    # Adjust recognition parameters for better performance
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8        # Reduced from 1.5s (faster speech detection)
    recognizer.energy_threshold = 400       # Increased for quicker activation
    recognizer.operation_timeout = 5         # Reduced from 10s
    recognizer.non_speaking_duration = 0.3     # Faster end-of-speech detection

    with mic as source:
        print("🎤 Calibrating microphone for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1) # Faster calibration
        
        
        print("🎤 Listening... Speak now!")
        try:
            audio = recognizer.listen(
                source, 
                timeout=5,              # Reduced from 8s
                phrase_time_limit=8     # Reduced from 15s
            )
        except sr.WaitTimeoutError:
            print("⏰ No speech detected within timeout period.")
            return None
        except Exception as e:
            print(f"❌ Listening error: {e}")
            return None

    try:
        print("🔄 Processing speech...")
        text = recognizer.recognize_google(
            audio, 
            language='en-IN',
            show_all=False
        )
        print(f"🗣️  Mr. Kanesh : {text}")
        return text
        
    except sr.UnknownValueError:
        print("🤖 Could not understand audio. Please speak more clearly.")
    except sr.RequestError as e:
        print(f"🔌 Could not request results; {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
    
    return None


def continuous_listen(max_attempts=3):
    """Listen continuously with retries"""
    for attempt in range(max_attempts):
        print(f"\nAttempt {attempt + 1} of {max_attempts}")
        result = recognize_speech()
        if result:
            return result
        print("Trying again...")
    
    print("❌ Maximum attempts reached. Please try again later.")
    return None

# Enhanced Tanglish Recognition
def recognize_speech_tanglish():
    """Enhanced speech recognition for Tanglish"""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    
    # Adjust recognition parameters
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.energy_threshold = 400
    recognizer.operation_timeout = 5
    recognizer.non_speaking_duration = 0.3

    with mic as source:
        print("🎤 Calibrating microphone for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        print("🎤 Listening... Speak now!")
        try:
            audio = recognizer.listen(
                source, 
                timeout=5,
                phrase_time_limit=8
            )
        except sr.WaitTimeoutError:
            print("⏰ No speech detected within timeout period.")
            return None
        except Exception as e:
            print(f"❌ Listening error: {e}")
            return None

    try:
        print("🔄 Processing Tanglish speech...")
        # Try English first, then Tamil if needed
        try:
            text = recognizer.recognize_google(audio, language='en-IN')
        except:
            # Fallback to Tamil
            text = recognizer.recognize_google(audio, language='ta-IN')
        
        print(f"🗣️  User said: {text}")
        return process_tanglish_input(text)
        
    except sr.UnknownValueError:
        print("🤖 Could not understand audio. Please speak more clearly.")
    except sr.RequestError as e:
        print(f"🔌 Could not request results; {e}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
    
    return None

def process_tanglish_input(text):
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Priority: Multi-word phrases first
    phrases_replacements = [
        ('time enna', 'what time'),
        ('weather epdi', 'how weather'), 
        ('open pannu', 'open'),
        ('close pannu', 'close'),
        ('search pannu', 'search'),
        ('vanakkam', 'hello')
    ]
    
    processed_text = text_lower
    for phrase, replacement in phrases_replacements:
        processed_text = processed_text.replace(phrase, replacement)
    
    # Single word replacements
    word_mapping = {
        'nandri': 'thank you', 'epdi': 'how', 'enna': 'what',
        'yaaru': 'who', 'edhukku': 'why', 'eppadi': 'how',
        'sollu': 'tell', 'sollunga': 'please tell',
        'seri': 'okay', 'nalla': 'good'
    }
    
    words = processed_text.split()
    processed_words = []
    for word in words:
        processed_words.append(word_mapping.get(word, word))
    
    processed_text = ' '.join(processed_words)
    
    return {
        'original': text,
        'processed': processed_text,
        'is_tanglish': text_lower != processed_text
    }