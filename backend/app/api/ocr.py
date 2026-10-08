"""
OCR endpoint — extracts ALL details from medical reports dynamically.
Uses OpenRouter vision models.
"""
from fastapi import APIRouter, UploadFile, File
import os
import json
import base64
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
logger = logging.getLogger("aarogyatriage.ocr")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 👈 FIXED: Strongest, most reliable OCR models first
OPENROUTER_MODELS = [
    "openai/gpt-4o-mini",                       # Best for complex forms
    "qwen/qwen-2.5-vl-72b-instruct",            # Excellent fallback
    "meta-llama/llama-3.2-11b-vision-instruct", # Last resort
]


def _mime(filename: str) -> str:
    ext = (filename or "").lower().split(".")[-1]
    return {
        "pdf": "application/pdf", "png": "image/png",
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "avif": "image/avif", "webp": "image/webp",
    }.get(ext, "image/png")


# 👈 FIXED: Extremely thorough prompt to extract EVERYTHING
PROMPT_TEMPLATE = """You are a highly precise medical OCR assistant.

Analyze this image: {filename}

TASK: Extract ALL text, measurements, checkboxes, and values from this medical document.

CRITICAL RULES:
1. DO NOT guess or invent values.
2. Extract EVERYTHING visible: patient name, age, sex, passport number, blood pressure, blood group, test names, results, dates, doctor names, physical exam findings, etc.
3. If a section is blank or unreadable, skip it. Do not output null.
4. Even if it is NOT a standard blood test (e.g., a fitness certificate), you MUST extract the fields as key-value pairs.

Output ONLY this JSON format (no markdown, no explanation):
{{
  "report_type": "blood_test | prescription | fitness_certificate | xray | other",
  "patient_info": {{
    "name": "exact name or null",
    "age": "exact age or null",
    "sex": "exact sex or null"
  }},
  "extracted_values": [
    {{"name": "Field or Test Name", "value": "exact value", "unit": "unit or empty string"}},
    {{"name": "Blood Pressure", "value": "110/70", "unit": "mmHg"}},
    {{"name": "Blood Group", "value": "B+", "unit": ""}},
    {{"name": "Malaria", "value": "Absent", "unit": ""}},
    {{"name": "Doctor Name", "value": "Dr. A. Sharma", "unit": ""}}
  ]
}}"""


def _strip_fences(text: str) -> str:
    for fence in ("```json", "```JSON", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def _try_openrouter(contents: bytes, mime: str, filename: str) -> dict:
    """Try to extract data via OpenRouter."""
    if not OPENROUTER_API_KEY:
        return {"ok": False, "error": "OPENROUTER_API_KEY not set"}

    b64 = base64.b64encode(contents).decode("utf-8")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AarogyaTriage",
    }

    prompt = PROMPT_TEMPLATE.format(filename=filename)
    last_error = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        for model in OPENROUTER_MODELS:
            try:
                logger.info("OCR trying OpenRouter model: %s", model)
                payload = {
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url",
                             "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    }],
                    "temperature": 0.0,
                    "max_tokens": 2000,
                }
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers, json=payload,
                )
                if resp.status_code != 200:
                    last_error = f"{model}: HTTP {resp.status_code}"
                    continue

                body = resp.json()
                text = _strip_fences(body["choices"][0]["message"]["content"])
                data = json.loads(text)
                data["_source"] = f"openrouter/{model}"
                logger.info("✓ OCR via OpenRouter %s", model)
                return {"ok": True, "data": data}

            except Exception as e:
                last_error = f"{model}: {str(e)[:120]}"
                logger.warning("OpenRouter OCR %s failed: %s", model, last_error)
                continue

    return {"ok": False, "error": f"OpenRouter: {last_error}"}


@router.post("/ocr/extract")
async def extract_report(file: UploadFile = File(...)):
    try:
        contents = await file.read()
    except Exception as e:
        return {"success": False, "error": f"Could not read file: {e}"}

    if not contents or len(contents) < 100:
        return {"success": False, "error": "File is empty or too small"}

    mime = _mime(file.filename)
    logger.info("OCR request — %s (%d bytes)", mime, len(contents))

    result = await _try_openrouter(contents, mime, file.filename)
    if result["ok"]:
        return {"success": True, "data": result["data"]}

    return {
        "success": False,
        "error": f"All OCR providers failed. {result['error']}",
        "data": {"extracted_values": [], "_source": "none"},
    }


@router.post("/reports/extract")
async def extract_report_alias(file: UploadFile = File(...)):
    return await extract_report(file)