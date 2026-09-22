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
        symptom_photo_filename: str = "photo.png",
    ) -> dict:
        """Full multimodal pipeline: Audio + Text + OCR + Vision + PII Redaction."""

        final_data = {
            "status": "success",
            "raw_text": "",
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

        # 1. Audio or Text
        if audio_path:
            audio_result = self.audio_service.process_audio(audio_path)
            if audio_result.get("status") == "low_confidence":
                return audio_result
            final_data["raw_text"] = audio_result.get("original_transcription", "")
            final_data["translation"] = audio_result.get("translation", "")
            final_data["symptoms"] = audio_result.get("symptoms", [])
            final_data["duration"] = audio_result.get("duration", "")
            final_data["severity"] = audio_result.get("severity", "")
            final_data["follow_up_questions"] = audio_result.get("follow_up_questions", [])
            final_data["confidence_score"] = audio_result.get("confidence_score", 0.0)
        elif text_input:
            final_data["raw_text"] = text_input
            final_data["translation"] = text_input

        # 2. Lab Reports (OCR)
        if lab_report_bytes:
            ocr_result = self.ocr_service.extract_report_data(lab_report_bytes, lab_report_filename)
            if ocr_result.get("status") == "success":
                final_data["report_data"] = ocr_result
            else:
                final_data["errors"].append(f"OCR: {ocr_result.get('message', 'Unknown error')}")

        # 3. Vision (Photos)
        if symptom_photo_bytes:
            vision_result = self.vision_service.analyze_image(symptom_photo_bytes, symptom_photo_filename)
            if vision_result.get("status") == "success":
                final_data["visual_findings"] = vision_result
            else:
                final_data["errors"].append(f"Vision: {vision_result.get('message', 'Unknown error')}")

        # 4. PII Redaction
        final_data["raw_text"] = PIIService.redact(final_data["raw_text"])
        final_data["translation"] = PIIService.redact(final_data["translation"])

        # If any errors, mark partial success
        if final_data["errors"]:
            final_data["status"] = "partial_success"

        return final_data

    def process_manual_inputs(
        self,
        text_input: str = None,
        manual_vitals: dict = None,
        manual_visual_finding: str = None,
    ) -> dict:
        """Manual nurse/patient input — no external APIs."""
        final_data = {
            "status": "success",
            "raw_text": text_input or "",
            "translation": text_input or "",
            "report_data": {"vital_signs": manual_vitals or {}} if manual_vitals else None,
            "visual_findings": {"finding": manual_visual_finding, "confidence": 1.0} if manual_visual_finding else None,
            "confidence_score": 1.0,
            "source": "manual",
        }
        final_data["raw_text"] = PIIService.redact(final_data["raw_text"])
        final_data["translation"] = PIIService.redact(final_data["translation"])
        return final_data