"""Command-line interface for Montaigne media processing toolkit."""

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .logging import setup_logging, get_logger

logger = get_logger(__name__)


def resolve_context(context_values: list) -> str:
    """
    Resolve a list of context values into a single combined context string.

    Each context value can be either:
    - A string to use directly
    - A path to a text or markdown file (contents will be read)

    Args:
        context_values: List of context strings or file paths

    Returns:
        Combined context string with all values joined by newlines
    """
    if not context_values:
        return ""

    resolved = []
    for value in context_values:
        path = Path(value)
        # Check if it's a file path (exists and is a text/markdown file)
        if path.exists() and path.is_file():
            suffix = path.suffix.lower()
            if suffix in {".txt", ".md", ".markdown", ".text"}:
                try:
                    content = path.read_text(encoding="utf-8")
                    resolved.append(f"[From {path.name}]\n{content}")
                    continue
                except Exception:
                    pass  # Fall through to use as string
        # Use as literal string
        resolved.append(value)

    return "\n\n".join(resolved)


def cmd_setup(args):
    """Install dependencies and verify configuration."""
    from .config import check_dependencies, install_dependencies

    logger.info("=== Montaigne Setup ===")

    if not check_dependencies():
        install_dependencies()
    else:
        logger.info("All dependencies installed.")

    # Verify API key
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        logger.info("API Key: %s%s", "*" * 10, api_key[-4:])
    else:
        logger.warning("GEMINI_API_KEY not found in .env file")
        logger.warning("Create a .env file with: GEMINI_API_KEY=your-api-key")

    logger.info("Setup complete!")


def cmd_models(args):
    """List available Gemini models."""
    from .config import list_models

    filter_term = args.filter if args.filter else None

    logger.info("=== Available Gemini Models ===")
    if filter_term:
        logger.info("Filter: %s", filter_term)

    models = list_models(filter_term)

    if not models:
        logger.info("No models found matching filter.")
        return

    for model in models:
        # Strip 'models/' prefix for cleaner output
        display_name = model.replace("models/", "")
        logger.info("  %s", display_name)

    logger.info("\nTotal: %d models", len(models))


