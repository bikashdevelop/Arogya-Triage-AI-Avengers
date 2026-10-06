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
        print(f"📷 Analyzing {filename}...")

        if not self.groq_client:
            return {"status": "error", "message": "GROQ_API_KEY not set"}

        ext = filename.lower().split(".")[-1]
        mime_type = {
            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "avif": "image/avif", "webp": "image/webp",
        }.get(ext, "image/png")

        prompt = """You are analyzing ONE specific clinical photograph.

Look at THIS image. Describe ONLY what you can literally SEE in it.

Do NOT give a generic answer. Do NOT describe a rash unless there IS a rash.
Do NOT describe a wound unless there IS a wound.

If the image is unclear or not clinical, set finding to "Not a clinical photo".

Output ONLY this JSON (no markdown):
{
  "finding": "One sentence describing exactly what you see",
  "location": "Exact body part visible",
  "characteristics": ["specific", "visual", "features"],
  "confidence": 0.0
}"""

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        try:
            print("  Trying Groq: qwen/qwen3.8-27b...")
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
                max_tokens=500,
            )
            content = response.choices[0].message.content
            cleaned = content.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            data["status"] = "success"
            data["source"] = "groq/qwen-3.8"
            print(f"  ✅ Vision: {data.get('finding', '')[:70]}")
            return data
        except Exception as e:
            print(f"  ❌ Groq Vision failed: {str(e)[:200]}")
            return {"status": "error", "message": str(e)[:200]}