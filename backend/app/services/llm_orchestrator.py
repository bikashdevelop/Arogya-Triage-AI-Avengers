"""
app/services/llm_orchestrator.py

Two responsibilities:
  1. generate_clinical_summary  → OpenRouter chat, SOAP note + timeline + gaps
  2. transcribe_audio           → Sarvam AI STT, optional translation

Both use httpx directly (matching the existing pattern) and never raise.
"""
import os
import json
import httpx
from dotenv import load_dotenv
from config import settings

load_dotenv()

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

# 👈 FIXED: Switched to OpenRouter for smarter summaries
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini" 

SARVAM_STT_URL = (
    getattr(settings, "SARVAM_STT_URL", None)
    or os.getenv("SARVAM_STT_URL")
    or "https://api.sarvam.ai/speech-to-text"
)
SARVAM_STT_MODEL = (
    getattr(settings, "SARVAM_STT_MODEL", None)
    or os.getenv("SARVAM_STT_MODEL")
    or "saarika:v2"
)
SARVAM_TIMEOUT_SECONDS = float(
    getattr(settings, "SARVAM_TIMEOUT_SECONDS", None)
    or os.getenv("SARVAM_TIMEOUT_SECONDS")
    or "60"
)
SARVAM_API_KEY = (
    getattr(settings, "SARVAM_API_KEY", None)
    or os.getenv("SARVAM_API_KEY")
)

SARVAM_LANG_MAP = {"en": "en-IN", "hi": "hi-IN", "or": "od-IN"}
LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "or": "Odia"}

print(f"[llm_orchestrator] SARVAM_API_KEY: "
      f"{'set (…' + SARVAM_API_KEY[-4:] + ')' if SARVAM_API_KEY else 'NOT SET'}")
print(f"[llm_orchestrator] SARVAM model={SARVAM_STT_MODEL} url={SARVAM_STT_URL}")

# ═══════════════════════════════════════════════════════════
# CLINICAL SUMMARY (OpenRouter)
# ═══════════════════════════════════════════════════════════

# 👈 FIXED: Strict SOAP prompt + handling for non-medical documents
SYSTEM_PROMPT = """You are a NON-DIAGNOSTIC medical triage summarizer for a rural Indian Primary Health Centre.

You MUST write a detailed clinical SOAP note based on the input provided.
You MUST output ONLY valid JSON in this exact format:
{
  "summary": "**Subjective:**\n<Chief complaint, history, symptoms>\n\n**Objective:**\n<Vitals, lab findings>\n\n**Assessment:**\n<Triage priority, clinical impression>\n\n**Plan:**\n<Next steps, missing information needed>",
  "timeline": [
    {"time": "08:30 AM", "event": "Symptom onset described by patient"},
    {"time": "09:15 AM", "event": "Arrival at PHC triage desk"}
  ],
  "identified_gaps": [
    "Missing clinical info 1",
    "Missing clinical info 2"
  ],
  "follow_up_questions": [
    {"id": "Q1", "text": "Question for the nurse", "target": "nurse"},
    {"id": "Q2", "text": "Question for the nurse", "target": "nurse"},
    {"id": "Q3", "text": "Question for the nurse", "target": "nurse"}
  ]
}

RULES:
- NEVER diagnose a condition. NEVER prescribe medication.
- Use neutral phrasing like "Requires Physician Confirmation".
- If unsure about something, add it to identified_gaps.
- Output RAW JSON only. No markdown outside the JSON. No explanations.
- Do NOT assign priority (P1-P4). A separate rule engine handles that.
- If the input contains NON-MEDICAL data (like school marks, unrelated documents), IGNORE it completely and state in the "Assessment" section: "Non-medical document detected. Clinical assessment pending."
"""


def build_user_prompt(symptoms_text: str, vitals: dict, duration: str = None, severity: str = None, medical_history: str = None, allergies: str = None, medications: str = None) -> str:
    return f"""Symptoms: {symptoms_text}
Duration: {duration or 'Not provided'}
Severity: {severity or 'Not provided'}
Medical History: {medical_history or 'None'}
Allergies: {allergies or 'None'}
Medications: {medications or 'None'}

Vitals:
BP: {vitals.get('bp_systolic')}/{vitals.get('bp_diastolic')} mmHg
HR: {vitals.get('heart_rate')} bpm
SpO2: {vitals.get('spo2')}%
Temp: {vitals.get('temperature_f')} F
RR: {vitals.get('respiratory_rate')}/min

Return JSON now."""


async def generate_clinical_summary(symptoms_text: str, vitals: dict, duration: str = None, severity: str = None, medical_history: str = None, allergies: str = None, medications: str = None) -> dict:
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        return _fallback(symptoms_text, "OPENROUTER_API_KEY not set")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(symptoms_text, vitals, duration, severity, medical_history, allergies, medications)},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AarogyaTriage",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            
            # Strip markdown fences if present
            for fence in ("```json", "```JSON", "```"):
                if content.startswith(fence):
                    content = content[len(fence):]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                result = {
                    "summary": content,
                    "timeline": [],
                    "identified_gaps": ["AI returned unstructured text."],
                    "follow_up_questions": []
                }
            
            result["_source"] = f"openrouter/{OPENROUTER_MODEL}"
            return result
    except Exception as e:
        print(f"[OpenRouter error] {e}")
        return _fallback(symptoms_text, str(e))


