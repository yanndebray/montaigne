"""Branding utilities for adding montaigne.cc logo to slides."""

from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from .logging import get_logger

logger = get_logger(__name__)


def detect_background_color(
    image: Image.Image, position: str = "bottom_right", sample_size: int = 20
) -> Tuple[int, int, int]:
    """
    Detect the dominant background color at a specific position in the image.

    Args:
        image: PIL Image object
        position: Position to sample from ('bottom_right', 'bottom_left', 'top_right', 'top_left')
        sample_size: Size of the square area to sample (in pixels)

    Returns:
        Tuple of (R, G, B) representing the dominant color
    """
    width, height = image.size

    # Determine sampling region based on position
    if position == "bottom_right":
        left = width - sample_size
        top = height - sample_size
        right = width
        bottom = height
    elif position == "bottom_left":
        left = 0
        top = height - sample_size
        right = sample_size
        bottom = height
    elif position == "top_right":
        left = width - sample_size
        top = 0
        right = width
        bottom = sample_size
    elif position == "top_left":
        left = 0
        top = 0
        right = sample_size
        bottom = sample_size
    else:
        raise ValueError(f"Invalid position: {position}")

    # Ensure we're within bounds
    left = max(0, left)
    top = max(0, top)
    right = min(width, right)
    bottom = min(height, bottom)

    # Crop to the sampling region
    region = image.crop((left, top, right, bottom))

    # Convert to RGB if not already
    if region.mode != "RGB":
        region = region.convert("RGB")

    # Get all pixels and calculate average color
    pixels = list(region.getdata())
    if not pixels:
        return (255, 255, 255)  # Default to white if no pixels

    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)

    return (int(avg_r), int(avg_g), int(avg_b))


def is_dark_color(color: Tuple[int, int, int]) -> bool:
    """
    Determine if a color is dark or light based on luminance.

    Args:
        color: RGB tuple

    Returns:
        True if the color is dark, False if light
    """
    # Calculate relative luminance (ITU-R BT.709)
    r, g, b = color
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance < 128


