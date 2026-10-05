import os
import json
import base64
from groq import Groq
from openai import OpenAI


class OCRService:
    def __init__(self):
        # Primary: Groq
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None

        # Fallback: OpenRouter
        self.or_key = os.getenv("OPENROUTER_API_KEY")
        self.or_client = OpenAI(
            api_key=self.or_key,
            base_url="https://openrouter.ai/api/v1"
        ) if self.or_key else None

    def _get_mime_type(self, filename: str) -> str:
        ext = filename.lower().split(".")[-1]
        return {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "avif": "image/avif",
            "webp": "image/webp",
        }.get(ext, "image/png")

    def _build_prompt(self) -> str:
        return """You are a medical data extraction assistant. Analyze this medical report
(blood test, X-ray, prescription, discharge summary, or vitals chart).

Output ONLY a valid JSON object:
{
  "report_type": "blood_test|xray|prescription|discharge_summary|vitals_chart|other",
  "patient_info": {"age": null, "sex": null, "date": null},
  "vital_signs": {
    "bp": null,
    "heart_rate": null,
    "spo2": null,
    "temperature": null,
    "respiratory_rate": null
  },
  "lab_values": [{"name": "", "value": "", "unit": "", "flag": "low|normal|high"}],
  "key_findings": [],
  "medications": [{"name": "", "dosage": "", "frequency": ""}],
  "abnormal_flags": []
}

Rules:
- Extract ONLY visibly written values. Do NOT invent anything.
- Reference ranges (like 60-100) are NOT patient values — return null for those.
- Output ONLY the JSON object. No markdown, no commentary."""

    def extract_report_data(self, file_bytes: bytes, filename: str) -> dict:
        print(f"Extracting data from {filename}...")
        mime_type = self._get_mime_type(filename)
        prompt = self._build_prompt()
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")

        # --- 1. Try Groq (Primary) ---
        if self.groq_client:
            try:
                print("  Trying Groq OCR...")
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
                    temperature=0.1,
                    max_tokens=1500,
                )
                content = response.choices[0].message.content
                if content:
                    cleaned = content.strip().replace("```json", "").replace("```", "")
                    data = json.loads(cleaned)
                    data["status"] = "success"
                    data["source"] = "groq"
                    print("  ✅ Groq OCR succeeded.")
                    return data
            except Exception as e:
                print(f"  ❌ Groq failed: {str(e)[:120]}")

        # --- 2. Try OpenRouter (Fallback) ---
        if self.or_client:
            or_models = [
                "meta-llama/llama-3.2-90b-vision-instruct:free",
                "qwen/qwen-2.5-vl-72b-instruct:free",
                "meta-llama/llama-3.2-11b-vision-instruct:free",
            ]
            for model in or_models:
                try:
                    print(f"  Trying OpenRouter: {model}")
                    response = self.or_client.chat.completions.create(
                        model=model,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url",
                                 "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
                            ]
                        }],
                        temperature=0.1,
                    )
                    content = response.choices[0].message.content
                    if content:
                        cleaned = content.strip().replace("```json", "").replace("```", "")
                        data = json.loads(cleaned)
                        data["status"] = "success"
                        data["source"] = "openrouter"
                        print(f"  ✅ OpenRouter OCR succeeded ({model}).")
                        return data
                except Exception as e:
                    print(f"  ❌ {model} failed: {str(e)[:120]}")

        # --- 3. All Failed ---
        return {
            "status": "error",
            "message": "All OCR providers unavailable. Please try again or enter values manually.",
            "source": "none",
        }