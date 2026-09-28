"""
Ingestion Test — Two-layer privacy: real name for doctor, redacted for AI.
Run: python test_ingestion.py
"""
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


def load_text(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


if __name__ == "__main__":
    service = IngestionService()

    report_bytes = load_file("report.png")
    rash_bytes = load_file("rash.png")
    audio_path = "test_sample.m4a" if os.path.exists("test_sample.m4a") else None
    text_input = load_text("patient_input.txt")

    print(f"📁 Report PNG : {'✅ found' if report_bytes else '❌ missing'}")
    print(f"📁 Rash PNG   : {'✅ found' if rash_bytes else '❌ missing'}")
    print(f"📁 Audio M4A  : {'✅ found' if audio_path else '❌ missing'}")
    print(f"📁 Text Input : {'✅ found' if text_input else '❌ missing'}")
    print()

    result = service.process_all_inputs(
        audio_path=audio_path,
        text_input=text_input,
        lab_report_bytes=report_bytes,
        lab_report_filename="report.png",
        symptom_photo_bytes=rash_bytes,
        symptom_photo_filename="rash.png",
    )

    print("\n--- FINAL JSON DELIVERABLE ---")
    print(json.dumps(result, indent=4, ensure_ascii=False))