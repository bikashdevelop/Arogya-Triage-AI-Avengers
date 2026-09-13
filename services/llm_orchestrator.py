import os
import json
import httpx
from dotenv import load_dotenv
from config import settings

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a NON-DIAGNOSTIC medical triage summarizer for a rural Indian Primary Health Centre.

You MUST output ONLY valid JSON in this exact format:
{
  "summary": "1-2 sentence clinical summary of the patient's presentation",
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
- Output RAW JSON only. No markdown. No explanations.
- Do NOT assign priority (P1-P4). A separate rule engine handles that.
"""


def build_user_prompt(symptoms_text: str, vitals: dict) -> str:
    return f"""Symptoms: {symptoms_text}

Vitals:
BP: {vitals.get('bp_systolic')}/{vitals.get('bp_diastolic')} mmHg
HR: {vitals.get('heart_rate')} bpm
SpO2: {vitals.get('spo2')}%
Temp: {vitals.get('temperature_f')} F
RR: {vitals.get('respiratory_rate')}/min

Return JSON now."""


async def generate_clinical_summary(symptoms_text: str, vitals: dict) -> dict:
    api_key = settings.GROQ_API_KEY

    if not api_key:
        return _fallback(symptoms_text, "GROQ_API_KEY not set")

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(symptoms_text, vitals)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=settings.GROQ_TIMEOUT_SECONDS) as client:
            r = await client.post(GROQ_URL, json=payload, headers=headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            result["_source"] = "groq"
            return result
    except Exception as e:
        print(f"[Groq error] {e}")
        return _fallback(symptoms_text, str(e))


def _fallback(symptoms_text: str, error: str) -> dict:
    return {
        "_source": "fallback",
        "_error": error,
        "summary": symptoms_text[:200] or "Patient presentation recorded.",
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