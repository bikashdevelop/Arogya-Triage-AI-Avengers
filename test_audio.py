from app.services.audio_service import AudioService

if __name__ == "__main__":
    service = AudioService()
    
    # Make sure you have a file named test_sample.wav in this folder!
    audio_file_path = "test_sample.m4a" 
    
    result = service.process_audio(audio_file_path, language="en")
    
    print("\n--- FINAL RESULTS ---")
    print(f"Raw Transcription: {result['original_transcription']}")
    print(f"Refined English:   {result['english_translation']}")