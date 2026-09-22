from app.services.audio_service import AudioService
from app.services.pii_service import PIIService
import json
import os

if __name__ == "__main__":
    service = AudioService()
    audio_file_path = "test_sample.m4a"

    if not os.path.exists(audio_file_path):
        print(f"❌ {audio_file_path} not found in {os.getcwd()}")
        exit(1)

    print(f"✅ Found: {audio_file_path}\n")
    result = service.process_audio(audio_file_path)

    # Apply PII redaction to the final output
    result["original_transcription"] = PIIService.redact(result.get("original_transcription", ""))
    result["translation"] = PIIService.redact(result.get("translation", ""))

    print("\n--- FINAL AUDIO JSON DELIVERABLE ---")
    print(json.dumps(result, indent=4, ensure_ascii=False))