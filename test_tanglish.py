from app.services import stt as STT
from app.services import tts as TTS

# Test Tanglish processing
test_phrases = [
    "vanakkam jarvis",
    "time enna", 
    "weather epdi irukku",
    "open chrome pannu",
    "nandri machi"
]

print("🧪 Testing Tanglish Integration...")

for phrase in test_phrases:
    print(f"\nInput: {phrase}")
    processed = STT.process_tanglish_input(phrase)
    print(f"Processed: {processed}")
    
    # Test TTS response
    response = TTS.TanglishProcessor().generate_tanglish_response(processed)
    print(f"Jarvis Response: {response}")

print("\n✅ Integration test completed!")
