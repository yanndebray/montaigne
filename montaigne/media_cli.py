#!/usr/bin/env python3
"""
Gemini Media Processing CLI

A unified tool for generating audio from voiceover scripts and translating images using Google Gemini API.

Usage:
    python media_cli.py setup          # Install dependencies and verify API key
    python media_cli.py audio          # Generate audio from voiceover scripts
    python media_cli.py images         # Translate images to French
    python media_cli.py all            # Run both audio and image processing
"""

import argparse
import base64
import mimetypes
import os
import re
import struct
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    try:
        from dotenv import load_dotenv
        from google import genai

        return True
    except ImportError:
        return False


def install_dependencies():
    """Install required packages."""
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-genai", "python-dotenv"])
    print("Dependencies installed successfully!")


def load_api_key():
    """Load the Gemini API key from .env file."""
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file")
        print("Please create a .env file with: GEMINI_API_KEY=your-api-key")
        sys.exit(1)
    return api_key


# ============== Audio Generation ==============


def parse_voiceover_script(script_path):
    """Parse the voiceover script and extract text for each slide.

    Supports formats:
    - ## SLIDE 1: Title  or  ## SLIDE 1 — Title
    - **[Duration: ~30s]**  or  *Duration: 45-60 seconds*
    """
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by slide headers - support SLIDE/DIAPOSITIVE and ":" or "—" separators
    slides = re.split(r"## (?:SLIDE|DIAPOSITIVE)\s+(\d+)\s*[:\—–-]", content, flags=re.IGNORECASE)

    parsed_slides = []
    for i in range(1, len(slides), 2):
        if i >= len(slides):
            break

        slide_num = int(slides[i])
        slide_content = slides[i + 1] if i + 1 < len(slides) else ""

        # Extract title from first line or **"Title"** pattern
        title_match = re.search(r'\*\*"([^"]+)"\*\*', slide_content)
        if title_match:
            title = title_match.group(1)
        else:
            first_line = slide_content.strip().split("\n")[0]
            title = first_line.strip() if first_line else f"Slide {slide_num}"

        lines = slide_content.split("\n")
        voiceover_lines = []
        capture = False

        for line in lines:
            # Support Duration/Durée in various formats
            if "Duration:" in line or "DURATION:" in line or "Durée" in line or "DURÉE" in line:
                capture = True
                continue
            if line.startswith("---") or line.startswith("## "):
                break
            if capture and line.strip():
                # Skip lines that are just formatting markers
                stripped = line.strip()
                if (
                    stripped
                    and not stripped.startswith("**")
                    and not stripped.startswith("*Duration")
                ):
                    voiceover_lines.append(stripped)

        voiceover_text = " ".join(voiceover_lines)

        if voiceover_text:
            parsed_slides.append(
                {
                    "number": slide_num,
                    "title": title[:50],  # Truncate long titles
                    "text": voiceover_text,
                }
            )

    return parsed_slides


def parse_audio_mime_type(mime_type: str) -> dict:
    """Parses bits per sample and rate from an audio MIME type string."""
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


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + audio_data


def generate_audio(script_path: Path, output_dir: Path, voice: str = "Orus"):
    """Generate audio for all slides in a voiceover script."""
    from google import genai
    from google.genai import types

    api_key = load_api_key()
    client = genai.Client(api_key=api_key)

    slides = parse_voiceover_script(script_path)
    print(f"\nFound {len(slides)} slides in {script_path.name}")

    output_dir.mkdir(exist_ok=True)

    for slide in slides:
        print(f"  Generating audio for Slide {slide['number']}: {slide['title'][:40]}...")

        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=slide["text"])],
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
                model="gemini-2.5-pro-preview-tts",
                contents=contents,
                config=config,
            ):
                if (
                    chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                ):
                    continue

                part = chunk.candidates[0].content.parts[0]
                if part.inline_data and part.inline_data.data:
                    inline_data = part.inline_data
                    file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".wav"
                    data_buffer = inline_data.data

                    if file_extension != ".wav":
                        file_extension = ".wav"
                        data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)

                    file_name = f"slide_{slide['number']:02d}{file_extension}"
                    output_path = output_dir / file_name

                    with open(output_path, "wb") as f:
                        f.write(data_buffer)
                    print(f"    Saved: {file_name}")

        except Exception as e:
            print(f"    Error: {e}")


# ============== Image Translation ==============


def save_image(file_name, data):
    """Save image data, handling base64 encoding if necessary."""
    if isinstance(data, str):
        data = base64.b64decode(data)
    elif isinstance(data, bytes):
        try:
            if data[:4] in (b"/9j/", b"iVBO", b"R0lG", b"UklG"):
                data = base64.b64decode(data)
        except Exception:
            pass

    with open(file_name, "wb") as f:
        f.write(data)


