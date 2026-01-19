"""Cloud configuration management for montaigne."""

import os
from functools import lru_cache

# Default Cloud Run API URL - update after deployment
DEFAULT_API_URL = "https://montaigne-api-944767079044.us-central1.run.app"


@lru_cache
def get_api_url() -> str:
    """Get cloud API URL from environment or default.

    Set MONTAIGNE_API_URL environment variable to override.
    """
    return os.environ.get("MONTAIGNE_API_URL", DEFAULT_API_URL)


@lru_cache
def get_gcs_bucket() -> str:
    """Get GCS bucket name (server-side only).

    Set GCS_BUCKET environment variable or it will be derived from GCP_PROJECT_ID.
    """
    bucket = os.environ.get("GCS_BUCKET")
    if not bucket:
        project = os.environ.get("GCP_PROJECT_ID", "")
        if project:
            bucket = f"montaigne-{project}"
        else:
            raise ValueError("GCS_BUCKET or GCP_PROJECT_ID environment variable must be set")
    return bucket


def get_gemini_api_key() -> str:
    """Get Gemini API key from environment.

    Checks GEMINI_API_KEY environment variable.
    """
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY environment variable must be set")
    return key


def is_cloud_configured() -> bool:
    """Check if cloud configuration is available.

    Returns True if we have a valid API URL configured.
    """
    url = os.environ.get("MONTAIGNE_API_URL", DEFAULT_API_URL)
    # Check if it's the placeholder URL
    return "XXXXXXXXXX" not in url


def get_cloud_region() -> str:
    """Get the GCP region for cloud resources.

    Defaults to us-central1.
    """
    return os.environ.get("GCP_REGION", "us-central1")
