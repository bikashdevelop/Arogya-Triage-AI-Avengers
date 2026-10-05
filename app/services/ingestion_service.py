from app.services.audio_service import AudioService
from app.services.ocr_service import OCRService
from app.services.vision_service import VisionService
from app.services.pii_service import PIIService


class IngestionService:
    def __init__(self):
        self.audio_service = AudioService()
        self.ocr_service = OCRService()
        self.vision_service = VisionService()

    def process_all_inputs(
        self,
        audio_path: str = None,
        text_input: str = None,
        lab_report_bytes: bytes = None,
        lab_report_filename: str = "report.png",
        symptom_photo_bytes: bytes = None,
        symptom_photo_filename: str = "rash.png",
    ) -> dict:

        final_data = {
            "status": "success",
            "patient_name": "Unknown",
            "raw_text": "",
            "redacted_text": "",
            "translation": "",
            "symptoms": [],
            "duration": "",
            "severity": "",
            "follow_up_questions": [],
            "report_data": None,
            "visual_findings": None,
            "errors": [],
            "confidence_score": 0.0,
        }

        collected_names = []
        collected_symptoms = []

        # ===== 1. AUDIO =====
        if audio_path:
            audio_result = self.audio_service.process_audio(audio_path)
            if audio_result.get("status") == "low_confidence":
                return audio_result

            final_data["raw_text"] = audio_result.get("original_transcription", "")
            final_data["redacted_text"] = audio_result.get("redacted_transcription", "")
            final_data["translation"] = audio_result.get("translation", "")
            collected_symptoms.extend(audio_result.get("symptoms", []))
            final_data["duration"] = audio_result.get("duration", "")
            final_data["severity"] = audio_result.get("severity", "")
            final_data["follow_up_questions"] = audio_result.get("follow_up_questions", [])
            final_data["confidence_score"] = audio_result.get("confidence_score", 0.0)

            # Collect names from audio
            if audio_result.get("patient_name") and audio_result["patient_name"] != "Unknown":
                collected_names.append(audio_result["patient_name"])

        # ===== 2. TEXT INPUT =====
        if text_input:
            print(f"Processing text input ({len(text_input)} chars)...")

            # Extract names from text BEFORE redaction
            text_names = PIIService.extract_names(text_input)
            print(f"  🔒 Extracted from text: {text_names}")

            # Redact before sending to LLM
            redacted_text = PIIService.redact(text_input)
            print(f"  🔒 Redacted text sent to LLM: {redacted_text[:80]}...")

            # Send redacted to LLM
            text_extracted = self.audio_service.refine_with_groq(redacted_text, "auto")

            # Merge into final data
            if final_data["raw_text"]:
                final_data["raw_text"] += "\n" + text_input
            else:
                final_data["raw_text"] = text_input

            if final_data["redacted_text"]:
                final_data["redacted_text"] += "\n" + redacted_text
            else:
                final_data["redacted_text"] = redacted_text

            if text_extracted.get("translation"):
                if final_data["translation"]:
                    final_data["translation"] += " " + text_extracted["translation"]
                else:
                    final_data["translation"] = text_extracted["translation"]

            collected_symptoms.extend(text_extracted.get("symptoms", []))
            collected_names.extend(text_names)

            if not final_data["duration"]:
                final_data["duration"] = text_extracted.get("duration", "")
            if not final_data["severity"]:
                final_data["severity"] = text_extracted.get("severity", "")
            if not final_data["follow_up_questions"]:
                final_data["follow_up_questions"] = text_extracted.get("follow_up_questions", [])

        # Deduplicate names + symptoms
        seen_n = set()
        unique_names = []
        for n in collected_names:
            for part in n.split(", "):
                key = part.strip().lower()
                if key and key not in seen_n:
                    seen_n.add(key)
                    unique_names.append(part.strip())
        final_data["patient_name"] = ", ".join(unique_names) if unique_names else "Unknown"

        seen_s = set()
        unique_symptoms = []
        for s in collected_symptoms:
            key = s.strip().lower()
            if key and key not in seen_s:
                seen_s.add(key)
                unique_symptoms.append(s.strip())
        final_data["symptoms"] = unique_symptoms

        # ===== 3. OCR =====
        if lab_report_bytes:
            ocr_result = self.ocr_service.extract_report_data(lab_report_bytes, lab_report_filename)
            if ocr_result.get("status") == "success":
                final_data["report_data"] = ocr_result
            else:
                final_data["errors"].append(f"OCR: {ocr_result.get('message', 'Unknown error')}")

        # ===== 4. VISION =====
        if symptom_photo_bytes:
            vision_result = self.vision_service.analyze_image(symptom_photo_bytes, symptom_photo_filename)
            if vision_result.get("status") == "success":
                final_data["visual_findings"] = vision_result
            else:
                final_data["errors"].append(f"Vision: {vision_result.get('message', 'Unknown error')}")

        if final_data["errors"]:
            final_data["status"] = "partial_success"

        return final_data