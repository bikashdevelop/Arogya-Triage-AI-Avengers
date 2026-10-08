import os
import json
from dotenv import load_dotenv
from app.services.ingestion_service import IngestionService

load_dotenv()


def load_file(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


if __name__ == "__main__":
    service = IngestionService()

    report_bytes = load_file("report.png")
    rash_bytes = load_file("rash.png")

    audio_path = None
    for name in ["test_sample.m4a", "test_audio.m4a"]:
        if os.path.exists(name):
            audio_path = name
            break

    print(f"📁 Report PNG : {'✅ found' if report_bytes else '❌ missing'}")
    print(f"📁 Rash PNG   : {'✅ found' if rash_bytes else '❌ missing'}")
    print(f"📁 Audio M4A  : {'✅ found' if audio_path else '❌ missing'}")
    print()

    result = service.process_all_inputs(
        audio_path=audio_path,
        lab_report_bytes=report_bytes,
        lab_report_filename="report.png",
        symptom_photo_bytes=rash_bytes,
        symptom_photo_filename="rash.png",
    )

    print("\n--- FINAL JSON DELIVERABLE ---")
    print(json.dumps(result, indent=4, ensure_ascii=False))