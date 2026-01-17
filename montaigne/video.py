"""Video generation from slides and audio using ffmpeg."""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .logging import get_logger

logger = get_logger(__name__)


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def validate_audio_file(audio_path: Path, min_size: int = 1000) -> None:
    """
    Validate that an audio file exists and has a reasonable size.

    Args:
        audio_path: Path to the audio file
        min_size: Minimum file size in bytes (default: 1000)

    Raises:
        FileNotFoundError: If the audio file doesn't exist
        ValueError: If the audio file is too small (likely corrupt or empty)
    """
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}\n"
            "This may indicate audio generation failed (e.g., API quota exceeded)."
        )

    file_size = audio_path.stat().st_size
    if file_size < min_size:
        raise ValueError(
            f"Audio file too small ({file_size} bytes): {audio_path}\n"
            "This may indicate audio generation failed (e.g., API quota exceeded)."
        )


def create_slide_clip(
    image_path: Path, audio_path: Path, output_path: Path, resolution: str = "1920:1080"
) -> Path:
    """
    Create a video clip from a single image and audio file.

    Args:
        image_path: Path to the slide image
        audio_path: Path to the audio file
        output_path: Path for output video clip
        resolution: Output resolution (default: 1920:1080)

    Returns:
        Path to the created video clip

    Raises:
        FileNotFoundError: If the audio file doesn't exist
        ValueError: If the audio file is too small
    """
    # Validate audio file before attempting ffmpeg
    validate_audio_file(audio_path)

    width, height = resolution.split(":")

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        str(output_path),
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def generate_video(
    images_dir: Path,
    audio_dir: Path,
    output_path: Optional[Path] = None,
    resolution: str = "1920:1080",
) -> Path:
    """
    Generate a video from slide images and audio files.

    Args:
        images_dir: Directory containing slide images (page_001.png, etc.)
        audio_dir: Directory containing audio files (slide_01.wav, etc.)
        output_path: Path for output video (default: {images_dir.stem}_video.mp4)
        resolution: Output resolution (default: 1920:1080)

    Returns:
        Path to the generated video
    """
    if not check_ffmpeg():
        raise RuntimeError("ffmpeg not found. Please install ffmpeg to generate videos.")

    images_dir = Path(images_dir)
    audio_dir = Path(audio_dir)

    # Find matching images and audio files
    images = sorted(images_dir.glob("page_*.png")) + sorted(images_dir.glob("page_*.jpg"))
    audio_files = sorted(audio_dir.glob("slide_*.wav")) + sorted(audio_dir.glob("slide_*.mp3"))

    if not images:
        raise FileNotFoundError(f"No slide images found in {images_dir}")
    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {audio_dir}")

    # Match images to audio by index
    num_slides = min(len(images), len(audio_files))
    logger.info("Generating video from %d slides...", num_slides)

    # Determine output path
    if output_path is None:
        base_name = images_dir.stem.replace("_images", "")
        output_path = images_dir.parent / f"{base_name}_video.mp4"
    output_path = Path(output_path)

    # Create temporary directory for clips
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        clips = []

        # Use tqdm for progress bar if available in TTY environment
        try:
            from tqdm import tqdm

            use_tqdm = sys.stderr.isatty()
        except ImportError:
            use_tqdm = False

        slide_iterator = range(num_slides)
        if use_tqdm:
            slide_iterator = tqdm(slide_iterator, desc="Creating clips", unit="clip")

        # Create individual clips
        for i in slide_iterator:
            image = images[i]
            audio = audio_files[i]
            clip_path = temp_path / f"clip_{i+1:03d}.mp4"

            if not use_tqdm:
                logger.info("Creating clip %d/%d: %s + %s", i+1, num_slides, image.name, audio.name)
            create_slide_clip(image, audio, clip_path, resolution)
            clips.append(clip_path)

        # Create concat list
        concat_file = temp_path / "concat_list.txt"
        with open(concat_file, "w") as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")

        # Concatenate all clips
        logger.info("Concatenating %d clips...", len(clips))
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output_path),
        ]
        subprocess.run(concat_cmd, capture_output=True, check=True)

    logger.info("Generated video: %s", output_path)

    # Get video info
    try:
        probe_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration,size",
            "-of",
            "csv=p=0",
            str(output_path),
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 2:
                duration = float(parts[0])
                size_mb = int(parts[1]) / (1024 * 1024)
                mins, secs = divmod(int(duration), 60)
                logger.info("  Duration: %d:%02d", mins, secs)
                logger.info("  Size: %.1f MB", size_mb)
    except Exception:
        pass

    return output_path


def generate_video_from_pdf(
    pdf_path: Path,
    script_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    resolution: str = "1920:1080",
    voice: Optional[str] = None,
    provider: str = "gemini",      # Keep your provider logic
    context: str = "",             # Keep upstream context logic
) -> Path:
    """
    Generate a complete video from a PDF presentation.
    """
    from .pdf import extract_pdf_pages
    from .scripts import generate_scripts
    from .audio import generate_audio

    pdf_path = Path(pdf_path)
    base_name = pdf_path.stem

    # Use the provider in the log statement
    logger.info("=== Generating Video from %s (%s) ===", pdf_path.name, provider.upper())

    # Step 1: Extract PDF pages
    logger.info("Step 1: Extracting PDF pages...")
    images_dir = pdf_path.parent / f"{base_name}_images"
    extract_pdf_pages(pdf_path, output_dir=images_dir)

    # Step 2: Generate script (Pass the context here)
    if script_path is None:
        logger.info("Step 2: Generating voiceover script...")
        script_path = generate_scripts(pdf_path, context=context) # Use upstream context
    else:
        script_path = Path(script_path)
        logger.info("Step 2: Using existing script: %s", script_path.name)

    # Step 3: Generate audio (Pass the provider here)
    logger.info("Step 3: Generating audio...")
    audio_dir = script_path.parent / f"{script_path.stem}_audio"
    generate_audio(script_path, output_dir=audio_dir, voice=voice, provider=provider) # Use your provider

    # Step 4: Generate video
    logger.info("Step 4: Creating video...")
    if output_path is None:
        output_path = pdf_path.parent / f"{base_name}_video.mp4"

    return generate_video(images_dir, audio_dir, output_path, resolution)