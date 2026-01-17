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

def resolve_voice_id(voice: str, client) -> str:
    """Resolve a voice name or ID to a voice ID.

    Priority:
    1. Preset voice names (adam, bob, william, george)
    2. Custom voice name lookup via ElevenLabs API
    3. Assume it's already a voice ID
    """
    # Check preset names first
    if voice.lower() in ELEVENLABS_VOICES:
        return ELEVENLABS_VOICES[voice.lower()]

    # Query ElevenLabs API for custom voices by name
    try:
        response = client.voices.get_all()
        for v in response.voices:
            if v.name.lower() == voice.lower():
                return v.voice_id
    except Exception:
        pass  # Fall through to treating it as a voice ID

    # Assume it's already a voice ID
    return voice


def generate_slide_audio_elevenlabs(
    text: str,
    output_path: Path,
    voice: str = "george",
    client=None
) -> Path:
    """Generate audio using ElevenLabs API and convert to WAV for consistency."""
    if client is None:
        client = get_elevenlabs_client()

    # Resolve voice name to ID (supports presets, custom names, or direct IDs)
    voice_id = resolve_voice_id(voice, client)

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