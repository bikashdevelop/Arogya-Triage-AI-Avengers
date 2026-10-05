import os
import json
import base64
from groq import Groq
from openai import OpenAI


class VisionService:
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

    def analyze_image(self, image_bytes: bytes, filename: str = "photo.png") -> dict:
        print(f"Analyzing {filename} with Vision AI...")

        ext = filename.lower().split(".")[-1]
        mime_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "avif": "image/avif",
            "webp": "image/webp",
        }.get(ext, "image/png")

        prompt_text = """You are a medical triage assistant analyzing a clinical photograph.
Describe ONLY what is visibly present. Do NOT diagnose.

Output ONLY valid JSON:
{
  "finding": "A concise, one-sentence clinical description",
  "location": "Body location if visible",
  "characteristics": ["list", "of", "descriptors"],
  "confidence": 0.0
}

Rules:
- Use precise clinical terms (e.g., 'erythematous papules' not 'red bumps').
- If the image is unclear, set finding to 'Image unclear or non-clinical'.
- Do NOT diagnose. Do NOT prescribe."""

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # --- 1. Try Groq (Primary) ---
        if self.groq_client:
            try:
                print("  Trying Groq Vision...")
                response = self.groq_client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url",
                             "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
                        ]
                    }],
                    temperature=0.1,
                    max_tokens=500,
                )
                content = response.choices[0].message.content
                if content:
                    cleaned = content.strip().replace("```json", "").replace("```", "")
                    data = json.loads(cleaned)
                    data["status"] = "success"
                    data["source"] = "groq"
                    print(f"  ✅ Groq Vision: {data.get('finding', '')[:80]}")
                    return data
            except Exception as e:
                print(f"  ❌ Groq failed: {str(e)[:120]}")

        # --- 2. Try OpenRouter (Fallback) ---
        if self.or_client:
            or_models = [
                "meta-llama/llama-3.2-11b-vision-instruct:free",
                "qwen/qwen-2.5-vl-72b-instruct:free",
            ]
            for model in or_models:
                try:
                    print(f"  Trying OpenRouter: {model}")
                    response = self.or_client.chat.completions.create(
                        model=model,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
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
                        print(f"  ✅ OpenRouter Vision: {data.get('finding', '')[:80]}")
                        return data
                except Exception as e:
                    print(f"  ❌ {model} failed: {str(e)[:120]}")

        # --- 3. All Failed ---
        return {
            "status": "error",
            "message": "All vision providers unavailable. Please try again or enter the finding manually.",
            "source": "none",
        }