def _fallback(symptoms_text: str, error: str) -> dict:
    return {
        "_source": "fallback",
        "_error": error,
        "summary": (
            "**Subjective:**\n"
            f"{symptoms_text[:300] or 'Patient symptoms recorded.'}\n\n"
            "**Objective:**\n"
            "Vitals recorded as per triage form.\n\n"
            "**Assessment:**\n"
            "AI SOAP generation unavailable due to a backend error. "
            "Manual clinical review required. Non-diagnostic.\n\n"
            "**Plan:**\n"
            "1. Clinician to review raw symptoms and vitals.\n"
            "2. Collect missing information (allergies, medications, history).\n"
            "3. Re-generate summary once backend issue is resolved."
        ),
        "timeline": [
            {"time": "Onset", "event": "Patient reported symptoms"},
            {"time": "Now", "event": "Arrived at PHC triage desk"},
        ],
        "identified_gaps": [
            "Current medications",
            "Known allergies",
            "Prior medical history",
        ],
        "follow_up_questions": [
            {"id": "Q1", "text": "Have you noticed any dizziness or fainting?", "target": "nurse"},
            {"id": "Q2", "text": "Can you keep fluids down?", "target": "nurse"},
            {"id": "Q3", "text": "Any family member with the same symptoms?", "target": "nurse"},
        ],
    }

# ═══════════════════════════════════════════════════════════
# SPEECH TRANSCRIPTION (Sarvam AI)
# ═══════════════════════════════════════════════════════════

TRANSLATE_SYSTEM_PROMPT = (
    "You are a medical translator. Translate the user's clinical narrative into "
    "clear, plain English suitable for a clinician's SOAP note. Preserve symptom "
    "names, durations, and any numbers exactly. Do NOT add interpretation, do NOT "
    "summarize. Return ONLY the translated English text, no quotes, no labels."
)

def _empty_transcription(language: str, error: str) -> dict:
    return {
        "text": "",
        "original": "",
        "language": language,
        "translated": False,
        "_source": "fallback",
        "_error": error,
    }

def _translate_to_english(source_text: str) -> str:
    if not source_text or not source_text.strip():
        return source_text

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return source_text

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
            {"role": "user", "content": source_text},
        ],
        "temperature": 0.0,
        "max_tokens": 800,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": "AarogyaTriage",
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(OPENROUTER_URL, json=payload, headers=headers)
            r.raise_for_status()
            english = r.json()["choices"][0]["message"]["content"].strip()
            return english or source_text
    except Exception as e:
        print(f"[OpenRouter translate error] {e}")
        return source_text

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "voice.webm",
    language: str = "en",
) -> dict:
    lang = language if language in SARVAM_LANG_MAP else "en"
    sarvam_code = SARVAM_LANG_MAP[lang]

    if not SARVAM_API_KEY:
        msg = "SARVAM_API_KEY not set (check .env and config.py)"
        print(f"[Sarvam] {msg}")
        return _empty_transcription(lang, msg)

    headers = {"api-subscription-key": SARVAM_API_KEY}
    files = {
        "file": (
            filename or "voice.webm",
            audio_bytes,
            "audio/webm",
        ),
    }
    data = {
        "model": SARVAM_STT_MODEL,
        "language_code": sarvam_code,
    }

    print(f"[Sarvam] POST {SARVAM_STT_URL} "
          f"size={len(audio_bytes)} lang={sarvam_code} model={SARVAM_STT_MODEL}")

    try:
        with httpx.Client(timeout=SARVAM_TIMEOUT_SECONDS) as client:
            r = client.post(
                SARVAM_STT_URL,
                headers=headers,
                files=files,
                data=data,
            )
    except httpx.TimeoutException:
        msg = f"Sarvam request timed out after {SARVAM_TIMEOUT_SECONDS}s"
        print(f"[Sarvam] {msg}")
        return _empty_transcription(lang, msg)
    except Exception as e:
        msg = f"Sarvam request failed: {type(e).__name__}: {e}"
        print(f"[Sarvam] {msg}")
        return _empty_transcription(lang, msg)

    if r.status_code != 200:
        body = (r.text or "")[:400]
        msg = f"Sarvam HTTP {r.status_code}: {body}"
        print(f"[Sarvam] {msg}")
        return _empty_transcription(lang, msg)

    try:
        payload = r.json()
    except Exception:
        msg = f"Sarvam returned non-JSON: {r.text[:200]}"
        print(f"[Sarvam] {msg}")
        return _empty_transcription(lang, msg)

    original_text = (payload.get("transcript") or "").strip()
    if not original_text:
        msg = f"Sarvam returned empty transcript: {str(payload)[:200]}"
        print(f"[Sarvam] {msg}")
        return _empty_transcription(lang, msg)

    print(f"[Sarvam] ✓ transcript {len(original_text)} chars in {lang}")

    if lang == "en":
        return {
            "text": original_text,
            "original": original_text,
            "language": "en",
            "translated": False,
            "_source": f"sarvam/{SARVAM_STT_MODEL}",
            "_error": None,
        }

    english = _translate_to_english(original_text)
    translated = bool(english and english != original_text)

    return {
        "text": english or original_text,
        "original": original_text,
        "language": lang,
        "translated": translated,
        "_source": f"sarvam/{SARVAM_STT_MODEL}",
        "_error": None,
    }