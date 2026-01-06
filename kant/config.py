"""Configuration and environment handling."""

import os
import sys
import subprocess
from pathlib import Path

REQUIRED_PACKAGES = ["google-genai", "python-dotenv", "pymupdf"]


def check_dependencies() -> bool:
    """Check if required packages are installed."""
    try:
        from dotenv import load_dotenv
        from google import genai
        import fitz  # PyMuPDF
        return True
    except ImportError:
        return False


def install_dependencies():
    """Install required packages."""
    print("Installing dependencies...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        *REQUIRED_PACKAGES, "-q"
    ])
    print("Dependencies installed successfully!")


def load_api_key() -> str:
    """Load the Gemini API key from .env file."""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file")
        print("Please create a .env file with: GEMINI_API_KEY=your-api-key")
        sys.exit(1)
    return api_key


def get_gemini_client():
    """Get a configured Gemini client."""
    from google import genai
    api_key = load_api_key()
    return genai.Client(api_key=api_key)
