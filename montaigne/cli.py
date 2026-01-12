"""Command-line interface for Montaigne media processing toolkit."""

import argparse
import os
import sys
from pathlib import Path

from . import __version__


def cmd_setup(args):
    """Install dependencies and verify configuration."""
    from .config import check_dependencies, install_dependencies

    print("=== Montaigne Setup ===\n")

    if not check_dependencies():
        install_dependencies()
    else:
        print("All dependencies installed.")

    # Verify API key
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(f"API Key: {'*' * 10}{api_key[-4:]}")
    else:
        print("Warning: GEMINI_API_KEY not found in .env file")
        print("Create a .env file with: GEMINI_API_KEY=your-api-key")

    print("\nSetup complete!")


def cmd_pdf(args):
    """Extract PDF pages to images."""
    from .config import check_dependencies
    from .pdf import extract_pdf_pages

    if not check_dependencies():
        print("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    print("=== PDF Extraction ===")

    pdf_path = Path(args.input)
    output_dir = Path(args.output) if args.output else None

    extract_pdf_pages(pdf_path, output_dir=output_dir, dpi=args.dpi, image_format=args.format)


def cmd_script(args):
    """Generate voiceover scripts from PDF or images."""
    from .config import check_dependencies
    from .scripts import generate_scripts

    if not check_dependencies():
        print("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    print("=== Script Generation ===")

    input_path = Path(args.input) if args.input else None

    # Auto-detect PDF or images
    if input_path is None:
        cwd = Path.cwd()
        pdfs = list(cwd.glob("*.pdf"))
        if pdfs:
            input_path = pdfs[0]
            print(f"Auto-detected: {input_path.name}")
        else:
            image_dirs = [d for d in cwd.iterdir() if d.is_dir() and "images" in d.name.lower()]
            if image_dirs:
                input_path = image_dirs[0]
                print(f"Auto-detected: {input_path.name}")
            else:
                print("No PDF or image folder found. Use --input to specify one.")
                return

    output_path = Path(args.output) if args.output else None
    context = args.context or ""

    generate_scripts(input_path, output_path=output_path, context=context)


def cmd_audio(args):
    """Generate audio from voiceover scripts."""
    from .config import check_dependencies
    from .audio import generate_audio

    if not check_dependencies():
        print("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    print("=== Audio Generation ===")

    script_path = Path(args.script) if args.script else None

    # Auto-detect voiceover scripts
    if script_path is None:
        cwd = Path.cwd()
        scripts = list(cwd.glob("*voiceover*.md"))
        if scripts:
            script_path = scripts[0]
            print(f"Auto-detected: {script_path.name}")
        else:
            print("No voiceover script found. Use --script to specify one.")
            return

    output_dir = Path(args.output) if args.output else None
    generate_audio(script_path, output_dir=output_dir, voice=args.voice)


def cmd_images(args):
    """Translate images to target language."""
    from .config import check_dependencies
    from .images import translate_images

    if not check_dependencies():
        print("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    print("=== Image Translation ===")

    input_path = Path(args.input) if args.input else None

    # Auto-detect images
    if input_path is None:
        cwd = Path.cwd()
        images = list(cwd.glob("*.png")) + list(cwd.glob("*.jpg"))
        if images:
            input_path = images[0]
            print(f"Auto-detected: {input_path.name}")
        else:
            print("No images found. Use --input to specify image or folder.")
            return

    output_dir = Path(args.output) if args.output else None
    translate_images(input_path, output_dir=output_dir, target_lang=args.lang)


def cmd_video(args):
    """Generate video from slides and audio."""
    from .video import generate_video, generate_video_from_pdf, check_ffmpeg

    if not check_ffmpeg():
        print("Error: ffmpeg not found. Please install ffmpeg to generate videos.")
        print("  Windows: choco install ffmpeg  or  winget install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        sys.exit(1)

    print("=== Video Generation ===")

    # If PDF provided, run full pipeline
    if args.pdf:
        pdf_path = Path(args.pdf)
        script_path = Path(args.script) if args.script else None
        output_path = Path(args.output) if args.output else None

        generate_video_from_pdf(
            pdf_path,
            script_path=script_path,
            output_path=output_path,
            resolution=args.resolution,
            voice=args.voice,
            context=args.context or "",
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
            print(f"Auto-detected images: {images_dir.name}")
        else:
            print("No images directory found. Use --images to specify one.")
            return

    if audio_dir is None:
        cwd = Path.cwd()
        audio_dirs = [d for d in cwd.iterdir() if d.is_dir() and "_audio" in d.name]
        if audio_dirs:
            audio_dir = audio_dirs[0]
            print(f"Auto-detected audio: {audio_dir.name}")
        else:
            print("No audio directory found. Use --audio to specify one.")
            return

    output_path = Path(args.output) if args.output else None

    generate_video(images_dir, audio_dir, output_path, resolution=args.resolution)


def cmd_ppt(args):
    """Create PowerPoint from PDF or images folder."""
    from .config import check_dependencies
    from .ppt import create_pptx

    if not check_dependencies():
        print("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    print("=== PowerPoint Generation ===")

    input_path = Path(args.input) if args.input else None

    # Auto-detect input
    if input_path is None:
        cwd = Path.cwd()
        # First try to find a PDF
        pdfs = list(cwd.glob("*.pdf"))
        if pdfs:
            input_path = pdfs[0]
            print(f"Auto-detected PDF: {input_path.name}")
        else:
            # Try to find an images folder
            image_dirs = [d for d in cwd.iterdir() if d.is_dir() and "images" in d.name.lower()]
            if image_dirs:
                input_path = image_dirs[0]
                print(f"Auto-detected folder: {input_path.name}")
            else:
                print("No PDF or images folder found. Use --input to specify one.")
                return

    output_path = Path(args.output) if args.output else None
    script_path = Path(args.script) if args.script else None

    # Auto-detect script if not provided
    if script_path is None:
        cwd = Path.cwd()
        scripts = list(cwd.glob("*voiceover*.md"))
        if scripts:
            script_path = scripts[0]
            print(f"Auto-detected script: {script_path.name}")

    create_pptx(
        input_path,
        output_path=output_path,
        script_path=script_path,
        dpi=args.dpi,
        keep_images=args.keep_images,
    )


def cmd_webapp(args):
    """Launch the Streamlit web application."""
    import subprocess

    try:
        import streamlit  # noqa: F401
    except ImportError:
        print("Streamlit not installed. Install with:")
        print("  pip install montaigne[webapp]")
        sys.exit(1)

    print("=== Launching Montaigne Web App ===")
    print("Opening in browser...\n")

    # Get the path to app.py
    app_path = Path(__file__).parent / "app.py"

    # Launch streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


# =============================================================================
# Cloud Commands
# =============================================================================

def cmd_cloud_health(args):
    """Check cloud API health."""
    import requests
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()
    print(f"Checking cloud API: {api_url}")

    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        response.raise_for_status()
        data = response.json()

        print(f"\nStatus: {data.get('status', 'unknown')}")
        print(f"Version: {data.get('version', 'unknown')}")
        print(f"FFmpeg: {'available' if data.get('ffmpeg') else 'not available'}")
    except requests.exceptions.ConnectionError:
        print(f"\nError: Could not connect to {api_url}")
        print("Make sure the cloud API is deployed and the URL is correct.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


def cmd_cloud_video(args):
    """Generate video via cloud API."""
    import requests
    import time
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()
    pdf_path = Path(args.pdf)

    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    print(f"=== Cloud Video Generation ===")
    print(f"API: {api_url}")
    print(f"PDF: {pdf_path.name}")

    # Step 1: Get upload URL
    print("\nStep 1: Requesting upload URL...")
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
    print(f"Job ID: {job_id}")

    # Step 2: Upload PDF
    print(f"\nStep 2: Uploading {pdf_path.name}...")
    with open(pdf_path, "rb") as f:
        upload_response = requests.put(
            upload_data["upload_url"],
            data=f,
            headers={"Content-Type": "application/pdf"},
        )
        upload_response.raise_for_status()
    print("Upload complete.")

    # Step 3: Start processing
    print("\nStep 3: Starting video generation...")
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
        print(f"\nJob submitted. Check status with:")
        print(f"  essai cloud status {job_id}")
        print(f"\nDownload when complete with:")
        print(f"  essai cloud download {job_id} -o output.mp4")
        return

    # Step 4: Wait for completion
    print("\nStep 4: Processing...")
    last_message = ""
    while True:
        response = requests.get(f"{api_url}/jobs/{job_id}/status")
        response.raise_for_status()
        status_data = response.json()

        status = status_data.get("status")
        progress = status_data.get("progress", {})
        message = progress.get("message", "")

        if message != last_message:
            print(f"  {message}")
            last_message = message

        if status == "completed":
            break
        elif status == "failed":
            error = status_data.get("error", {})
            print(f"\nError: {error.get('message', 'Unknown error')}")
            sys.exit(1)

        time.sleep(2)

    # Step 5: Download video
    output_path = Path(args.output) if args.output else Path(f"{pdf_path.stem}_video.mp4")
    print(f"\nStep 5: Downloading video to {output_path}...")

    response = requests.get(f"{api_url}/jobs/{job_id}/download?file=video")
    response.raise_for_status()
    download_data = response.json()

    video_response = requests.get(download_data["download_url"], stream=True)
    video_response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in video_response.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nComplete! Video saved to: {output_path} ({size_mb:.1f} MB)")


def cmd_cloud_status(args):
    """Check job status."""
    import requests
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()

    response = requests.get(f"{api_url}/jobs/{args.job_id}/status")

    if response.status_code == 404:
        print(f"Job not found: {args.job_id}")
        sys.exit(1)

    response.raise_for_status()
    data = response.json()

    print(f"Job ID: {data.get('job_id')}")
    print(f"Status: {data.get('status')}")
    print(f"Pipeline: {data.get('pipeline', 'unknown')}")

    if data.get("progress"):
        progress = data["progress"]
        print(f"\nProgress:")
        print(f"  Step: {progress.get('step')}")
        if progress.get("current") is not None:
            print(f"  Progress: {progress.get('current')}/{progress.get('total')}")
        if progress.get("message"):
            print(f"  Message: {progress.get('message')}")

    if data.get("created_at"):
        print(f"\nCreated: {data.get('created_at')}")
    if data.get("started_at"):
        print(f"Started: {data.get('started_at')}")
    if data.get("completed_at"):
        print(f"Completed: {data.get('completed_at')}")

    if data.get("output"):
        output = data["output"]
        print(f"\nOutput:")
        if output.get("video_size_bytes"):
            size_mb = output["video_size_bytes"] / (1024 * 1024)
            print(f"  Video size: {size_mb:.1f} MB")
        if output.get("download_expires"):
            print(f"  Download expires: {output['download_expires']}")

    if data.get("error"):
        error = data["error"]
        print(f"\nError: {error.get('message')}")


def cmd_cloud_download(args):
    """Download job output."""
    import requests
    from .cloud_config import get_api_url

    api_url = args.api_url or get_api_url()
    output_path = Path(args.output)

    print(f"Downloading {args.file} from job {args.job_id}...")

    response = requests.get(f"{api_url}/jobs/{args.job_id}/download?file={args.file}")

    if response.status_code == 404:
        print(f"Job or file not found: {args.job_id}")
        sys.exit(1)
    elif response.status_code == 400:
        print(f"Job not completed yet. Check status with: essai cloud status {args.job_id}")
        sys.exit(1)

    response.raise_for_status()
    download_data = response.json()

    print(f"File size: {download_data['size_bytes'] / (1024 * 1024):.1f} MB")
    print(f"Downloading to: {output_path}")

    file_response = requests.get(download_data["download_url"], stream=True)
    file_response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in file_response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Download complete: {output_path}")


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
        print("No jobs found.")
        return

    print(f"{'Job ID':<30} {'Status':<12} {'Pipeline':<10} {'Created'}")
    print("-" * 80)
    for job in jobs:
        created = job.get("created_at", "")[:19] if job.get("created_at") else ""
        print(f"{job['job_id']:<30} {job.get('status', ''):<12} {job.get('pipeline', ''):<10} {created}")


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
        print("Dependencies not installed. Run: essai setup")
        sys.exit(1)

    print("=== Montaigne Localization Pipeline ===\n")

    project_dir = Path.cwd()
    output_base = (
        Path(args.output) if args.output else project_dir / f"localized_{args.lang.lower()}"
    )
    output_base.mkdir(parents=True, exist_ok=True)

    images_to_translate = []

    # Step 1: Extract PDF if provided
    if args.pdf:
        pdf_path = Path(args.pdf)
        print("Step 1: Extracting PDF pages...")
        images_dir = output_base / "source_images"
        extracted = extract_pdf_pages(pdf_path, output_dir=images_dir, dpi=args.dpi)
        images_to_translate = extracted
        print()
    elif args.images:
        images_to_translate = [Path(args.images)]
    else:
        # Auto-detect PDF or images
        pdfs = list(project_dir.glob("*.pdf"))
        if pdfs:
            print(f"Step 1: Auto-detected PDF: {pdfs[0].name}")
            images_dir = output_base / "source_images"
            extracted = extract_pdf_pages(pdfs[0], output_dir=images_dir, dpi=args.dpi)
            images_to_translate = extracted
            print()

    # Step 2: Translate images
    if images_to_translate:
        print(f"Step 2: Translating images to {args.lang}...")
        if isinstance(images_to_translate, list) and len(images_to_translate) > 0:
            # If we have a list from PDF extraction, use the parent dir
            source_dir = images_to_translate[0].parent
        else:
            source_dir = Path(images_to_translate)

        translated_dir = output_base / "translated_images"
        translate_images(source_dir, output_dir=translated_dir, target_lang=args.lang)
        print()

    # Step 3: Generate audio if script provided
    if args.script:
        print("Step 3: Generating audio...")
        script_path = Path(args.script)
        audio_dir = output_base / "audio"
        generate_audio(script_path, output_dir=audio_dir, voice=args.voice)
    else:
        # Auto-detect voiceover script
        scripts = list(project_dir.glob("*voiceover*.md"))
        if scripts:
            print(f"Step 3: Auto-detected script: {scripts[0].name}")
            audio_dir = output_base / "audio"
            generate_audio(scripts[0], output_dir=audio_dir, voice=args.voice)

    print("\n=== Localization Complete ===")
    print(f"Output: {output_base}/")


def main():
    parser = argparse.ArgumentParser(
        prog="essai",
        description="Montaigne - Media Processing Toolkit for Presentation Localization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  essai setup                           # Install dependencies
  essai webapp                          # Launch web editor
  essai pdf presentation.pdf            # Extract PDF to images
  essai script --input presentation.pdf # Generate voiceover script from PDF
  essai audio --script voiceover.md     # Generate audio from script
  essai video --pdf presentation.pdf    # Generate video from PDF (full pipeline)
  essai images --input slides/          # Translate images
  essai ppt --input presentation.pdf    # Convert PDF to PowerPoint
  essai ppt --input slides/ --script voiceover.md  # Images to PPT with notes
  essai localize --pdf deck.pdf --script script.md --lang Spanish

Web Editor:
  essai webapp                          # Launch Streamlit slide editor

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

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    subparsers.add_parser("setup", help="Install dependencies and verify configuration")

    # Webapp command
    subparsers.add_parser("webapp", help="Launch the Streamlit web application")

    # PDF command
    pdf_parser = subparsers.add_parser("pdf", help="Extract PDF pages to images")
    pdf_parser.add_argument("input", help="Path to PDF file")
    pdf_parser.add_argument("--output", "-o", help="Output directory")
    pdf_parser.add_argument("--dpi", type=int, default=150, help="Image resolution (default: 150)")
    pdf_parser.add_argument("--format", choices=["png", "jpg"], default="png", help="Output format")

    # Script command
    script_parser = subparsers.add_parser(
        "script", help="Generate voiceover script from PDF/images"
    )
    script_parser.add_argument("--input", "-i", help="PDF file or images folder")
    script_parser.add_argument("--output", "-o", help="Output markdown file")
    script_parser.add_argument("--context", "-c", help="Presentation context/description")

    # Audio command
    audio_parser = subparsers.add_parser("audio", help="Generate audio from voiceover script")
    audio_parser.add_argument("--script", "-s", help="Path to voiceover script")
    audio_parser.add_argument("--output", "-o", help="Output directory")
    audio_parser.add_argument(
        "--voice",
        default="Orus",
        choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"],
        help="TTS voice (default: Orus)",
    )

    # Images command
    images_parser = subparsers.add_parser("images", help="Translate images")
    images_parser.add_argument("--input", "-i", help="Input image file or folder")
    images_parser.add_argument("--output", "-o", help="Output directory")
    images_parser.add_argument(
        "--lang", "-l", default="French", help="Target language (default: French)"
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
        choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"],
        help="TTS voice for audio generation (default: Orus)",
    )
    video_parser.add_argument(
        "--context", "-c", help="Additional context/instructions for script generation"
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
    cloud_parser.add_argument(
        "--api-url", help="Cloud API URL (overrides MONTAIGNE_API_URL)"
    )
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
        choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"],
        help="TTS voice (default: Orus)",
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

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "setup": cmd_setup,
        "webapp": cmd_webapp,
        "pdf": cmd_pdf,
        "script": cmd_script,
        "audio": cmd_audio,
        "video": cmd_video,
        "images": cmd_images,
        "localize": cmd_localize,
        "ppt": cmd_ppt,
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
