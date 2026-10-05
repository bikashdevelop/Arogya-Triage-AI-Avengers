import os
import json
from dotenv import load_dotenv
from app.services.audio_service import AudioService
from app.services.pii_service import PIIService

load_dotenv()


if __name__ == "__main__":
    service = AudioService()

    # Try both possible filenames
    audio_path = None
    for name in ["test_sample.m4a", "test_audio.m4a", "test_audio.wav"]:
        if os.path.exists(name):
            audio_path = name
            break

    if not audio_path:
        print(f"❌ No audio file found in {os.getcwd()}")
        print("Place an audio file named test_sample.m4a or test_audio.m4a")
        exit(1)

    print(f"✅ Found: {audio_path}\n")
    result = service.process_audio(audio_path, language="auto")

    result["original_transcription"] = PIIService.redact(result.get("original_transcription", ""))
    result["translation"] = PIIService.redact(result.get("translation", ""))

    print("\n--- FINAL AUDIO JSON ---")
    print(json.dumps(result, indent=4, ensure_ascii=False))