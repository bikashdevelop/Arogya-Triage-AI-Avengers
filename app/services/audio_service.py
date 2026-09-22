import os
import math
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class AudioService:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            print("WARNING: GROQ_API_KEY not found in .env")
        self.groq_client = Groq(api_key=self.groq_api_key)

    def transcribe_audio(self, audio_path: str) -> tuple:
        """Groq Whisper → (text, confidence_score)."""
        try:
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
            return text, math.exp(avg_logprob)
        except Exception as e:
            print(f"Groq STT failed: {e}")
            return "", 0.0

    def refine_with_groq(self, text: str, source_lang: str) -> dict:
        """Groq LLM: translate Hindi → English + extract structured data."""
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
            "You receive a transcript of a patient describing their symptoms in Hindi, Odia, or English.\n\n"
            "Your tasks:\n"
            "1. TRANSLATE the transcript into natural, complete English. "
            "Keep ALL information including the patient's name as spoken "
            "(the name will be redacted later by another system). "
            "Example: 'मेरा नाम जितेन्द्र सती है, मुझे बुखार है' → "
            "'My name is Jitendra Sati, I have a fever.'\n"
            "2. Extract the SYMPTOMS list.\n"
            "3. Extract the DURATION if mentioned.\n"
            "4. Extract the SEVERITY if mentioned.\n"
            "5. Generate 3 FOLLOW-UP questions for a nurse.\n\n"
            "Output ONLY a valid JSON object with these exact keys:\n"
            "{\n"
            "  \"translation\": \"<natural English translation>\",\n"
            "  \"symptoms\": [\"...\"],\n"
            "  \"duration\": \"...\",\n"
            "  \"severity\": \"...\",\n"
            "  \"follow_up_questions\": [\"...\", \"...\", \"...\"]\n"
            "}\n"
            "No commentary, no markdown, no code fences."
        )

        models_to_try = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b",
        ]

        for model in models_to_try:
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

    def process_audio(self, audio_path: str) -> dict:
        """Full pipeline: transcribe → confidence gate → translate + extract."""
        print(f"Processing audio file: {audio_path}")

        text, confidence = self.transcribe_audio(audio_path)
        print(f"Groq STT output: {text}")
        print(f"Confidence Score: {confidence:.2%}")

        if confidence < 0.60:
            return {
                "status": "low_confidence",
                "message": "We couldn't hear you clearly. Please re-record in a quieter place.",
                "confidence_score": confidence,
                "original_transcription": text,
            }

        extracted = self.refine_with_groq(text, "auto")

        return {
            "status": "success",
            "confidence_score": confidence,
            "original_transcription": text,
            "translation": extracted.get("translation", ""),
            "symptoms": extracted.get("symptoms", []),
            "duration": extracted.get("duration", ""),
            "severity": extracted.get("severity", ""),
            "follow_up_questions": extracted.get("follow_up_questions", []),
        }