"""Script generation from PDF slides using Gemini AI."""

import base64
import mimetypes
from pathlib import Path
from typing import List, Optional

from .config import get_gemini_client

IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".gif", ".webp"}
SCRIPT_MODEL = "gemini-2.5-flash"


def generate_slide_script(
    image_path: Path,
    slide_number: int = 1,
    context: str = "",
    client=None
) -> dict:
    """
    Generate a voiceover script for a single slide image using Gemini.

    Args:
        image_path: Path to the slide image
        slide_number: Slide number for the script header
        context: Optional context about the presentation
        client: Optional pre-configured Gemini client

    Returns:
        Dict with 'number', 'title', 'duration', and 'text' keys
    """
    from google.genai import types

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if client is None:
        client = get_gemini_client()

    # Read source image
    with open(image_path, "rb") as f:
        image_data = f.read()

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/png"

    # Build prompt
    context_note = f"\nPresentation context: {context}" if context else ""

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(mime_type=mime_type, data=image_data),
                types.Part.from_text(text=f"""Analyze this presentation slide and generate a voiceover script for it.
{context_note}

Please provide:
1. A short title for the slide (max 50 characters)
2. Estimated duration for reading the script (e.g., "30-45 seconds")
3. A natural, conversational voiceover script that:
   - Explains the key points on the slide
   - Flows naturally when spoken aloud
   - Is engaging and clear for the audience
   - Does not simply read bullet points verbatim
   - Adds context and transitions where appropriate

Format your response EXACTLY as:
TITLE: [slide title]
DURATION: [estimated duration]
SCRIPT:
[voiceover text here]"""),
            ],
        ),
    ]

    response = client.models.generate_content(
        model=SCRIPT_MODEL,
        contents=contents,
    )

    # Parse response
    text = response.text

    title = f"Slide {slide_number}"
    duration = "30-45 seconds"
    script = text

    # Extract title
    if "TITLE:" in text:
        title_line = text.split("TITLE:")[1].split("\n")[0].strip()
        title = title_line[:50] if title_line else title

    # Extract duration
    if "DURATION:" in text:
        duration_line = text.split("DURATION:")[1].split("\n")[0].strip()
        duration = duration_line if duration_line else duration

    # Extract script
    if "SCRIPT:" in text:
        script = text.split("SCRIPT:")[1].strip()

    return {
        "number": slide_number,
        "title": title,
        "duration": duration,
        "text": script
    }


def generate_scripts(
    input_path: Path,
    output_path: Optional[Path] = None,
    context: str = ""
) -> Path:
    """
    Generate voiceover scripts from PDF or image folder.

    Args:
        input_path: PDF file or directory containing slide images
        output_path: Path for output markdown file (default: {input_stem}_voiceover.md)
        context: Optional context about the presentation

    Returns:
        Path to generated markdown script file
    """
    from .pdf import extract_pdf_pages

    input_path = Path(input_path)

    # Handle PDF input
    if input_path.suffix.lower() == ".pdf":
        print(f"Extracting pages from PDF: {input_path.name}")
        images_dir = input_path.parent / f"{input_path.stem}_images"
        images = extract_pdf_pages(input_path, output_dir=images_dir)
        base_name = input_path.stem
    elif input_path.is_dir():
        images = sorted([
            f for f in input_path.iterdir()
            if f.suffix.lower() in IMAGE_EXTENSIONS
        ])
        base_name = input_path.name
    elif input_path.is_file() and input_path.suffix.lower() in IMAGE_EXTENSIONS:
        images = [input_path]
        base_name = input_path.stem
    else:
        raise FileNotFoundError(f"Input not found or unsupported: {input_path}")

    if not images:
        raise ValueError(f"No images found in {input_path}")

    # Determine output path
    if output_path is None:
        output_path = input_path.parent / f"{base_name}_voiceover.md"
    output_path = Path(output_path)

    print(f"\nGenerating scripts for {len(images)} slide(s)...")

    client = get_gemini_client()
    slides_data = []

    for i, image_path in enumerate(images, 1):
        print(f"  Analyzing slide {i}: {image_path.name}...")

        try:
            slide_data = generate_slide_script(
                image_path,
                slide_number=i,
                context=context,
                client=client
            )
            slides_data.append(slide_data)
            print(f"    Generated: {slide_data['title'][:40]}...")
        except Exception as e:
            print(f"    Error: {e}")
            slides_data.append({
                "number": i,
                "title": f"Slide {i}",
                "duration": "30 seconds",
                "text": f"[Script generation failed: {e}]"
            })

    # Generate markdown output
    markdown = _format_scripts_markdown(slides_data, base_name)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nGenerated voiceover script: {output_path}")
    return output_path


def _format_scripts_markdown(slides: List[dict], title: str) -> str:
    """Format slide scripts as markdown."""
    lines = [
        f"# Voiceover Script: {title}",
        "",
        f"Total slides: {len(slides)}",
        "",
        "---",
        ""
    ]

    for slide in slides:
        lines.extend([
            f"## SLIDE {slide['number']}: {slide['title']}",
            "",
            f"**[Duration: ~{slide['duration']}]**",
            "",
            slide['text'],
            "",
            "---",
            ""
        ])

    return "\n".join(lines)
