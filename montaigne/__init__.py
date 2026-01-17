"""
Montaigne - Media Processing Toolkit

A unified tool for processing presentations:
- Extract PDF pages to images
- Generate voiceover scripts from slides using AI
- Translate images using Gemini AI
- Generate audio voiceovers from scripts
- Generate videos from slides and audio
"""

__version__ = "0.8.6"

from .pdf import extract_pdf_pages
from .scripts import generate_scripts, generate_slide_script
from .images import translate_image, translate_images
from .audio import generate_audio, parse_voiceover_script
from .video import generate_video, generate_video_from_pdf
from .ppt import create_pptx, pdf_to_pptx, folder_to_pptx

__all__ = [
    "extract_pdf_pages",
    "generate_scripts",
    "generate_slide_script",
    "translate_image",
    "translate_images",
    "generate_audio",
    "parse_voiceover_script",
    "generate_video",
    "generate_video_from_pdf",
    "create_pptx",
    "pdf_to_pptx",
    "folder_to_pptx",
]
