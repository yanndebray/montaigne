"""Configuration and environment handling."""

import os
import sys
import subprocess

REQUIRED_PACKAGES = ["elevenlabs", "google-genai", "python-dotenv", "pymupdf"]

def check_dependencies() -> bool:
    """Check if required packages are installed."""
    try:
        from dotenv import load_dotenv  # noqa: F401
        from google import genai  # noqa: F401
        from elevenlabs.client import ElevenLabs  # noqa: F401
        import fitz  # noqa: F401
        return True
    except ImportError:
        return False

def install_dependencies():
    """Install required packages."""
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", *REQUIRED_PACKAGES, "-q"])
    print("Dependencies installed successfully!")

def load_api_key(client_name: str) -> str:
    """Load the requested API key from .env file."""
    from dotenv import load_dotenv
    load_dotenv()

    if client_name == "gemini":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            print("Error: GEMINI_API_KEY not found in .env file")
            sys.exit(1)
        return key
    
    if client_name == "elevenlabs":
        key = os.environ.get("ELEVENLABS_API_KEY")
        if not key:
            print("Error: ELEVENLABS_API_KEY not found in .env file")
            sys.exit(1)
        return key

    print(f"Error: Unknown client '{client_name}' specified")
    sys.exit(1)

def get_gemini_client():
    """Get a configured Gemini client."""
    from google import genai
    api_key = load_api_key("gemini")
    return genai.Client(api_key=api_key)

def get_elevenlabs_client():
    """Get a configured ElevenLabs client."""
    from elevenlabs.client import ElevenLabs
    api_key = load_api_key("elevenlabs")
    return ElevenLabs(api_key=api_key)