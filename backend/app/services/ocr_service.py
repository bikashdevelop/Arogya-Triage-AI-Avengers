import os
import json
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class OCRService:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None

    def _get_mime_type(self, filename: str) -> str:
        ext = filename.lower().split(".")[-1]
        return {
            "pdf": "application/pdf", "png": "image/png",
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "avif": "image/avif", "webp": "image/webp",
        }.get(ext, "image/png")

    def extract_report_data(self, file_bytes: bytes, filename: str) -> dict:
        print(f"Extracting data from {filename}...")

        if not self.groq_client:
            return {"status": "error", "message": "GROQ_API_KEY not set"}

        mime_type = self._get_mime_type(filename)
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")

        prompt = """Look at this medical report image. Read it VERY CAREFULLY.
Extract ONLY what is literally written. Do NOT guess.

Output ONLY this JSON (no markdown):
{
  "report_type": "blood_test or xray or prescription or other",
  "patient_info": {"age": "age or null", "sex": "MALE or FEMALE or null", "date": "date or null"},
  "vital_signs": {"bp": "BP or null", "heart_rate": "HR or null", "spo2": "SpO2 or null", "temperature": "temp or null"},
  "lab_values": [{"name": "Test Name", "value": "measured value", "unit": "unit", "flag": "low or normal or high"}],
  "abnormal_flags": ["values marked as low or high"]
}"""

        try:
            response = self.groq_client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
                    ]
                }],
                temperature=0.0,
                max_tokens=2000,
            )
            content = response.choices[0].message.content
            cleaned = content.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            data["status"] = "success"
            data["source"] = "groq/qwen3.8-27b"
            return data
        except Exception as e:
            print(f"Groq OCR failed: {str(e)[:200]}")
            return {"status": "error", "message": str(e)[:200]}