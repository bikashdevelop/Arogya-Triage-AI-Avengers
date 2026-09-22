from app.services.ingestion_service import IngestionService
import json
import os

if __name__ == "__main__":
    service = IngestionService()
    
    # 👇 YOUR FILES HERE
    lab_report_filename = "report.png"  
    rash_photo_path = "rash.png"       
    
    lab_report_bytes = None
    rash_photo_bytes = None
    
    if os.path.exists(lab_report_filename):
        with open(lab_report_filename, "rb") as f:
            lab_report_bytes = f.read()
        print(f"✅ Loaded {lab_report_filename} for OCR.")
    else:
        print(f"❌ Warning: {lab_report_filename} not found.")

    if os.path.exists(rash_photo_path):
        with open(rash_photo_path, "rb") as f:
            rash_photo_bytes = f.read()
        print(f"✅ Loaded {rash_photo_path} for Vision.")
    else:
        print(f"❌ Warning: {rash_photo_path} not found.")

    result = service.process_all_inputs(
        text_input="My name is Jitendra, my ABHA is 12-3456-7890-1234. I have a high fever.",
        lab_report_bytes=lab_report_bytes,
        lab_report_filename=lab_report_filename,
        symptom_photo_bytes=rash_photo_bytes
    )
    
    print("\n--- FINAL CLEAN JSON DELIVERABLE ---")
    print(json.dumps(result, indent=4))