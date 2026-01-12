"""Image translation using Gemini AI."""

import base64
import mimetypes
import sys
from pathlib import Path
from typing import List, Optional, Union

from .config import get_gemini_client

IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".gif", ".webp"}
IMAGE_MODEL = "gemini-3-pro-image-preview"


def _save_image(file_path: Path, data: Union[str, bytes]):
    """Save image data, handling base64 encoding if necessary."""
    if isinstance(data, str):
        data = base64.b64decode(data)
    elif isinstance(data, bytes):
        # Check if bytes look like base64-encoded data
        try:
            if data[:4] in (b"/9j/", b"iVBO", b"R0lG", b"UklG"):
                data = base64.b64decode(data)
        except Exception:
            pass

    with open(file_path, "wb") as f:
        f.write(data)


def translate_image(
    image_path: Path, output_path: Optional[Path] = None, target_lang: str = "French", client=None
) -> Path:
    """
    Translate text in an image to target language using Gemini.

    Args:
        image_path: Path to source image
        output_path: Path for translated image (default: {stem}_{lang_code}.{ext})
        target_lang: Target language (default: French)
        client: Optional pre-configured Gemini client

    Returns:
        Path to translated image
    """
    from google.genai import types

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if client is None:
        client = get_gemini_client()

    # Determine output path
    if output_path is None:
        lang_code = target_lang[:2].lower()
        output_path = image_path.parent / f"{image_path.stem}_{lang_code}{image_path.suffix}"

    output_path = Path(output_path)

    # Read source image
    with open(image_path, "rb") as f:
        image_data = f.read()

    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/png"

    # Build prompt
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

    # Generate translated image
    for chunk in client.models.generate_content_stream(
        model=IMAGE_MODEL,
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
            # Determine output format from response
            resp_ext = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
            if output_path.suffix != resp_ext:
                output_path = output_path.with_suffix(resp_ext)

            _save_image(output_path, part.inline_data.data)
            return output_path

    raise RuntimeError("No image data received from API")


def translate_images(
    input_path: Path, output_dir: Optional[Path] = None, target_lang: str = "French"
) -> List[Path]:
    """
    Translate images from input path (file or directory).

    Args:
        input_path: Single image file or directory containing images
        output_dir: Directory for output (default: {input}_translated/)
        target_lang: Target language

    Returns:
        List of paths to translated images
    """
    input_path = Path(input_path)

    # Determine input images
    if input_path.is_file():
        images = [input_path]
        if output_dir is None:
            output_dir = input_path.parent / "images_translated"
    elif input_path.is_dir():
        images = sorted([f for f in input_path.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS])
        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.name}_translated"
    else:
        raise FileNotFoundError(f"Input not found: {input_path}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nFound {len(images)} image(s) to translate")

    client = get_gemini_client()
    lang_code = target_lang[:2].lower()
    translated_images = []

    # Use tqdm for progress bar if available in TTY environment
    try:
        from tqdm import tqdm

        use_tqdm = sys.stderr.isatty()
    except ImportError:
        use_tqdm = False

    image_iterator = images
    if use_tqdm:
        image_iterator = tqdm(images, desc="Translating images", unit="image")

    for image_path in image_iterator:
        if not use_tqdm:
            print(f"  Translating: {image_path.name}...")

        try:
            output_path = output_dir / f"{image_path.stem}_{lang_code}{image_path.suffix}"
            result = translate_image(image_path, output_path, target_lang, client=client)
            translated_images.append(result)
            if not use_tqdm:
                print(f"    Saved: {result.name}")
        except Exception as e:
            if not use_tqdm:
                print(f"    Error: {e}")

    print(f"\nTranslated {len(translated_images)} images to {output_dir}/")
    return translated_images
