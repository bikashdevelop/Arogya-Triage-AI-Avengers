import os
import math
import json
import requests
from groq import Groq
from dotenv import load_dotenv
from app.services.pii_service import PIIService

load_dotenv()


class AudioService:
    def __init__(self):
        # Groq for LLM refinement (translation, symptom extraction)
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            print("WARNING: GROQ_API_KEY not found in .env")
        self.groq_client = Groq(api_key=self.groq_api_key)

        # Sarvam AI for Odia + Indian language STT
        self.sarvam_api_key = os.getenv("SARVAM_API_KEY")
        if not self.sarvam_api_key:
            print("WARNING: SARVAM_API_KEY not found in .env — Odia support disabled")

    # ═══════════════════════════════════════════════════════════
    # SPEECH-TO-TEXT — Sarvam AI primary, Groq Whisper fallback
    # ═══════════════════════════════════════════════════════════
    def transcribe_audio(self, audio_path: str, language: str = "auto") -> tuple:
        """
        Transcribe audio. Uses Sarvam AI for Indian languages (esp. Odia),
        falls back to Groq Whisper if Sarvam fails or key is missing.

        Returns: (text, confidence_score)
        """
        # Try Sarvam AI first (best for Odia, Hindi, Bengali, Tamil, etc.)
        if self.sarvam_api_key:
            text, confidence = self._transcribe_with_sarvam(audio_path, language)
            if text:
                return text, confidence
            print("  ⚠️  Sarvam failed. Falling back to Groq Whisper...")

        # Fallback: Groq Whisper
        return self._transcribe_with_groq(audio_path)

    def _transcribe_with_sarvam(self, audio_path: str, language: str) -> tuple:
        """Transcribe with Sarvam AI (Saaras v3). Best for Odia."""
        try:
            # Map UI language to Sarvam language code
            lang_map = {
                "auto": "unknown",
                "en": "en-IN",
                "hi": "hi-IN",
                "or": "od-IN",     # Odia
                "bn": "bn-IN",     # Bengali
                "ta": "ta-IN",     # Tamil
                "te": "te-IN",     # Telugu
                "mr": "mr-IN",     # Marathi
                "gu": "gu-IN",     # Gujarati
                "kn": "kn-IN",     # Kannada
                "ml": "ml-IN",     # Malayalam
                "pa": "pa-IN",     # Punjabi
                "as": "as-IN",     # Assamese
            }
            language_code = lang_map.get(language.lower(), "unknown")

            print(f"  🎤 Trying Sarvam AI (language={language_code})...")

            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                data = {
                    "model": "saaras:v3",
                    "language_code": language_code,
                }
                headers = {"api-subscription-key": self.sarvam_api_key}

                response = requests.post(
                    "https://api.sarvam.ai/speech-to-text",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=60,
                )

            response.raise_for_status()
            result = response.json()

            transcript = result.get("transcript", "").strip()

            if not transcript:
                print("  ❌ Sarvam returned empty transcript")
                return "", 0.0

            # Sarvam doesn't return confidence; use a high default
            confidence = 0.95
            print(f"  ✅ Sarvam transcription: {transcript[:80]}...")
            return transcript, confidence

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Sarvam API failed: {str(e)[:150]}")
            return "", 0.0
        except Exception as e:
            print(f"  ❌ Sarvam unexpected error: {str(e)[:150]}")
            return "", 0.0

    def _transcribe_with_groq(self, audio_path: str) -> tuple:
        """Fallback: Groq Whisper."""
        try:
            print("  🎤 Trying Groq Whisper (fallback)...")
            with open(audio_path, "rb") as file:
                response = self.groq_client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json",
                )
            text = response.text
            if response.segments:
                segment = response.segments[0]
                avg_logprob = (
                    segment.get("avg_logprob", -10.0)
                    if isinstance(segment, dict)
                    else getattr(segment, "avg_logprob", -10.0)
                )
            else:
                avg_logprob = -10.0
            confidence = math.exp(avg_logprob)
            print(f"  ✅ Groq Whisper succeeded (conf: {confidence:.2%})")
            return text, confidence
        except Exception as e:
            print(f"  ❌ Groq STT failed: {e}")
            return "", 0.0

    # ═══════════════════════════════════════════════════════════
    # LLM REFINEMENT (unchanged)
    # ═══════════════════════════════════════════════════════════
    def refine_with_groq(self, text: str, source_lang: str = "auto") -> dict:
        """Groq LLM: translate + extract structured data. Receives REDACTED text only."""
        empty = {
            "translation": text,
            "symptoms": [],
            "duration": "",
            "severity": "",
            "follow_up_questions": [],
        }
        if not text:
            return empty

        system_prompt = (
            "You are a medical triage assistant for Indian government hospitals.\n"
            "Analyze the patient transcript and output ONLY a valid JSON object with these exact keys:\n"
            "1. 'translation': Clear, professional English translation of the transcript.\n"
            "2. 'symptoms': A list of identified symptoms (e.g., ['fever', 'headache']).\n"
            "3. 'duration': How long the symptoms lasted (e.g., '3 days').\n"
            "4. 'severity': The reported severity (e.g., 'mild', 'moderate', 'severe').\n"
            "5. 'follow_up_questions': A list of 3 clinical questions for a nurse to ask.\n"
            "Output ONLY the JSON object. No commentary, no markdown, no code fences."
        )

        for model in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]:
            try:
                response = self.groq_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Transcript:\n{text}"},
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                print(f"  ✅ Used Groq LLM: {model}")
                return json.loads(response.choices[0].message.content.strip())
            except Exception as e:
                print(f"  ❌ {model} failed: {str(e)[:100]}")
                continue

        print("All Groq LLMs failed. Returning raw transcript.")
        return empty

    # ═══════════════════════════════════════════════════════════
    # FULL PIPELINE
    # ═══════════════════════════════════════════════════════════
    def process_audio(self, audio_path: str, language: str = "auto") -> dict:
        """Full pipeline: transcribe → extract name → redact → send redacted to LLM."""
        print(f"\n🎧 Processing audio file: {audio_path}")

        # STEP 1: Transcribe (Sarvam for Odia, Groq fallback)
        raw_text, confidence = self.transcribe_audio(audio_path, language)
        print(f"STT output: {raw_text}")
        print(f"Confidence Score: {confidence:.2%}")

        if not raw_text:
            return {
                "status": "error",
                "message": "Transcription failed. Please try again.",
                "confidence_score": 0.0,
                "original_transcription": "",
            }

        if confidence < 0.60:
            return {
                "status": "low_confidence",
                "message": "We couldn't hear you clearly. Please re-record in a quieter place.",
                "confidence_score": confidence,
                "original_transcription": raw_text,
            }

        # STEP 2: Extract real names (for doctor) BEFORE redaction
        real_names = PIIService.extract_names(raw_text)
        print(f"  🔒 Extracted {len(real_names)} name(s) for doctor: {real_names}")

        # STEP 3: Redact names + IDs BEFORE sending to LLM
        redacted_text = PIIService.redact(raw_text)
        print(f"  🔒 Redacted text sent to LLM: {redacted_text[:80]}...")

        # STEP 4: Send REDACTED text to LLM
        extracted = self.refine_with_groq(redacted_text, "auto")

        return {
            "status": "success",
            "confidence_score": confidence,
            "patient_name": ", ".join(real_names) if real_names else "Unknown",
            "original_transcription": raw_text,
            "redacted_transcription": redacted_text,
            "translation": extracted.get("translation", ""),
            "symptoms": extracted.get("symptoms", []),
            "duration": extracted.get("duration", ""),
            "severity": extracted.get("severity", ""),
            "follow_up_questions": extracted.get("follow_up_questions", []),
        }