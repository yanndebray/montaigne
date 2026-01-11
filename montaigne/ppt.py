"""PowerPoint generation from PDF or images."""

import re
from pathlib import Path
from typing import List, Optional

IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".gif", ".webp", ".bmp", ".tiff"}


def parse_script_to_slides(script_path: Path) -> List[str]:
    """
    Parse a voiceover script markdown file and extract text for each slide.

    Expects format like:
        ## SLIDE 1: Title
        ...script text...
        ---
        ## SLIDE 2: Title
        ...

    Args:
        script_path: Path to the markdown script file

    Returns:
        List of script texts, one per slide (index 0 = slide 1)
    """
    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by slide headers (## SLIDE N: or ## SLIDE N —)
    slide_pattern = r"##\s+SLIDE\s+\d+[:\s—–-]"
    parts = re.split(slide_pattern, content, flags=re.IGNORECASE)

    # First part is header content before first slide, skip it
    slide_texts = []
    for part in parts[1:]:
        # Remove duration markers and separators
        text = re.sub(r"\*\*\[Duration:[^\]]*\]\*\*", "", part)
        text = re.sub(r"^---\s*$", "", text, flags=re.MULTILINE)
        # Clean up extra whitespace
        text = "\n".join(line.strip() for line in text.strip().split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text)
        slide_texts.append(text.strip())

    return slide_texts


def images_to_pptx(
    images: List[Path], output_path: Path, notes: Optional[List[str]] = None
) -> Path:
    """
    Create a PowerPoint presentation from a list of images.

    Args:
        images: List of image file paths
        output_path: Path for output .pptx file
        notes: Optional list of notes text, one per slide

    Returns:
        Path to the created PowerPoint file
    """
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()

    # Set slide dimensions to 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Use blank layout
    blank_layout = prs.slide_layouts[6]

    for i, image_path in enumerate(images):
        image_path = Path(image_path)
        if not image_path.exists():
            print(f"  Warning: Image not found, skipping: {image_path}")
            continue

        slide = prs.slides.add_slide(blank_layout)

        # Add image to fill the slide
        # Calculate dimensions to fit while maintaining aspect ratio
        from PIL import Image

        with Image.open(image_path) as img:
            img_width, img_height = img.size

        slide_width = prs.slide_width
        slide_height = prs.slide_height

        # Scale to fit slide
        width_ratio = slide_width / Inches(img_width / 96)  # assuming 96 DPI
        height_ratio = slide_height / Inches(img_height / 96)
        scale = min(width_ratio, height_ratio, 1.0)  # Don't scale up

        pic_width = Inches(img_width / 96) * scale
        pic_height = Inches(img_height / 96) * scale

        # Center the image
        left = (slide_width - pic_width) / 2
        top = (slide_height - pic_height) / 2

        slide.shapes.add_picture(str(image_path), left, top, pic_width, pic_height)

        # Add notes if provided
        if notes and i < len(notes) and notes[i]:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = notes[i]

        print(f"  Added slide {i + 1}: {image_path.name}")

    prs.save(output_path)
    return output_path


def pdf_to_pptx(
    pdf_path: Path,
    output_path: Optional[Path] = None,
    script_path: Optional[Path] = None,
    dpi: int = 150,
    keep_images: bool = False,
) -> Path:
    """
    Convert a PDF to a PowerPoint presentation.

    Each page of the PDF becomes a slide with the page as an image.

    Args:
        pdf_path: Path to the PDF file
        output_path: Path for output .pptx file (default: {pdf_stem}.pptx)
        script_path: Optional path to voiceover script for slide notes
        dpi: Resolution for PDF extraction (default: 150)
        keep_images: If True, keep extracted images; if False, delete them

    Returns:
        Path to the created PowerPoint file
    """
    from .pdf import extract_pdf_pages
    import tempfile
    import shutil

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_path is None:
        output_path = pdf_path.parent / f"{pdf_path.stem}.pptx"
    output_path = Path(output_path)

    print(f"Converting PDF to PowerPoint: {pdf_path.name}")

    # Extract PDF pages to temporary directory or keep
    if keep_images:
        images_dir = pdf_path.parent / f"{pdf_path.stem}_images"
    else:
        images_dir = Path(tempfile.mkdtemp(prefix="montaigne_pdf_"))

    try:
        images = extract_pdf_pages(pdf_path, output_dir=images_dir, dpi=dpi)

        # Parse script if provided
        notes = None
        if script_path:
            script_path = Path(script_path)
            print(f"Parsing script for notes: {script_path.name}")
            notes = parse_script_to_slides(script_path)
            if len(notes) != len(images):
                print(f"  Warning: Script has {len(notes)} slides but PDF has {len(images)} pages")

        # Create PowerPoint
        print(f"\nCreating PowerPoint with {len(images)} slides...")
        images_to_pptx(images, output_path, notes=notes)

    finally:
        # Clean up temporary images if not keeping
        if not keep_images and images_dir.exists():
            shutil.rmtree(images_dir)

    print(f"\nCreated: {output_path}")
    return output_path


def folder_to_pptx(
    folder_path: Path, output_path: Optional[Path] = None, script_path: Optional[Path] = None
) -> Path:
    """
    Convert a folder of images to a PowerPoint presentation.

    Images are sorted alphabetically/numerically and each becomes a slide.

    Args:
        folder_path: Path to folder containing images
        output_path: Path for output .pptx file (default: {folder_name}.pptx)
        script_path: Optional path to voiceover script for slide notes

    Returns:
        Path to the created PowerPoint file
    """
    folder_path = Path(folder_path)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    if not folder_path.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    # Find all images in folder
    images = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS])

    if not images:
        raise ValueError(f"No images found in {folder_path}")

    if output_path is None:
        output_path = folder_path.parent / f"{folder_path.name}.pptx"
    output_path = Path(output_path)

    print(f"Creating PowerPoint from {len(images)} images in: {folder_path.name}")

    # Parse script if provided
    notes = None
    if script_path:
        script_path = Path(script_path)
        print(f"Parsing script for notes: {script_path.name}")
        notes = parse_script_to_slides(script_path)
        if len(notes) != len(images):
            print(f"  Warning: Script has {len(notes)} slides but folder has {len(images)} images")

    # Create PowerPoint
    print(f"\nCreating PowerPoint with {len(images)} slides...")
    images_to_pptx(images, output_path, notes=notes)

    print(f"\nCreated: {output_path}")
    return output_path


def create_pptx(
    input_path: Path,
    output_path: Optional[Path] = None,
    script_path: Optional[Path] = None,
    dpi: int = 150,
    keep_images: bool = False,
) -> Path:
    """
    Create a PowerPoint presentation from PDF or image folder.

    This is the main entry point that auto-detects input type.

    Args:
        input_path: Path to PDF file or folder of images
        output_path: Path for output .pptx file
        script_path: Optional path to voiceover script for slide notes
        dpi: Resolution for PDF extraction (default: 150)
        keep_images: If True and input is PDF, keep extracted images

    Returns:
        Path to the created PowerPoint file
    """
    input_path = Path(input_path)

    if input_path.suffix.lower() == ".pdf":
        return pdf_to_pptx(
            input_path,
            output_path=output_path,
            script_path=script_path,
            dpi=dpi,
            keep_images=keep_images,
        )
    elif input_path.is_dir():
        return folder_to_pptx(input_path, output_path=output_path, script_path=script_path)
    else:
        raise ValueError(f"Input must be a PDF file or folder of images: {input_path}")