def add_branding_overlay(
    image_path: Path,
    output_path: Optional[Path] = None,
    logo_path: Optional[Path] = None,
    position: str = "bottom_right",
    padding: int = 20,
    rectangle_padding: int = 10,
    rectangle_opacity: int = 180,
    text: str = "montaigne.cc",
    font_size: int = 24,
) -> Path:
    """
    Add montaigne.cc branding to an image.

    This function:
    1. Detects the background color at the specified position
    2. Overlays a semi-transparent rectangle
    3. Adds the montaigne.cc logo or text

    Args:
        image_path: Path to the source image
        output_path: Path for the output image (default: overwrite source)
        logo_path: Path to logo image file (if None, uses text)
        position: Where to place the logo ('bottom_right', 'bottom_left', etc.)
        padding: Pixels from edge to logo position
        rectangle_padding: Pixels of padding inside the rectangle around logo
        rectangle_opacity: Opacity of the background rectangle (0-255)
        text: Text to display if no logo_path provided
        font_size: Font size for text branding

    Returns:
        Path to the output image
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if output_path is None:
        output_path = image_path

    output_path = Path(output_path)

    # Open image
    img = Image.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    width, height = img.size

    # Detect background color
    bg_color = detect_background_color(img, position=position, sample_size=40)
    is_dark = is_dark_color(bg_color)

    # Choose text/logo color based on background
    text_color = (255, 255, 255) if is_dark else (0, 0, 0)
    # For rectangle, use a slightly adjusted background color
    rect_color = tuple(min(255, c + 30) if is_dark else max(0, c - 30) for c in bg_color)

    # Create overlay layer for transparency effects
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Load or create logo/text
    if logo_path and Path(logo_path).exists():
        logo_img = Image.open(logo_path)
        if logo_img.mode != "RGBA":
            logo_img = logo_img.convert("RGBA")

        # Scale logo to appropriate size
        max_logo_width = width // 8
        max_logo_height = height // 12
        logo_img.thumbnail((max_logo_width, max_logo_height), Image.Resampling.LANCZOS)

        logo_width, logo_height = logo_img.size
    else:
        # Use text instead of logo
        try:
            # Try to use a nice font
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
            )
        except Exception:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except Exception:
                # Fallback to default font
                font = ImageFont.load_default()

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        logo_width = bbox[2] - bbox[0]
        logo_height = bbox[3] - bbox[1]
        logo_img = None

    # Calculate rectangle dimensions
    rect_width = logo_width + 2 * rectangle_padding
    rect_height = logo_height + 2 * rectangle_padding

    # Calculate position based on location
    if position == "bottom_right":
        rect_x = width - rect_width - padding
        rect_y = height - rect_height - padding
    elif position == "bottom_left":
        rect_x = padding
        rect_y = height - rect_height - padding
    elif position == "top_right":
        rect_x = width - rect_width - padding
        rect_y = padding
    elif position == "top_left":
        rect_x = padding
        rect_y = padding
    else:
        raise ValueError(f"Invalid position: {position}")

    # Draw semi-transparent rectangle
    draw.rectangle(
        [(rect_x, rect_y), (rect_x + rect_width, rect_y + rect_height)],
        fill=rect_color + (rectangle_opacity,),
    )

    # Add logo or text
    logo_x = rect_x + rectangle_padding
    logo_y = rect_y + rectangle_padding

    if logo_img:
        # Paste logo image
        overlay.paste(logo_img, (logo_x, logo_y), logo_img)
    else:
        # Draw text
        draw.text((logo_x, logo_y), text, fill=text_color + (255,), font=font)

    # Composite overlay onto original image
    img = Image.alpha_composite(img, overlay)

    # Convert back to RGB for saving
    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        img = img.convert("RGB")

    # Save
    img.save(output_path)
    logger.debug("Added branding to: %s", output_path.name)

    return output_path


def add_branding_to_images(
    input_path: Path,
    output_dir: Optional[Path] = None,
    logo_path: Optional[Path] = None,
    position: str = "bottom_right",
    in_place: bool = False,
) -> list[Path]:
    """
    Add branding to multiple images from a directory or single file.

    Args:
        input_path: Single image file or directory containing images
        output_dir: Directory for output (default: {input}_branded/)
        logo_path: Path to logo image (if None, uses text)
        position: Where to place the logo
        in_place: If True, modify images in place; if False, create copies

    Returns:
        List of paths to processed images
    """
    input_path = Path(input_path)

    # Determine input images
    image_extensions = {".jpeg", ".jpg", ".png", ".gif", ".webp", ".bmp"}
    if input_path.is_file():
        images = [input_path]
        if output_dir is None and not in_place:
            output_dir = input_path.parent / "images_branded"
    elif input_path.is_dir():
        images = sorted([f for f in input_path.iterdir() if f.suffix.lower() in image_extensions])
        if output_dir is None and not in_place:
            output_dir = input_path.parent / f"{input_path.name}_branded"
    else:
        raise FileNotFoundError(f"Input not found: {input_path}")

    if not images:
        raise ValueError(f"No images found in {input_path}")

    # Create output directory if needed
    if not in_place:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Adding branding to %d image(s)...", len(images))

    processed_images = []
    for image_path in images:
        if in_place:
            output_path = image_path
        else:
            output_path = output_dir / image_path.name

        try:
            result = add_branding_overlay(
                image_path, output_path=output_path, logo_path=logo_path, position=position
            )
            processed_images.append(result)
            logger.info("  Processed: %s", image_path.name)
        except Exception as e:
            logger.error("  Error processing %s: %s", image_path.name, e)

    logger.info("Added branding to %d/%d images", len(processed_images), len(images))
    return processed_images
