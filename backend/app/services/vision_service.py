import os
import json
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class VisionService:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None

    def analyze_image(self, image_bytes: bytes, filename: str = "photo.png") -> dict:
        print(f"Analyzing {filename}...")

        if not self.groq_client:
            return {"status": "error", "message": "GROQ_API_KEY not set"}

        ext = filename.lower().split(".")[-1]
        mime_type = {
            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "avif": "image/avif", "webp": "image/webp",
        }.get(ext, "image/png")

        prompt = """Describe what you see in this medical image in ONE sentence.
Include the body part and visible features (color, swelling, wound, rash).
Do NOT diagnose. Plain English, no JSON, no markdown."""

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

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
                max_tokens=300,
            )
            finding = response.choices[0].message.content.strip()
            return {
                "status": "success",
                "finding": finding,
                "location": "",
                "characteristics": [],
                "confidence": 0.9,
                "source": "groq/qwen3.8-27b",
            }
        except Exception as e:
            print(f"Groq Vision failed: {str(e)[:200]}")
            return {"status": "error", "message": str(e)[:200]}