"""
Speech-to-text endpoint with dual-provider fallback.

Provider order:
    1. Sarvam AI        (best for Odia / Hindi / Indian languages)
    2. Groq Whisper     (auto-detects; reliable fallback)

If both fail, returns a clean error payload — never a silent empty string.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
logger = logging.getLogger("aarogyatriage.speech")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ═══════════════════════════════════════════════════════════
# SARVAM language codes (their accepted values)
# ═══════════════════════════════════════════════════════════
_SARVAM_LANGS = {
    "od-IN", "or-IN", "hi-IN", "en-IN", "bn-IN", "ta-IN",
    "te-IN", "mr-IN", "gu-IN", "kn-IN", "ml-IN", "pa-IN", "ur-IN",
}


# ═══════════════════════════════════════════════════════════
# PROVIDER 1 — SARVAM AI (saaras:v3)
# ═══════════════════════════════════════════════════════════
async def _transcribe_sarvam(audio_bytes: bytes, filename: str,
                             language_code: str) -> dict:
    if not SARVAM_API_KEY:
        return {"ok": False, "error": "SARVAM_API_KEY not set"}

    # Normalize Odia aliases
    lang = language_code or "od-IN"
    if lang in ("or-IN", "or"):
        lang = "od-IN"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {
                "file": (filename or "recording.webm", audio_bytes, "audio/webm"),
            }
            data = {
                "model": "saaras:v3",       # ← correct current model
                "language_code": lang,
            }
            headers = {"api-subscription-key": SARVAM_API_KEY}

            resp = await client.post(
                "https://api.sarvam.ai/speech-to-text",
                files=files, data=data, headers=headers,
            )

            if resp.status_code != 200:
                return {
                    "ok": False,
                    "error": f"Sarvam HTTP {resp.status_code}: {resp.text[:200]}",
                }

            payload = resp.json()
            transcript = (
                payload.get("transcript")
                or payload.get("text")
                or ""
            ).strip()

            if not transcript:
                return {"ok": False, "error": "Sarvam returned empty transcript"}

            return {
                "ok": True,
                "transcript": transcript,
                "language": payload.get("language_code", lang),
                "source": "sarvam/saaras-v3",
            }

    except (httpx.ConnectError, httpx.ConnectTimeout,
            httpx.ReadTimeout, httpx.HTTPError) as exc:
        return {"ok": False, "error": f"Sarvam network error: {str(exc)[:150]}"}
    except Exception as exc:
        logger.exception("Unexpected Sarvam error")
        return {"ok": False, "error": f"Sarvam error: {str(exc)[:150]}"}


# ═══════════════════════════════════════════════════════════
# PROVIDER 2 — GROQ WHISPER (auto-detect for Odia)
# ═══════════════════════════════════════════════════════════
# Whisper's documented language set does NOT include Odia ('or').
# For Odia we pass NO language → Whisper auto-detects the phonemes.
_GROQ_SUPPORTED = {
    "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "ur",
    "en", "as", "ne", "si", "sd", "sa",
}

_LANG_TO_GROQ = {
    "od-IN": None,   # Odia → auto-detect
    "or-IN": None,
    "hi-IN": "hi",
    "en-IN": "en",
    "bn-IN": "bn",
    "ta-IN": "ta",
    "te-IN": "te",
    "mr-IN": "mr",
    "gu-IN": "gu",
    "kn-IN": "kn",
    "ml-IN": "ml",
    "pa-IN": "pa",
    "ur-IN": "ur",
}


async def _transcribe_groq(audio_bytes: bytes, filename: str,
                           language_code: str) -> dict:
    if not GROQ_API_KEY:
        return {"ok": False, "error": "GROQ_API_KEY not set"}

    try:
        from groq import Groq
    except ImportError:
        return {"ok": False, "error": "groq package not installed"}

    try:
        client = Groq(api_key=GROQ_API_KEY)

        whisper_lang = _LANG_TO_GROQ.get(language_code or "", None)
        if whisper_lang and whisper_lang not in _GROQ_SUPPORTED:
            whisper_lang = None

        kwargs = {
            "file": (filename or "recording.webm", audio_bytes),
            "model": "whisper-large-v3",
            "response_format": "json",
            "temperature": 0.0,
        }
        if whisper_lang:
            kwargs["language"] = whisper_lang

        transcription = client.audio.transcriptions.create(**kwargs)
        transcript = (getattr(transcription, "text", "") or "").strip()

        if not transcript:
            return {"ok": False, "error": "Groq Whisper returned empty transcript"}

        return {
            "ok": True,
            "transcript": transcript,
            "language": whisper_lang or "auto",
            "source": "groq/whisper-large-v3",
        }

    except Exception as exc:
        logger.exception("Groq Whisper failed")
        return {"ok": False, "error": f"Groq Whisper error: {str(exc)[:200]}"}


# ═══════════════════════════════════════════════════════════
# MAIN ENDPOINT
# ═══════════════════════════════════════════════════════════
@router.post("/speech/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("od-IN"),
):
    """Transcribe audio → text. Tries Sarvam first, then Groq Whisper."""
    try:
        audio_bytes = await audio.read()
    except Exception as exc:
        raise HTTPException(400, detail=f"Could not read audio: {exc}")

    if not audio_bytes or len(audio_bytes) < 1000:
        raise HTTPException(
            400,
            detail=(
                "Audio file too small (need ≥1 second of speech). "
                "Please record again and speak for at least 2-3 seconds."
            ),
        )

    logger.info("Speech transcribe — size=%d bytes, lang=%s",
                len(audio_bytes), language)

    # ─── Try Sarvam ───
    logger.info("Attempting Sarvam AI (saaras:v3)...")
    sarvam_result = await _transcribe_sarvam(audio_bytes, audio.filename, language)
    if sarvam_result.get("ok"):
        logger.info("✓ Sarvam success: %s", sarvam_result["transcript"][:60])
        return {
            "success": True,
            "data": {
                "transcript": sarvam_result["transcript"],
                "language": sarvam_result["language"],
                "_source": sarvam_result["source"],
            },
        }

    logger.warning("Sarvam failed: %s — falling back to Groq Whisper",
                   sarvam_result.get("error"))

    # ─── Try Groq Whisper ───
    logger.info("Attempting Groq Whisper...")
    groq_result = await _transcribe_groq(audio_bytes, audio.filename, language)
    if groq_result.get("ok"):
        logger.info("✓ Groq Whisper success: %s", groq_result["transcript"][:60])
        return {
            "success": True,
            "data": {
                "transcript": groq_result["transcript"],
                "language": groq_result["language"],
                "_source": groq_result["source"],
            },
        }

    logger.error("Both providers failed — Sarvam: %s | Groq: %s",
                 sarvam_result.get("error"), groq_result.get("error"))

    return {
        "success": False,
        "error": (
            f"Speech transcription failed. "
            f"Sarvam: {sarvam_result.get('error', 'unknown')}. "
            f"Groq: {groq_result.get('error', 'unknown')}."
        ),
        "data": {"transcript": "", "language": language, "_source": "none"},
    }