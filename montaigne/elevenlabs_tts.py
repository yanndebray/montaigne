import subprocess
from pathlib import Path
from .config import get_elevenlabs_client

# Your specific voice list
ELEVENLABS_VOICES = {
    "adam": "6FiCmD8eY5VyjOdG5Zjk",
    "bob": "3nzyRCzDIWOtbkzj2qvj",
    "william": "8Es4wFxsDlHBmFWAOWRS",
    "george": "JBFqnCBsd6RMkjVDRZzb"
}

ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

def generate_slide_audio_elevenlabs(
    text: str, 
    output_path: Path, 
    voice: str = "george",
    client=None
) -> Path:
    """Generate audio using ElevenLabs API and convert to WAV for consistency."""
    if client is None:
        client = get_elevenlabs_client()

    # Map name to ID (case-insensitive)
    voice_id = ELEVENLABS_VOICES.get(voice.lower(), voice)

    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=ELEVENLABS_MODEL_ID,
        output_format="mp3_44100_128",
    )

   
    temp_mp3 = output_path.with_suffix(".mp3")
    with open(temp_mp3, "wb") as f:
        for chunk in audio_generator:
            if chunk: f.write(chunk)
            
    wav_path = output_path.with_suffix(".wav")
    
    # Use ffmpeg for the conversion
    subprocess.run([
        "ffmpeg", "-y", "-i", str(temp_mp3), str(wav_path)
    ], capture_output=True)
    
    if temp_mp3.exists():
        temp_mp3.unlink()
        
    return wav_path