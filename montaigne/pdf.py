"""PDF to images extraction using PyMuPDF."""

import sys
from pathlib import Path
from typing import List, Optional

from .logging import get_logger

logger = get_logger(__name__)


def extract_pdf_pages(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    dpi: int = 150,
    image_format: str = "png",
    add_branding: bool = False,
    logo_path: Optional[Path] = None,
) -> List[Path]:
    """
    Extract all pages from a PDF as individual images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory for output images (default: {pdf_stem}_images/)
        dpi: Resolution for extracted images (default: 150)
        image_format: Output format - 'png' or 'jpg' (default: png)
        add_branding: If True, add montaigne.cc logo to bottom right (default: False)
        logo_path: Optional path to logo image (if None, uses text)

    Returns:
        List of paths to extracted image files
    """
    import fitz  # PyMuPDF

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_dir is None:
        output_dir = pdf_path.parent / f"{pdf_path.stem}_images"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Extracting pages from: %s", pdf_path.name)

    doc = fitz.open(pdf_path)
    extracted_images = []

    # Calculate zoom factor from DPI (72 is PDF default)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    # Use tqdm for progress bar if available in TTY environment
    try:
        from tqdm import tqdm

        use_tqdm = sys.stderr.isatty()
    except ImportError:
        use_tqdm = False

    page_iterator = range(len(doc))
    if use_tqdm:
        page_iterator = tqdm(page_iterator, desc="Extracting pages", unit="page")

    for page_num in page_iterator:
        page = doc[page_num]

        # Render page to pixmap
        pix = page.get_pixmap(matrix=matrix)

        # Determine output format
        if image_format.lower() == "jpg":
            ext = ".jpg"
            output_path = output_dir / f"page_{page_num + 1:03d}{ext}"
            pix.save(output_path, jpg_quality=95)
        else:
            ext = ".png"
            output_path = output_dir / f"page_{page_num + 1:03d}{ext}"
            pix.save(output_path)

        extracted_images.append(output_path)
        if not use_tqdm:
            logger.info("  Extracted: page_%03d%s", page_num + 1, ext)

    doc.close()

    # Add branding if requested
    if add_branding:
        from .branding import add_branding_overlay

        logger.info("Adding branding to extracted images...")
        for img_path in extracted_images:
            try:
                add_branding_overlay(img_path, output_path=img_path, logo_path=logo_path)
            except Exception as e:
                logger.warning("  Failed to add branding to %s: %s", img_path.name, e)

    logger.info("Extracted %d pages to %s/", len(extracted_images), output_dir)
    return extracted_images


def get_pdf_info(pdf_path: Path) -> dict:
    """
    Get information about a PDF file.

    Returns:
        Dict with page_count, title, author, etc.
    """
    import fitz

    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    info = {
        "page_count": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
        "creator": doc.metadata.get("creator", ""),
    }

    # Get first page dimensions
    if len(doc) > 0:
        page = doc[0]
        rect = page.rect
        info["width"] = rect.width
        info["height"] = rect.height

    doc.close()
    return info
