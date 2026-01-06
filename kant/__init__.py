"""
Kant - Media Processing Toolkit

A unified tool for processing presentations:
- Extract PDF pages to images
- Translate images using Gemini AI
- Generate audio voiceovers from scripts
"""

__version__ = "0.1.0"

from .pdf import extract_pdf_pages
from .images import translate_image, translate_images
from .audio import generate_audio, parse_voiceover_script

__all__ = [
    "extract_pdf_pages",
    "translate_image",
    "translate_images",
    "generate_audio",
    "parse_voiceover_script",
]
