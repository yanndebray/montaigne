"""Command-line interface for Kant media processing toolkit."""

import argparse
import os
import sys
from pathlib import Path

from . import __version__


def cmd_setup(args):
    """Install dependencies and verify configuration."""
    from .config import check_dependencies, install_dependencies, load_api_key

    print("=== Kant Setup ===\n")

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
        print("Dependencies not installed. Run: kant setup")
        sys.exit(1)

    print("=== PDF Extraction ===")

    pdf_path = Path(args.input)
    output_dir = Path(args.output) if args.output else None

    extract_pdf_pages(
        pdf_path,
        output_dir=output_dir,
        dpi=args.dpi,
        image_format=args.format
    )


def cmd_script(args):
    """Generate voiceover scripts from PDF or images."""
    from .config import check_dependencies
    from .scripts import generate_scripts

    if not check_dependencies():
        print("Dependencies not installed. Run: kant setup")
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
        print("Dependencies not installed. Run: kant setup")
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
        print("Dependencies not installed. Run: kant setup")
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
        print("Dependencies not installed. Run: kant setup")
        sys.exit(1)

    print("=== Kant Localization Pipeline ===\n")

    project_dir = Path.cwd()
    output_base = Path(args.output) if args.output else project_dir / f"localized_{args.lang.lower()}"
    output_base.mkdir(parents=True, exist_ok=True)

    images_to_translate = []

    # Step 1: Extract PDF if provided
    if args.pdf:
        pdf_path = Path(args.pdf)
        print(f"Step 1: Extracting PDF pages...")
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
        print(f"Step 3: Generating audio...")
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

    print(f"\n=== Localization Complete ===")
    print(f"Output: {output_base}/")


def main():
    parser = argparse.ArgumentParser(
        prog="kant",
        description="Kant - Media Processing Toolkit for Presentation Localization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kant setup                           # Install dependencies
  kant pdf presentation.pdf            # Extract PDF to images
  kant script --input presentation.pdf # Generate voiceover script from PDF
  kant audio --script voiceover.md     # Generate audio from script
  kant images --input slides/          # Translate images
  kant localize --pdf deck.pdf --script script.md --lang Spanish

Full pipeline:
  kant pdf presentation.pdf            # Step 1: Extract slides
  kant script --input presentation.pdf # Step 2: Generate script
  kant audio --script voiceover.md     # Step 3: Generate audio
        """
    )
    parser.add_argument("--version", action="version", version=f"kant {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    subparsers.add_parser("setup", help="Install dependencies and verify configuration")

    # PDF command
    pdf_parser = subparsers.add_parser("pdf", help="Extract PDF pages to images")
    pdf_parser.add_argument("input", help="Path to PDF file")
    pdf_parser.add_argument("--output", "-o", help="Output directory")
    pdf_parser.add_argument("--dpi", type=int, default=150, help="Image resolution (default: 150)")
    pdf_parser.add_argument("--format", choices=["png", "jpg"], default="png", help="Output format")

    # Script command
    script_parser = subparsers.add_parser("script", help="Generate voiceover script from PDF/images")
    script_parser.add_argument("--input", "-i", help="PDF file or images folder")
    script_parser.add_argument("--output", "-o", help="Output markdown file")
    script_parser.add_argument("--context", "-c", help="Presentation context/description")

    # Audio command
    audio_parser = subparsers.add_parser("audio", help="Generate audio from voiceover script")
    audio_parser.add_argument("--script", "-s", help="Path to voiceover script")
    audio_parser.add_argument("--output", "-o", help="Output directory")
    audio_parser.add_argument("--voice", default="Orus",
                              choices=["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Orus"],
                              help="TTS voice (default: Orus)")

    # Images command
    images_parser = subparsers.add_parser("images", help="Translate images")
    images_parser.add_argument("--input", "-i", help="Input image file or folder")
    images_parser.add_argument("--output", "-o", help="Output directory")
    images_parser.add_argument("--lang", "-l", default="French", help="Target language (default: French)")

    # Localize command (full pipeline)
    loc_parser = subparsers.add_parser("localize", help="Full localization pipeline")
    loc_parser.add_argument("--pdf", "-p", help="Input PDF file")
    loc_parser.add_argument("--images", "-i", help="Input images folder (alternative to PDF)")
    loc_parser.add_argument("--script", "-s", help="Voiceover script for audio generation")
    loc_parser.add_argument("--output", "-o", help="Output directory")
    loc_parser.add_argument("--lang", "-l", default="French", help="Target language (default: French)")
    loc_parser.add_argument("--voice", default="Orus", help="TTS voice (default: Orus)")
    loc_parser.add_argument("--dpi", type=int, default=150, help="PDF extraction DPI (default: 150)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "setup": cmd_setup,
        "pdf": cmd_pdf,
        "script": cmd_script,
        "audio": cmd_audio,
        "images": cmd_images,
        "localize": cmd_localize,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
