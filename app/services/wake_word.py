import speech_recognition as sr
import threading
import time
import logging
import os
import sys

# Configure logging
logger = logging.getLogger(__name__)

class WakeWordDetector:
    def __init__(self, sensitivity=0.8):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.wake_callback = None
        self.sensitivity = sensitivity
        
        # Wake words - you can customize these
        self.wake_words = [
            "jarvis", "hey jarvis", "hello jarvis", "wake up", 
            "ultron", "hey ultron", "hello ultron", "are you there",
            "computer", "hey computer"
        ]
        
        # Adjust for ambient noise
        self._calibrate_microphone()
        
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        try:
            logger.info("🔧 Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            logger.info("✅ Microphone calibrated successfully")
        except Exception as e:
            logger.error(f"❌ Microphone calibration failed: {e}")
    
    def start_listening(self, wake_callback):
        """Start continuous wake word detection"""
        if self.is_listening:
            logger.warning("⚠️ Wake word detection already running")
            return
            
        self.wake_callback = wake_callback
        self.is_listening = True
        
        logger.info("👂 Starting wake word detection...")
        print("🎯 Wake words active: " + ", ".join(self.wake_words))
        
        # Start listening in a separate thread
        listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        listen_thread.start()
        
    def _listen_loop(self):
        """Main listening loop"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen for audio with shorter timeouts for responsiveness
                    audio = self.recognizer.listen(
                        source, 
                        timeout=1, 
                        phrase_time_limit=2
                    )
                
                # Convert speech to text
                text = self.recognizer.recognize_google(audio).lower()
                logger.debug(f"🎤 Heard: {text}")
                
                # Check for wake words
                if self._is_wake_word(text):
                    logger.info("✅ Wake word detected!")
                    if self.wake_callback:
                        self.wake_callback(text)
                        
            except sr.WaitTimeoutError:
                # No speech detected, continue listening
                continue
            except sr.UnknownValueError:
                # Speech not understood, continue listening
                continue
            except sr.RequestError as e:
                logger.error(f"❌ Speech recognition error: {e}")
                time.sleep(2)  # Wait before retry
            except Exception as e:
                logger.error(f"❌ Listening error: {e}")
                time.sleep(0.5)
                
    def _is_wake_word(self, text):
        """Check if the detected text contains any wake word"""
        if not text:
            return False
            
        text_lower = text.lower().strip()
        
        # Check for exact matches or contained matches
        for wake_word in self.wake_words:
            if (wake_word == text_lower or 
                wake_word in text_lower or 
                any(phrase in text_lower for phrase in wake_word.split())):
                return True
                
        return False
    
    def stop_listening(self):
        """Stop wake word detection"""
        self.is_listening = False
        logger.info("🔇 Wake word detection stopped")
    
    def add_wake_word(self, wake_word):
        """Add a custom wake word"""
        if wake_word and wake_word.lower() not in self.wake_words:
            self.wake_words.append(wake_word.lower())
            logger.info(f"✅ Added wake word: {wake_word}")
    
    def remove_wake_word(self, wake_word):
        """Remove a wake word"""
        if wake_word.lower() in self.wake_words:
            self.wake_words.remove(wake_word.lower())
            logger.info(f"🗑️ Removed wake word: {wake_word}")
    
    def get_wake_words(self):
        """Get list of current wake words"""
        return self.wake_words.copy()