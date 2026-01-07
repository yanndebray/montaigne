"""Audio generation from voiceover scripts using Gemini TTS."""

import base64
import mimetypes
import re
import struct
from pathlib import Path
from typing import List, Dict, Optional

from .config import get_gemini_client

# Available Gemini TTS voices
VOICES = ["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"]
DEFAULT_VOICE = "Orus"
TTS_MODEL = "gemini-2.5-pro-preview-tts"


def parse_voiceover_script(script_path: Path) -> List[Dict]:
    """
    Parse a voiceover script and extract text for each slide.

    Supports formats:
    - ## SLIDE 1: Title  or  ## SLIDE 1 - Title
    - **[Duration: ~30s]**  or  *Duration: 45-60 seconds*

    Args:
        script_path: Path to markdown voiceover script

    Returns:
        List of dicts with 'number', 'title', and 'text' keys
    """
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by slide headers - support various separators
    slides = re.split(r"## SLIDE\s+(\d+)\s*[:\-\u2014\u2013]", content, flags=re.IGNORECASE)

    parsed_slides = []
    for i in range(1, len(slides), 2):
        if i >= len(slides):
            break

        slide_num = int(slides[i])
        slide_content = slides[i + 1] if i + 1 < len(slides) else ""

        # Extract title
        title_match = re.search(r'\*\*"([^"]+)"\*\*', slide_content)
        if title_match:
            title = title_match.group(1)
        else:
            first_line = slide_content.strip().split('\n')[0]
            title = first_line.strip() if first_line else f"Slide {slide_num}"

        # Extract voiceover text (content after Duration marker)
        lines = slide_content.split('\n')
        voiceover_lines = []
        capture = False

        for line in lines:
            if 'Duration:' in line or 'DURATION:' in line:
                capture = True
                continue
            if line.startswith('---') or line.startswith('## '):
                break
            if capture and line.strip():
                stripped = line.strip()
                if stripped and not stripped.startswith('**') and not stripped.startswith('*Duration'):
                    voiceover_lines.append(stripped)

        voiceover_text = ' '.join(voiceover_lines)

        if voiceover_text:
            parsed_slides.append({
                'number': slide_num,
                'title': title[:50],
                'text': voiceover_text
            })

    return parsed_slides


def _parse_audio_mime_type(mime_type: str) -> dict:
    """Parse bits per sample and rate from audio MIME type."""
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


def _decode_audio_data(data: bytes) -> bytes:
    """Decode audio data, handling base64 encoding if present."""
    # Check if data looks like base64 (all printable ASCII, no binary)
    # Base64 uses A-Z, a-z, 0-9, +, /, = characters
    if isinstance(data, bytes):
        try:
            # If it looks like base64 text (all ASCII printable)
            if all(32 <= b < 127 for b in data[:100]):
                return base64.b64decode(data)
        except Exception:
            pass
    return data


def _convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Convert raw audio data to WAV format with proper headers."""
    # First decode base64 if needed
    audio_data = _decode_audio_data(audio_data)

    params = _parse_audio_mime_type(mime_type)
    bits_per_sample = params["bits_per_sample"]
    sample_rate = params["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
        num_channels, sample_rate, byte_rate, block_align,
        bits_per_sample, b"data", data_size
    )
    return header + audio_data


def generate_slide_audio(
    text: str,
    output_path: Path,
    voice: str = DEFAULT_VOICE,
    client=None
) -> Path:
    """
    Generate audio for a single text using Gemini TTS.

    Args:
        text: Text to convert to speech
        output_path: Where to save the audio file
        voice: Voice name (default: Orus)
        client: Optional pre-configured Gemini client

    Returns:
        Path to generated audio file
    """
    from google.genai import types

    if client is None:
        client = get_gemini_client()

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=text)],
        ),
    ]

    config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=TTS_MODEL,
        contents=contents,
        config=config,
    ):
        if (chunk.candidates is None or
            chunk.candidates[0].content is None or
            chunk.candidates[0].content.parts is None):
            continue

        part = chunk.candidates[0].content.parts[0]
        if part.inline_data and part.inline_data.data:
            inline_data = part.inline_data
            data_buffer = _convert_to_wav(inline_data.data, inline_data.mime_type)

            with open(output_path, "wb") as f:
                f.write(data_buffer)
            return output_path

    raise RuntimeError("No audio data received from API")


def generate_audio(
    script_path: Path,
    output_dir: Optional[Path] = None,
    voice: str = DEFAULT_VOICE
) -> List[Path]:
    """
    Generate audio for all slides in a voiceover script.

    Args:
        script_path: Path to markdown voiceover script
        output_dir: Directory for output (default: {script_stem}_audio/)
        voice: TTS voice name

    Returns:
        List of paths to generated audio files
    """
    script_path = Path(script_path)

    if output_dir is None:
        output_dir = script_path.parent / f"{script_path.stem}_audio"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    slides = parse_voiceover_script(script_path)
    print(f"\nFound {len(slides)} slides in {script_path.name}")

    client = get_gemini_client()
    generated_files = []

    for slide in slides:
        print(f"  Generating audio for Slide {slide['number']}: {slide['title'][:40]}...")

        try:
            output_path = output_dir / f"slide_{slide['number']:02d}.wav"
            generate_slide_audio(slide['text'], output_path, voice=voice, client=client)
            generated_files.append(output_path)
            print(f"    Saved: {output_path.name}")
        except Exception as e:
            print(f"    Error: {e}")

    print(f"\nGenerated {len(generated_files)} audio files in {output_dir}/")
    return generated_files
