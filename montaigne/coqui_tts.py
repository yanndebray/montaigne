"""Local TTS generation using Coqui XTTS-v2."""

import tempfile
from pathlib import Path
from typing import Optional
from .logging import get_logger

logger = get_logger(__name__)

# Cache for loaded TTS model
_tts_model = None


class CoquiLoadError(Exception):
    """Raised when Coqui TTS cannot be loaded."""

    pass


# Default speaker/voice options for XTTS-v2
# These correspond to different voice characteristics
COQUI_VOICES = {
    "female": "Claribel Dervla",
    "male": "Damien Black",
    "neutral": "Damien Black",
}

DEFAULT_VOICE = "female"
DEFAULT_LANGUAGE = "en"


def get_tts_model():
    """Get or initialize the Coqui TTS model (lazy loading)."""
    global _tts_model

    if _tts_model is not None:
        return _tts_model

    try:
        from TTS.api import TTS

        logger.info("Loading Coqui XTTS-v2 model (this may take a moment)...")

        # Load XTTS-v2 model
        _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

        logger.info("Coqui XTTS-v2 model loaded successfully")
        return _tts_model

    except ImportError as e:
        raise CoquiLoadError(
            "Coqui TTS not installed. Install with:\n"
            "  pip install montaigne[coqui]\n"
            "Or manually:\n"
            "  pip install TTS torch"
        ) from e
    except Exception as e:
        raise CoquiLoadError(f"Failed to load Coqui TTS model: {e}") from e


def generate_slide_audio_coqui(
    text: str,
    output_path: Path,
    voice: str = DEFAULT_VOICE,
    language: str = DEFAULT_LANGUAGE,
    speaker_wav: Optional[Path] = None,
) -> Path:
    """Generate audio using Coqui XTTS-v2 local TTS.

    Args:
        text: Text to convert to speech
        output_path: Path to save the WAV file
        voice: Voice preset name (female, male, neutral) or custom speaker name
        language: Language code (default: en)
        speaker_wav: Optional path to reference audio for voice cloning

    Returns:
        Path to generated WAV file

    Raises:
        CoquiLoadError: When TTS model cannot be loaded
    """
    tts = get_tts_model()

    # Resolve voice to speaker name if using preset
    speaker = COQUI_VOICES.get(voice.lower(), voice)

    try:
        # If a speaker_wav is provided, use it for voice cloning
        if speaker_wav and speaker_wav.exists():
            logger.info("Using custom voice from: %s", speaker_wav)
            tts.tts_to_file(
                text=text,
                file_path=str(output_path),
                speaker_wav=str(speaker_wav),
                language=language,
            )
        else:
            # Use built-in speaker
            logger.debug("Generating audio with speaker: %s", speaker)

            # XTTS-v2 requires a reference audio for voice cloning
            # We'll use the model's default speaker samples
            # For multi-speaker models, we can specify the speaker
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            try:
                # Generate with default reference
                # XTTS-v2 multilingual model needs speaker_wav
                # We'll use a simple approach - generate with the model defaults
                tts.tts_to_file(
                    text=text,
                    file_path=str(output_path),
                    language=language,
                )
            except Exception:
                # If direct generation fails, try with speaker parameter
                logger.debug("Direct generation failed, trying with speaker parameter")
                tts.tts_to_file(
                    text=text, file_path=str(output_path), speaker=speaker, language=language
                )
            finally:
                if temp_path.exists():
                    temp_path.unlink()

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Coqui TTS generated empty audio file")

        return output_path

    except Exception as e:
        error_msg = str(e)
        if "out of memory" in error_msg.lower() or "oom" in error_msg.lower():
            raise RuntimeError(
                "Out of memory error. Try:\n"
                "  - Using a smaller batch of slides\n"
                "  - Closing other applications\n"
                "  - Using a machine with more RAM/GPU memory"
            ) from e
        raise RuntimeError(f"Coqui TTS generation failed: {error_msg}") from e


def list_coqui_voices():
    """List available Coqui voice presets."""
    logger.info("Available Coqui TTS Voice Presets:")
    for name, speaker in COQUI_VOICES.items():
        logger.info("  %s -> %s", name, speaker)
    logger.info("\nNote: You can also provide a path to a reference audio file")
    logger.info("for voice cloning using --speaker-wav option.")
