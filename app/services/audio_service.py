import os
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AudioService:
    def __init__(self):
        # 1. Setup Groq Client for Speech-to-Text (STT)
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            print("WARNING: GROQ_API_KEY not found in .env file.")
        self.groq_client = Groq(api_key=self.groq_api_key)

        # 2. Setup OpenRouter Client for Translation/Refinement
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            print("WARNING: OPENROUTER_API_KEY not found in .env file.")
            
        self.client = OpenAI(
            api_key=self.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )

    def transcribe_audio(self, audio_path: str, language: str = "en") -> str:
        """Step 1: Uses Groq's Whisper API to turn audio into text."""
        try:
            with open(audio_path, "rb") as file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file.read()),
                    model="whisper-large-v3-turbo",
                    language=language if language != "auto" else None,
                    response_format="text",
                )
            return transcription
        except Exception as e:
            print(f"Groq STT failed: {e}")
            return ""

    def refine_with_deepseek(self, text: str, source_lang: str) -> str:
        """Step 2: Uses OpenRouter (DeepSeek) to translate and refine the text."""
        if not self.openrouter_api_key or not text:
            return text

        system_prompt = (
            "You are a medical triage assistant. The user will provide a transcript "
            "of a patient describing their symptoms. Your task is to:\n"
            "1. Translate the text to clear, professional English if it is in another language.\n"
            "2. Correct any grammatical errors or disfluencies.\n"
            "3. Output ONLY the final refined English text. Do not add any commentary."
        )
        
        user_prompt = f"Source Language Hint: {source_lang}\n\nTranscript:\n{text}"

        try:
            response = self.client.chat.completions.create(
                model="deepseek/deepseek-r1:free", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenRouter refinement failed: {e}")
            return text # Fallback to raw text

    def process_audio(self, audio_path: str, language: str = "en") -> dict:
        """The main function you will call from the backend."""
        print(f"Processing audio file: {audio_path}")
        
        transcribed_text = self.transcribe_audio(audio_path, language)
        print(f"Groq output: {transcribed_text}")
        
        refined_english_text = self.refine_with_deepseek(transcribed_text, language)
        print(f"OpenRouter output: {refined_english_text}")

        return {
            "original_transcription": transcribed_text,
            "english_translation": refined_english_text,
            "detected_language": language
        }