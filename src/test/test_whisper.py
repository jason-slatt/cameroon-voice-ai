# test_whisper_only.py
"""
Test Whisper service independently
"""
import asyncio
from pathlib import Path

from services.whisper.preprocessor import AudioPreprocessor
from services.whisper.service import WhisperService



async def test_whisper():
    print("\n" + "="*50)
    print("🧪 TESTING WHISPER SERVICE")
    print("="*50 + "\n")
    
    # 1. Initialize
    print("1️⃣ Loading Whisper model...")
    whisper = WhisperService()
    await whisper.initialize()
    print("   ✅ Whisper loaded\n")
    
    # 2. Check if ready
    if whisper.is_ready():
        print("2️⃣ ✅ Whisper is ready\n")
    else:
        print("2️⃣ ❌ Whisper NOT ready\n")
        return
    
    # 3. Test with audio file
    # REPLACE THIS with your actual test audio file
    test_audio = Path("test_audio.wav")
    
    if not test_audio.exists():
        print(f"❌ Test audio file not found: {test_audio}")
        print("   Create a short audio file and try again.")
        return
    
    print(f"3️⃣ Testing with: {test_audio}")
    
    # 4. Preprocess
    print("   📦 Preprocessing audio...")
    preprocessed = await AudioPreprocessor.preprocess(test_audio)
    print(f"   ✅ Preprocessed: {preprocessed}\n")
    
    # 5. Transcribe
    print("4️⃣ Transcribing...")
    text, language, confidence = await whisper.transcribe(preprocessed)
    
    print("\n" + "="*50)
    print("📊 RESULTS")
    print("="*50)
    print(f"📝 Text: {text}")
    print(f"🌍 Language: {language}")
    print(f"✅ Confidence: {confidence:.2%}")
    print("="*50 + "\n")
    
    # 6. Cleanup
    await whisper.cleanup()
    print("🧹 Cleanup complete\n")


if __name__ == "__main__":
    asyncio.run(test_whisper())