def cmd_pdf(args):
    """Extract PDF pages to images."""
    from .config import check_dependencies
    from .pdf import extract_pdf_pages

    if not check_dependencies():
        logger.error("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    logger.info("=== PDF Extraction ===")

    pdf_path = Path(args.input)
    output_dir = Path(args.output) if args.output else None
    logo_path = Path(args.logo) if hasattr(args, "logo") and args.logo else None

    extract_pdf_pages(
        pdf_path,
        output_dir=output_dir,
        dpi=args.dpi,
        image_format=args.format,
        add_branding=not (hasattr(args, "no_branding") and args.no_branding),
        logo_path=logo_path,
    )


def cmd_script(args):
    """Generate voiceover scripts from PDF or images."""
    from .config import check_dependencies
    from .scripts import generate_scripts

    if not check_dependencies():
        logger.error("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    logger.info("=== Script Generation ===")

    input_path = Path(args.input) if args.input else None

    # Auto-detect PDF or images
    if input_path is None:
        cwd = Path.cwd()
        pdfs = list(cwd.glob("*.pdf"))
        if pdfs:
            input_path = pdfs[0]
            logger.info("Auto-detected: %s", input_path.name)
        else:
            image_dirs = [d for d in cwd.iterdir() if d.is_dir() and "images" in d.name.lower()]
            if image_dirs:
                input_path = image_dirs[0]
                logger.info("Auto-detected: %s", input_path.name)
            else:
                logger.error("No PDF or image folder found. Use --input to specify one.")
                return

    output_path = Path(args.output) if args.output else None
    context = resolve_context(args.context)

    generate_scripts(input_path, output_path=output_path, context=context, model=args.model)


def cmd_audio(args):
    """Generate audio from voiceover scripts."""
    from .config import check_dependencies
    from .audio import generate_audio

    if args.list_voices:
        from .audio import list_voices

        list_voices(provider=args.provider)
        return  # Stop execution here

    if not check_dependencies():
        logger.error("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    logger.info("=== Audio Generation ===")

    script_path = Path(args.script) if args.script else None

    # Auto-detect voiceover scripts
    if script_path is None:
        cwd = Path.cwd()
        scripts = list(cwd.glob("*voiceover*.md"))
        if scripts:
            script_path = scripts[0]
            logger.info("Auto-detected: %s", script_path.name)
        else:
            logger.error("No voiceover script found. Use --script to specify one.")
            return

    output_dir = Path(args.output) if args.output else None
    generate_audio(
        script_path,
        output_dir=output_dir,
        voice=args.voice,
        provider=args.provider,
        model=args.model,
    )


def cmd_images(args):
    """Translate images to target language."""
    from .config import check_dependencies
    from .images import translate_images

    if not check_dependencies():
        logger.error("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    logger.info("=== Image Translation ===")

    input_path = Path(args.input) if args.input else None

    # Auto-detect images
    if input_path is None:
        cwd = Path.cwd()
        images = list(cwd.glob("*.png")) + list(cwd.glob("*.jpg"))
        if images:
            input_path = images[0]
            logger.info("Auto-detected: %s", input_path.name)
        else:
            logger.error("No images found. Use --input to specify image or folder.")
            return

    output_dir = Path(args.output) if args.output else None
    logo_path = Path(args.logo) if hasattr(args, "logo") and args.logo else None

    translate_images(
        input_path,
        output_dir=output_dir,
        target_lang=args.lang,
        model=args.model,
        add_branding=not (hasattr(args, "no_branding") and args.no_branding),
        logo_path=logo_path,
    )


def cmd_video(args):
    """Generate video from slides and audio."""
    from .video import generate_video, generate_video_from_pdf, check_ffmpeg

    if not check_ffmpeg():
        logger.error("ffmpeg not found. Please install ffmpeg to generate videos.")
        logger.error("  Windows: choco install ffmpeg  or  winget install ffmpeg")
        logger.error("  macOS: brew install ffmpeg")
        logger.error("  Linux: sudo apt install ffmpeg")
        sys.exit(1)

    logger.info("=== Video Generation ===")

    # If PDF provided, run full pipeline
    if args.pdf:
        pdf_path = Path(args.pdf)
        script_path = Path(args.script) if args.script else None
        output_path = Path(args.output) if args.output else None
        logo_path = Path(args.logo) if hasattr(args, "logo") and args.logo else None

        generate_video_from_pdf(
            pdf_path,
            script_path=script_path,
            output_path=output_path,
            resolution=args.resolution,
            voice=args.voice,
            provider=args.provider,
            context=resolve_context(args.context),
            script_model=args.script_model,
            audio_model=args.audio_model,
            add_branding=not (hasattr(args, "no_branding") and args.no_branding),
            logo_path=logo_path,
        )
        return

    # Otherwise, combine existing images and audio
    images_dir = Path(args.images) if args.images else None
    audio_dir = Path(args.audio) if args.audio else None

    # Auto-detect directories
    if images_dir is None:
        cwd = Path.cwd()
        image_dirs = [d for d in cwd.iterdir() if d.is_dir() and "_images" in d.name]
        if image_dirs:
            images_dir = image_dirs[0]
            logger.info("Auto-detected images: %s", images_dir.name)
        else:
            logger.error("No images directory found. Use --images to specify one.")
            return

    if audio_dir is None:
        cwd = Path.cwd()
        audio_dirs = [d for d in cwd.iterdir() if d.is_dir() and "_audio" in d.name]
        if audio_dirs:
            audio_dir = audio_dirs[0]
            logger.info("Auto-detected audio: %s", audio_dir.name)
        else:
            logger.error("No audio directory found. Use --audio to specify one.")
            return

    output_path = Path(args.output) if args.output else None

    generate_video(images_dir, audio_dir, output_path, resolution=args.resolution)


def cmd_ppt(args):
    """Create PowerPoint from PDF or images folder."""
    from .config import check_dependencies
    from .ppt import create_pptx

    if not check_dependencies():
        logger.error("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    logger.info("=== PowerPoint Generation ===")

    input_path = Path(args.input) if args.input else None

    # Auto-detect input
    if input_path is None:
        cwd = Path.cwd()
        # First try to find a PDF
        pdfs = list(cwd.glob("*.pdf"))
        if pdfs:
            input_path = pdfs[0]
            logger.info("Auto-detected PDF: %s", input_path.name)
        else:
            # Try to find an images folder
            image_dirs = [d for d in cwd.iterdir() if d.is_dir() and "images" in d.name.lower()]
            if image_dirs:
                input_path = image_dirs[0]
                logger.info("Auto-detected folder: %s", input_path.name)
            else:
                logger.error("No PDF or images folder found. Use --input to specify one.")
                return

    output_path = Path(args.output) if args.output else None
    script_path = Path(args.script) if args.script else None

    # Auto-detect script if not provided
    if script_path is None:
        cwd = Path.cwd()
        scripts = list(cwd.glob("*voiceover*.md"))
        if scripts:
            script_path = scripts[0]
            logger.info("Auto-detected script: %s", script_path.name)

    create_pptx(
        input_path,
        output_path=output_path,
        script_path=script_path,
        dpi=args.dpi,
        keep_images=args.keep_images,
    )


def cmd_edit(args):
    """Launch the Streamlit web editor."""
    import subprocess

    try:
        import streamlit  # noqa: F401
    except ImportError:
        logger.error("Streamlit not installed. Install with:")
        logger.error("  pip install montaigne[edit]")
        sys.exit(1)

    logger.info("=== Launching Montaigne Web App ===")

    # Set environment variables for preloading
    env = os.environ.copy()

    if args.pdf:
        pdf_path = Path(args.pdf).resolve()
        if pdf_path.exists():
            env["MONTAIGNE_PRELOAD_PDF"] = str(pdf_path)
            logger.info("Preloading PDF: %s", pdf_path.name)
        else:
            logger.warning("PDF not found: %s", args.pdf)

    if args.images:
        images_path = Path(args.images).resolve()
        if images_path.exists() and images_path.is_dir():
            env["MONTAIGNE_PRELOAD_IMAGES"] = str(images_path)
            logger.info("Preloading images: %s", images_path.name)
        else:
            logger.warning("Images folder not found: %s", args.images)

    if args.script:
        script_path = Path(args.script).resolve()
        if script_path.exists():
            env["MONTAIGNE_PRELOAD_SCRIPT"] = str(script_path)
            logger.info("Preloading script: %s", script_path.name)
        else:
            logger.warning("Script not found: %s", args.script)

    logger.info("Opening in browser...")

    # Get the path to app.py
    app_path = Path(__file__).parent / "app.py"

    # Launch streamlit with environment variables
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], env=env)


# =============================================================================
# Cloud Commands
# =============================================================================


def cmd_cloud_health(args):
    """Check cloud API health."""
    import requests
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()
    logger.info("Checking cloud API: %s", api_url)

    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        response.raise_for_status()
        data = response.json()

        logger.info("Status: %s", data.get("status", "unknown"))
        logger.info("Version: %s", data.get("version", "unknown"))
        logger.info("FFmpeg: %s", "available" if data.get("ffmpeg") else "not available")
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to %s", api_url)
        logger.error("Make sure the cloud API is deployed and the URL is correct.")
        sys.exit(1)
    except Exception as e:
        logger.error("Error: %s", e)
        sys.exit(1)


def cmd_cloud_video(args):
    """Generate video via cloud API."""
    import requests
    import time
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()
    pdf_path = Path(args.pdf)

    if not pdf_path.exists():
        logger.error("PDF file not found: %s", pdf_path)
        sys.exit(1)

    logger.info("=== Cloud Video Generation ===")
    logger.info("API: %s", api_url)
    logger.info("PDF: %s", pdf_path.name)

    # Step 1: Get upload URL
    logger.info("Step 1: Requesting upload URL...")
    response = requests.post(
        f"{api_url}/jobs/upload-url",
        json={
            "filename": pdf_path.name,
            "content_type": "application/pdf",
            "size_bytes": pdf_path.stat().st_size,
        },
    )
    response.raise_for_status()
    upload_data = response.json()
    job_id = upload_data["job_id"]
    logger.info("Job ID: %s", job_id)

    # Step 2: Upload PDF
    logger.info("Step 2: Uploading %s...", pdf_path.name)
    with open(pdf_path, "rb") as f:
        upload_response = requests.put(
            upload_data["upload_url"],
            data=f,
            headers={"Content-Type": "application/pdf"},
        )
        upload_response.raise_for_status()
    logger.info("Upload complete.")

    # Step 3: Start processing
    logger.info("Step 3: Starting video generation...")
    response = requests.post(
        f"{api_url}/jobs/{job_id}/start",
        json={
            "pipeline": "video",
            "resolution": args.resolution,
            "voice": args.voice,
            "context": args.context or "",
        },
    )
    response.raise_for_status()

    if not args.wait:
        logger.info("Job submitted. Check status with:")
        logger.info("  essai cloud status %s", job_id)
        logger.info("Download when complete with:")
        logger.info("  essai cloud download %s -o output.mp4", job_id)
        return

    # Step 4: Wait for completion
    logger.info("Step 4: Processing...")
    last_message = ""
    while True:
        response = requests.get(f"{api_url}/jobs/{job_id}/status")
        response.raise_for_status()
        status_data = response.json()

        status = status_data.get("status")
        progress = status_data.get("progress", {})
        message = progress.get("message", "")

        if message != last_message:
            logger.info("  %s", message)
            last_message = message

        if status == "completed":
            break
        elif status == "failed":
            error = status_data.get("error", {})
            logger.error("Error: %s", error.get("message", "Unknown error"))
            sys.exit(1)

        time.sleep(2)

    # Step 5: Download video
    output_path = Path(args.output) if args.output else Path(f"{pdf_path.stem}_video.mp4")
    logger.info("Step 5: Downloading video to %s...", output_path)

    response = requests.get(f"{api_url}/jobs/{job_id}/download?file=video")
    response.raise_for_status()
    download_data = response.json()

    video_response = requests.get(download_data["download_url"], stream=True)
    video_response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in video_response.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Complete! Video saved to: %s (%.1f MB)", output_path, size_mb)


def cmd_cloud_status(args):
    """Check job status."""
    import requests
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()

    response = requests.get(f"{api_url}/jobs/{args.job_id}/status")

    if response.status_code == 404:
        logger.error("Job not found: %s", args.job_id)
        sys.exit(1)

    response.raise_for_status()
    data = response.json()

    logger.info("Job ID: %s", data.get("job_id"))
    logger.info("Status: %s", data.get("status"))
    logger.info("Pipeline: %s", data.get("pipeline", "unknown"))

    if data.get("progress"):
        progress = data["progress"]
        logger.info("Progress:")
        logger.info("  Step: %s", progress.get("step"))
        if progress.get("current") is not None:
            logger.info("  Progress: %s/%s", progress.get("current"), progress.get("total"))
        if progress.get("message"):
            logger.info("  Message: %s", progress.get("message"))

    if data.get("created_at"):
        logger.info("Created: %s", data.get("created_at"))
    if data.get("started_at"):
        logger.info("Started: %s", data.get("started_at"))
    if data.get("completed_at"):
        logger.info("Completed: %s", data.get("completed_at"))

    if data.get("output"):
        output = data["output"]
        logger.info("Output:")
        if output.get("video_size_bytes"):
            size_mb = output["video_size_bytes"] / (1024 * 1024)
            logger.info("  Video size: %.1f MB", size_mb)
        if output.get("download_expires"):
            logger.info("  Download expires: %s", output["download_expires"])

    if data.get("error"):
        error = data["error"]
        logger.error("Error: %s", error.get("message"))


def cmd_cloud_download(args):
    """Download job output."""
    import requests
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()
    output_path = Path(args.output)

    logger.info("Downloading %s from job %s...", args.file, args.job_id)

    response = requests.get(f"{api_url}/jobs/{args.job_id}/download?file={args.file}")

    if response.status_code == 404:
        logger.error("Job or file not found: %s", args.job_id)
        sys.exit(1)
    elif response.status_code == 400:
        logger.error("Job not completed yet. Check status with: essai cloud status %s", args.job_id)
        sys.exit(1)

    response.raise_for_status()
    download_data = response.json()

    logger.info("File size: %.1f MB", download_data["size_bytes"] / (1024 * 1024))
    logger.info("Downloading to: %s", output_path)

    file_response = requests.get(download_data["download_url"], stream=True)
    file_response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in file_response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Download complete: %s", output_path)


def cmd_cloud_jobs(args):
    """List recent jobs."""
    import requests
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()

    params = {"limit": args.limit}
    if args.status:
        params["status"] = args.status

    response = requests.get(f"{api_url}/jobs", params=params)
    response.raise_for_status()
    data = response.json()

    jobs = data.get("jobs", [])
    if not jobs:
        logger.info("No jobs found.")
        return

    logger.info("%-30s %-12s %-10s %s", "Job ID", "Status", "Pipeline", "Created")
    logger.info("-" * 80)
    for job in jobs:
        created = job.get("created_at", "")[:19] if job.get("created_at") else ""
        logger.info(
            "%-30s %-12s %-10s %s",
            job["job_id"],
            job.get("status", ""),
            job.get("pipeline", ""),
            created,
        )


def cmd_annotate(args):
    """Launch the video/audio annotation tool."""
    from pathlib import Path

    # Check for Flask dependency
    try:
        import flask  # noqa: F401
    except ImportError:
        logger.error("Flask not installed. Install with:")
        logger.error("  pip install montaigne[annotate]")
        sys.exit(1)

    logger.info("=== Video Annotation Tool ===")

    # Find media file (optional for interactive mode)
    media_path = Path(args.input) if args.input else None

    if media_path is None:
        cwd = Path.cwd()
        # Auto-detect video/audio files
        video_exts = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"}
        audio_exts = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
        all_exts = video_exts | audio_exts

        media_files = [f for f in cwd.iterdir() if f.suffix.lower() in all_exts]
        if media_files:
            media_path = media_files[0]
            logger.info("Auto-detected: %s", media_path.name)
        # If no media found, continue without it (standalone mode)

    # Resolve to absolute path for Flask compatibility (if media exists)
    if media_path is not None:
        media_path = media_path.resolve()
        if not media_path.exists():
            logger.error("File not found: %s", media_path)
            sys.exit(1)

    # Handle export mode (non-interactive) - requires media file
    if args.export:
        if media_path is None:
            logger.error("Export requires a media file. Use --input to specify one.")
            sys.exit(1)

        from .annotation import (
            AnnotationStore,
            get_media_id,
            export_to_webvtt,
            export_to_srt,
            export_to_json,
        )

        store = AnnotationStore()
        media_id = get_media_id(media_path)
        annotations = store.get_by_media(media_id)

        if not annotations:
            logger.error("No annotations found for: %s", media_path.name)
            sys.exit(1)

        output_path = (
            Path(args.output)
            if args.output
            else Path(f"{media_path.stem}_annotations.{args.export}")
        )

        if args.export == "vtt":
            export_to_webvtt(annotations, output_path)
        elif args.export == "srt":
            export_to_srt(annotations, output_path)
        elif args.export == "json":
            export_to_json(annotations, output_path)

        logger.info("Exported %d annotations to: %s", len(annotations), output_path)
        return

    # Launch interactive annotation server
    from .annotation_server import run_server

    db_path = Path(args.db) if args.db else None

    # Determine host - --network flag overrides --host
    host = "0.0.0.0" if args.network else args.host

    if args.network:
        import socket

        try:
            # Get local IP for display
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            logger.info("Network mode: accessible at http://%s:%d", local_ip, args.port)
        except Exception:
            logger.info("Network mode: server will be accessible on all interfaces")

    run_server(
        media_path=media_path,
        host=host,
        port=args.port,
        db_path=db_path,
        open_browser=not args.no_browser,
    )


def cmd_localize(args):
    """
    Full localization pipeline: PDF -> Images -> Translate + Audio

    This is the main workflow that:
    1. Extracts PDF pages to images (if PDF provided)
    2. Translates all images to target language
    3. Generates audio from voiceover script (if provided)
    """
    from .config import check_dependencies
    from .pdf import extract_pdf_pages
    from .images import translate_images
    from .audio import generate_audio

    if not check_dependencies():
        logger.error("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    logger.info("=== Montaigne Localization Pipeline ===")

    project_dir = Path.cwd()
    output_base = (
        Path(args.output) if args.output else project_dir / f"localized_{args.lang.lower()}"
    )
    output_base.mkdir(parents=True, exist_ok=True)

    images_to_translate = []

    # Step 1: Extract PDF if provided
    if args.pdf:
        pdf_path = Path(args.pdf)
        logger.info("Step 1: Extracting PDF pages...")
        images_dir = output_base / "source_images"
        extracted = extract_pdf_pages(pdf_path, output_dir=images_dir, dpi=args.dpi)
        images_to_translate = extracted
    elif args.images:
        images_to_translate = [Path(args.images)]
    else:
        # Auto-detect PDF or images
        pdfs = list(project_dir.glob("*.pdf"))
        if pdfs:
            logger.info("Step 1: Auto-detected PDF: %s", pdfs[0].name)
            images_dir = output_base / "source_images"
            extracted = extract_pdf_pages(pdfs[0], output_dir=images_dir, dpi=args.dpi)
            images_to_translate = extracted

    # Step 2: Translate images
    if images_to_translate:
        logger.info("Step 2: Translating images to %s...", args.lang)
        if isinstance(images_to_translate, list) and len(images_to_translate) > 0:
            # If we have a list from PDF extraction, use the parent dir
            source_dir = images_to_translate[0].parent
        else:
            source_dir = Path(images_to_translate)

        translated_dir = output_base / "translated_images"
        translate_images(source_dir, output_dir=translated_dir, target_lang=args.lang)

    # Step 3: Generate audio if script provided
    if args.script:
        logger.info("Step 3: Generating audio...")
        script_path = Path(args.script)
        audio_dir = output_base / "audio"
        generate_audio(script_path, output_dir=audio_dir, voice=args.voice, provider=args.provider)
    else:
        # Auto-detect voiceover script
        scripts = list(project_dir.glob("*voiceover*.md"))
        if scripts:
            logger.info("Step 3: Auto-detected script: %s", scripts[0].name)
            audio_dir = output_base / "audio"
            generate_audio(
                scripts[0], output_dir=audio_dir, voice=args.voice, provider=args.provider
            )

    logger.info("=== Localization Complete ===")
    logger.info("Output: %s/", output_base)


def main():
    parser = argparse.ArgumentParser(
        prog="essai",
        description="Montaigne - Media Processing Toolkit for Presentation Localization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  essai setup                           # Install dependencies
  essai edit                             # Launch web editor
  essai pdf presentation.pdf            # Extract PDF to images
  essai script --input presentation.pdf # Generate voiceover script from PDF
  essai audio --script voiceover.md     # Generate audio from script
  essai video --pdf presentation.pdf    # Generate video from PDF (full pipeline)
  essai translate --input slides/       # Translate images
  essai ppt --input presentation.pdf    # Convert PDF to PowerPoint
  essai ppt --input slides/ --script voiceover.md  # Images to PPT with notes
  essai localize --pdf deck.pdf --script script.md --lang Spanish
  essai annotate video.mp4              # Launch video annotation tool

Web Editor:
  essai edit                             # Launch Streamlit slide editor

Annotation Tool:
  essai annotate video.mp4              # Launch annotation UI
  essai annotate --export srt           # Export annotations to SRT

Full pipeline (manual):
  essai pdf presentation.pdf            # Step 1: Extract slides
  essai script --input presentation.pdf # Step 2: Generate script
  essai audio --script voiceover.md     # Step 3: Generate audio
  essai video --images slides/ --audio audio/  # Step 4: Create video

One-command video:
  essai video --pdf presentation.pdf    # Does all steps automatically
        """,
    )
    parser.add_argument("--version", action="version", version=f"montaigne {__version__}")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show debug output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Show only errors")
    parser.add_argument("--log-file", metavar="FILE", help="Write logs to file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    subparsers.add_parser("setup", help="Install dependencies and verify configuration")

    # Models command
    models_parser = subparsers.add_parser("models", help="List available Gemini models")
    models_parser.add_argument(
        "--filter",
        "-f",
        help="Filter models by name (e.g., 'tts', 'flash', 'pro', 'image')",
    )

    # Webapp command
    edit_parser = subparsers.add_parser("edit", help="Launch the Streamlit web editor")
    edit_parser.add_argument("--pdf", "-p", help="PDF file to preload")
    edit_parser.add_argument("--images", "-i", help="Images folder to preload")
    edit_parser.add_argument("--script", "-s", help="Voiceover script (.md) to preload")

    # PDF command
    pdf_parser = subparsers.add_parser("pdf", help="Extract PDF pages to images")
    pdf_parser.add_argument("input", help="Path to PDF file")
    pdf_parser.add_argument("--output", "-o", help="Output directory")
    pdf_parser.add_argument("--dpi", type=int, default=150, help="Image resolution (default: 150)")
    pdf_parser.add_argument("--format", choices=["png", "jpg"], default="png", help="Output format")
    pdf_parser.add_argument(
        "--no-branding",
        action="store_true",
        help="Disable montaigne.cc logo branding (enabled by default)",
    )
    pdf_parser.add_argument(
        "--logo", help="Path to custom logo image (default: montaigne amber logo)"
    )

    # Script command
    script_parser = subparsers.add_parser(
        "script", help="Generate voiceover script from PDF/images"
    )
    script_parser.add_argument("--input", "-i", help="PDF file or images folder")
    script_parser.add_argument("--output", "-o", help="Output markdown file")
    script_parser.add_argument(
        "--context",
        "-c",
        action="append",
        help="Context string or path to .txt/.md file (can be specified multiple times)",
    )
    script_parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Gemini model for script generation (default: gemini-3-pro-preview)",
    )

    # Audio command
    audio_parser = subparsers.add_parser("audio", help="Generate audio from voiceover script")
    audio_parser.add_argument("--script", "-s", help="Path to voiceover script")
    audio_parser.add_argument("--output", "-o", help="Output directory")
    audio_parser.add_argument(
        "--provider",
        choices=["gemini", "elevenlabs"],
        default="gemini",
        help="TTS provider to use (default: gemini)",
    )
    audio_parser.add_argument(
        "--voice",
        default=None,  # audio.py will handle the default (Orus or George)
        help="Voice name: Gemini (Puck, Orus, etc.) or ElevenLabs (preset: adam, bob, william, george; or any voice ID)",
    )
    audio_parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices for the provider",
    )
    audio_parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Gemini model for TTS (default: gemini-2.5-pro-preview-tts)",
    )

    # Translate command (image translation)
    translate_parser = subparsers.add_parser(
        "translate", help="Translate images to another language"
    )
    translate_parser.add_argument("--input", "-i", help="Input image file or folder")
    translate_parser.add_argument("--output", "-o", help="Output directory")
    translate_parser.add_argument(
        "--lang", "-l", default="French", help="Target language (default: French)"
    )
    translate_parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Gemini model for image translation (default: gemini-3-pro-image-preview)",
    )
    translate_parser.add_argument(
        "--no-branding",
        action="store_true",
        help="Disable montaigne.cc logo branding (enabled by default)",
    )
    translate_parser.add_argument(
        "--logo", help="Path to custom logo image (default: montaigne amber logo)"
    )

    # Localize command (full pipeline)
    loc_parser = subparsers.add_parser("localize", help="Full localization pipeline")
    loc_parser.add_argument("--pdf", "-p", help="Input PDF file")
    loc_parser.add_argument("--images", "-i", help="Input images folder (alternative to PDF)")
    loc_parser.add_argument("--script", "-s", help="Voiceover script for audio generation")
    loc_parser.add_argument("--output", "-o", help="Output directory")
    loc_parser.add_argument(
        "--lang", "-l", default="French", help="Target language (default: French)"
    )
    loc_parser.add_argument("--voice", default="Orus", help="TTS voice (default: Orus)")
    loc_parser.add_argument(
        "--dpi", type=int, default=150, help="PDF extraction DPI (default: 150)"
    )
    loc_parser.add_argument("--provider", choices=["gemini", "elevenlabs"], default="gemini")

    # PPT command
    ppt_parser = subparsers.add_parser("ppt", help="Create PowerPoint from PDF or images")
    ppt_parser.add_argument("--input", "-i", help="PDF file or images folder")
    ppt_parser.add_argument("--output", "-o", help="Output .pptx file")
    ppt_parser.add_argument("--script", "-s", help="Voiceover script for slide notes")
    ppt_parser.add_argument(
        "--dpi", type=int, default=150, help="PDF extraction DPI (default: 150)"
    )
    ppt_parser.add_argument(
        "--keep-images", action="store_true", help="Keep extracted images when converting PDF"
    )

    # Annotate command
    annotate_parser = subparsers.add_parser(
        "annotate",
        help="Launch interactive video/audio annotation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  essai annotate video.mp4              # Open annotation UI for video
  essai annotate --input audio.wav      # Open annotation UI for audio
  essai annotate                        # Auto-detect media file in current dir
  essai annotate video.mp4 --network    # Make accessible on local network
  essai annotate video.mp4 --export srt # Export annotations to SRT
  essai annotate video.mp4 --export vtt # Export annotations to WebVTT
  essai annotate video.mp4 --export json -o notes.json

Keyboard shortcuts in the annotation UI:
  Space       - Play/Pause
  I           - Set In point for range annotation
  O           - Set Out point for range annotation
  [ ]         - Step frame backward/forward
  Ctrl+Enter  - Submit annotation
  Escape      - Clear range / exit input
        """,
    )
    annotate_parser.add_argument("input", nargs="?", help="Video or audio file to annotate")
    annotate_parser.add_argument(
        "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)"
    )
    annotate_parser.add_argument(
        "--port", "-p", type=int, default=8765, help="Server port (default: 8765)"
    )
    annotate_parser.add_argument(
        "--network",
        action="store_true",
        help="Make server accessible on the network (binds to 0.0.0.0)",
    )
    annotate_parser.add_argument("--db", help="Custom SQLite database path for annotations")
    annotate_parser.add_argument(
        "--no-browser", action="store_true", help="Don't auto-open browser"
    )
    annotate_parser.add_argument(
        "--export",
        "-e",
        choices=["vtt", "srt", "json"],
        help="Export annotations instead of launching UI",
    )
    annotate_parser.add_argument("--output", "-o", help="Output file for export")

    # Video command
    video_parser = subparsers.add_parser("video", help="Generate video from slides and audio")
    video_parser.add_argument(
        "--pdf", "-p", help="PDF file (runs full pipeline: extract, script, audio, video)"
    )
    video_parser.add_argument("--images", "-i", help="Images directory (if not using --pdf)")
    video_parser.add_argument("--audio", "-a", help="Audio directory (if not using --pdf)")
    video_parser.add_argument(
        "--script", "-s", help="Existing voiceover script (optional with --pdf)"
    )
    video_parser.add_argument("--output", "-o", help="Output video file")
    video_parser.add_argument(
        "--resolution", "-r", default="1920:1080", help="Video resolution (default: 1920:1080)"
    )
    video_parser.add_argument(
        "--voice",
        default="Orus",
        help="Voice name: Gemini (Orus, Puck, etc.) or ElevenLabs (preset: adam, bob, etc.; or any voice ID)",
    )
    video_parser.add_argument("--provider", choices=["gemini", "elevenlabs"], default="gemini")
    video_parser.add_argument(
        "--context",
        "-c",
        action="append",
        help="Context string or path to .txt/.md file (can be specified multiple times)",
    )
    video_parser.add_argument(
        "--script-model",
        default=None,
        help="Gemini model for script generation (default: gemini-3-pro-preview)",
    )
    video_parser.add_argument(
        "--audio-model",
        default=None,
        help="Gemini model for TTS (default: gemini-2.5-pro-preview-tts)",
    )
    video_parser.add_argument(
        "--no-branding",
        action="store_true",
        help="Disable montaigne.cc logo branding (enabled by default)",
    )
    video_parser.add_argument(
        "--logo", help="Path to custom logo image (default: montaigne amber logo)"
    )

    # Cloud command group
    cloud_parser = subparsers.add_parser(
        "cloud",
        help="Run commands via cloud API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cloud Commands:
  essai cloud health                    # Check cloud API health
  essai cloud video --pdf presentation.pdf  # Generate video in cloud
  essai cloud status {job_id}           # Check job status
  essai cloud download {job_id} -o out.mp4  # Download output
  essai cloud jobs                      # List recent jobs

Environment:
  MONTAIGNE_API_URL    Cloud API URL (default: configured endpoint)
        """,
    )
    cloud_parser.add_argument("--api-url", help="Cloud API URL (overrides MONTAIGNE_API_URL)")
    cloud_subparsers = cloud_parser.add_subparsers(dest="cloud_command", help="Cloud commands")

    # Cloud health command
    cloud_subparsers.add_parser("health", help="Check cloud API health")

    # Cloud video command
    cloud_video_parser = cloud_subparsers.add_parser("video", help="Generate video via cloud")
    cloud_video_parser.add_argument("--pdf", "-p", required=True, help="PDF file to process")
    cloud_video_parser.add_argument("--output", "-o", help="Output video file")
    cloud_video_parser.add_argument(
        "--resolution", "-r", default="1920:1080", help="Video resolution (default: 1920:1080)"
    )
    cloud_video_parser.add_argument(
        "--voice",
        default="Orus",
        help="Voice name: Gemini (Orus, Puck, etc.) or ElevenLabs (preset or any voice ID)",
    )
    cloud_video_parser.add_argument(
        "--context", "-c", help="Additional context for script generation"
    )
    cloud_video_parser.add_argument(
        "--wait/--no-wait",
        dest="wait",
        action="store_true",
        default=True,
        help="Wait for completion (default: wait)",
    )
    cloud_video_parser.add_argument(
        "--no-wait",
        dest="wait",
        action="store_false",
        help="Don't wait, return job ID immediately",
    )

    # Cloud status command
    cloud_status_parser = cloud_subparsers.add_parser("status", help="Check job status")
    cloud_status_parser.add_argument("job_id", help="Job ID to check")

    # Cloud download command
    cloud_download_parser = cloud_subparsers.add_parser("download", help="Download job output")
    cloud_download_parser.add_argument("job_id", help="Job ID to download from")
    cloud_download_parser.add_argument("--output", "-o", required=True, help="Output file path")
    cloud_download_parser.add_argument(
        "--file",
        default="video",
        choices=["video", "script", "audio", "images"],
        help="File type to download (default: video)",
    )

    # Cloud jobs command
    cloud_jobs_parser = cloud_subparsers.add_parser("jobs", help="List recent jobs")
    cloud_jobs_parser.add_argument("--limit", type=int, default=20, help="Max jobs to list")
    cloud_jobs_parser.add_argument(
        "--status",
        choices=["pending", "processing", "completed", "failed"],
        help="Filter by status",
    )

    args = parser.parse_args()

    # Setup logging based on flags
    setup_logging(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
        log_file=getattr(args, "log_file", None),
    )

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "setup": cmd_setup,
        "models": cmd_models,
        "edit": cmd_edit,
        "pdf": cmd_pdf,
        "script": cmd_script,
        "audio": cmd_audio,
        "video": cmd_video,
        "translate": cmd_images,
        "localize": cmd_localize,
        "ppt": cmd_ppt,
        "annotate": cmd_annotate,
    }

    # Handle cloud command specially (has subcommands)
    if args.command == "cloud":
        cloud_commands = {
            "health": cmd_cloud_health,
            "video": cmd_cloud_video,
            "status": cmd_cloud_status,
            "download": cmd_cloud_download,
            "jobs": cmd_cloud_jobs,
        }
        if args.cloud_command is None:
            cloud_parser.print_help()
            return
        cloud_commands[args.cloud_command](args)
    else:
        commands[args.command](args)


if __name__ == "__main__":
    main()
