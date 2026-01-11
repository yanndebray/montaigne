"""PDF to images extraction using PyMuPDF."""

from pathlib import Path
from typing import List, Optional


def extract_pdf_pages(
    pdf_path: Path, output_dir: Optional[Path] = None, dpi: int = 150, image_format: str = "png"
) -> List[Path]:
    """
    Extract all pages from a PDF as individual images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory for output images (default: {pdf_stem}_images/)
        dpi: Resolution for extracted images (default: 150)
        image_format: Output format - 'png' or 'jpg' (default: png)

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

    print(f"Extracting pages from: {pdf_path.name}")

    doc = fitz.open(pdf_path)
    extracted_images = []

    # Calculate zoom factor from DPI (72 is PDF default)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
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
        print(f"  Extracted: page_{page_num + 1:03d}{ext}")

    doc.close()

    print(f"Extracted {len(extracted_images)} pages to {output_dir}/")
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
