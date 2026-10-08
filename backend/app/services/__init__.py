import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("aarogyatriage.services")


async def generate_clinical_summary(symptoms_text: str, vitals: dict) -> dict:
    """Generate AI-assisted clinical summary + timeline."""
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            return _fallback(symptoms_text)

        client = Groq(api_key=groq_key)

        system_prompt = (
            "You are a medical triage assistant. Output ONLY valid JSON:\n"
            "{\n"
            '  "summary": "1-2 sentence clinical summary",\n'
            '  "timeline": [{"time": "Day 1", "event": "..."}]\n'
            "}\n"
            "No diagnosis. No commentary."
        )

        user_prompt = f"Symptoms: {symptoms_text}\nVitals: {json.dumps(vitals)}"

        for model in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                data = json.loads(response.choices[0].message.content.strip())
                data["_source"] = f"groq/{model}"
                return data
            except Exception as e:
                logger.warning(f"Groq {model} failed: {str(e)[:80]}")
                continue

        return _fallback(symptoms_text)
    except Exception:
        logger.exception("Summary generation failed.")
        return _fallback(symptoms_text)


def _fallback(text: str) -> dict:
    return {
        "summary": f"Patient reports: {text[:180]}",
        "timeline": [],
        "_source": "fallback",
    }