def translate_image(client, image_path: Path, output_dir: Path, target_lang: str = "French"):
    """Translate text in an image to target language."""
    from google.genai import types

    print(f"  Translating: {image_path.name}...")

    with open(image_path, "rb") as f:
        image_data = f.read()

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/jpeg"

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(mime_type=mime_type, data=image_data),
                types.Part.from_text(
                    text=f"""Generate a new image based on this one with the following changes:
1. Translate all text to {target_lang}
2. Keep the same layout, colors, and visual style

Output the modified image, not text."""
                ),
            ],
        ),
    ]

    config = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])

    for chunk in client.models.generate_content_stream(
        model="gemini-3-pro-image-preview",
        contents=contents,
        config=config,
    ):
        if (
            chunk.candidates is None
            or chunk.candidates[0].content is None
            or chunk.candidates[0].content.parts is None
        ):
            continue

        part = chunk.candidates[0].content.parts[0]
        if part.inline_data and part.inline_data.data:
            file_extension = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
            output_name = f"{image_path.stem}_fr{file_extension}"
            output_path = output_dir / output_name

            save_image(output_path, part.inline_data.data)
            print(f"    Saved: {output_name}")
        elif hasattr(part, "text") and part.text:
            print(f"    Model response: {part.text[:100]}...")


def translate_images(input_path: Path, output_dir: Path, target_lang: str = "French"):
    """Translate images from input path (file or directory)."""
    from google import genai

    api_key = load_api_key()
    client = genai.Client(api_key=api_key)

    image_extensions = {".jpeg", ".jpg", ".png", ".gif", ".webp"}

    if input_path.is_file():
        images = [input_path]
    elif input_path.is_dir():
        images = sorted([f for f in input_path.iterdir() if f.suffix.lower() in image_extensions])
    else:
        print(f"Error: {input_path} not found")
        return

    print(f"\nFound {len(images)} image(s) to translate")
    output_dir.mkdir(exist_ok=True)

    for image_path in images:
        try:
            translate_image(client, image_path, output_dir, target_lang)
        except Exception as e:
            print(f"    Error: {e}")


# ============== CLI Commands ==============


def cmd_setup(args):
    """Setup command: install dependencies and verify configuration."""
    print("=== Setup ===\n")

    if not check_dependencies():
        install_dependencies()
    else:
        print("Dependencies already installed.")

    # Re-import after install
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(f"API Key: {'*' * 10}{api_key[-4:]}")
    else:
        print("Warning: GEMINI_API_KEY not found in .env file")

    print("\nSetup complete!")


def cmd_audio(args):
    """Audio command: generate audio from voiceover scripts."""
    if not check_dependencies():
        print("Dependencies not installed. Run: python media_cli.py setup")
        sys.exit(1)

    print("=== Audio Generation ===")

    project_dir = Path(__file__).parent
    scripts = list(project_dir.glob("*voiceover*.md"))

    if args.script:
        scripts = [Path(args.script)]

    if not scripts:
        print("No voiceover scripts found. Use --script to specify one.")
        return

    print(f"Found {len(scripts)} script(s)")

    for script in scripts:
        output_dir = project_dir / f"{script.stem}_audio"
        generate_audio(script, output_dir, voice=args.voice)
        print(f"  Output: {output_dir}/")


def cmd_images(args):
    """Images command: translate images."""
    if not check_dependencies():
        print("Dependencies not installed. Run: python media_cli.py setup")
        sys.exit(1)

    print("=== Image Translation ===")

    project_dir = Path(__file__).parent

    if args.input:
        input_path = Path(args.input)
    else:
        # Look for image files or folders
        images = (
            list(project_dir.glob("*.png"))
            + list(project_dir.glob("*.jpg"))
            + list(project_dir.glob("*.jpeg"))
        )
        if images:
            input_path = images[0]
            print(f"Auto-detected: {input_path.name}")
        else:
            print("No images found. Use --input to specify image or folder.")
            return

    output_dir = Path(args.output) if args.output else project_dir / "images_translated"
    translate_images(input_path, output_dir, target_lang=args.lang)
    print(f"  Output: {output_dir}/")


def cmd_all(args):
    """Run both audio and image processing."""
    print("=== Running All Tasks ===\n")
    cmd_audio(args)
    print()
    cmd_images(args)


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Media Processing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python media_cli.py setup                    # Install dependencies
  python media_cli.py audio                    # Generate audio from all voiceover scripts
  python media_cli.py audio --script file.md  # Generate audio from specific script
  python media_cli.py images                   # Translate auto-detected images
  python media_cli.py images --input img.png  # Translate specific image
  python media_cli.py all                      # Run everything
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    subparsers.add_parser("setup", help="Install dependencies and verify configuration")

    # Audio command
    audio_parser = subparsers.add_parser("audio", help="Generate audio from voiceover scripts")
    audio_parser.add_argument("--script", help="Path to specific voiceover script")
    audio_parser.add_argument(
        "--voice",
        default="Orus",
        choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"],
        help="Voice to use (default: Orus)",
    )

    # Images command
    images_parser = subparsers.add_parser("images", help="Translate images")
    images_parser.add_argument("--input", help="Input image file or folder")
    images_parser.add_argument("--output", help="Output folder")
    images_parser.add_argument("--lang", default="French", help="Target language (default: French)")

    # All command
    all_parser = subparsers.add_parser("all", help="Run both audio and image processing")
    all_parser.add_argument("--script", help="Path to specific voiceover script")
    all_parser.add_argument("--voice", default="Orus", help="Voice to use")
    all_parser.add_argument("--input", help="Input image file or folder")
    all_parser.add_argument("--output", help="Output folder for images")
    all_parser.add_argument("--lang", default="French", help="Target language")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "setup": cmd_setup,
        "audio": cmd_audio,
        "images": cmd_images,
        "all": cmd_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
