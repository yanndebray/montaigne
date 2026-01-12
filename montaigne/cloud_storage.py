"""Google Cloud Storage operations for montaigne cloud offloading."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from functools import lru_cache

# Lazy import to avoid requiring google-cloud-storage for local usage
_storage_client = None
_signing_credentials = None


def _get_storage_client():
    """Get or create the GCS storage client (lazy initialization)."""
    global _storage_client
    if _storage_client is None:
        from google.cloud import storage
        _storage_client = storage.Client()
    return _storage_client


def _get_signing_credentials():
    """Get credentials that can sign URLs (for Cloud Run environments)."""
    global _signing_credentials
    if _signing_credentials is not None:
        return _signing_credentials

    import google.auth
    from google.auth import compute_engine
    from google.auth.transport import requests

    credentials, project = google.auth.default()

    # If running on Cloud Run/Compute Engine, use IAM signing
    if isinstance(credentials, compute_engine.Credentials):
        from google.auth import iam
        from google.auth.transport import requests as auth_requests

        # Get the service account email
        request = auth_requests.Request()
        credentials.refresh(request)

        # Create signing credentials using IAM
        signer = iam.Signer(
            request,
            credentials,
            credentials.service_account_email,
        )

        _signing_credentials = compute_engine.IDTokenCredentials(
            request,
            target_audience="",
            service_account_email=credentials.service_account_email,
        )
        # Store the signer and email for later use
        _signing_credentials._signer = signer
        _signing_credentials._service_account_email = credentials.service_account_email

    return _signing_credentials


@lru_cache
def get_bucket_name() -> str:
    """Get the GCS bucket name from environment or default."""
    bucket = os.environ.get("GCS_BUCKET")
    if not bucket:
        project_id = os.environ.get("GCP_PROJECT_ID", "")
        if project_id:
            bucket = f"montaigne-{project_id}"
        else:
            raise ValueError(
                "GCS_BUCKET or GCP_PROJECT_ID environment variable must be set"
            )
    return bucket


def get_bucket():
    """Get the GCS bucket object."""
    client = _get_storage_client()
    return client.bucket(get_bucket_name())


def generate_job_id() -> str:
    """Generate a unique job ID with timestamp and random suffix."""
    import secrets
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    suffix = secrets.token_hex(4)
    return f"{timestamp}_{suffix}"


def get_job_path(job_id: str, *parts: str) -> str:
    """Get the GCS path for a job file.

    Args:
        job_id: The job identifier
        *parts: Additional path components (e.g., "input", "presentation.pdf")

    Returns:
        GCS path like "jobs/{job_id}/input/presentation.pdf"
    """
    return "/".join(["jobs", job_id] + list(parts))


def _get_signing_info() -> tuple[Optional[str], Optional[str]]:
    """Get service account email and access token for IAM-based signing.

    Returns:
        Tuple of (service_account_email, access_token) or (None, None) if not on Cloud Run.
    """
    try:
        import google.auth
        from google.auth import compute_engine

        credentials, _ = google.auth.default()
        if isinstance(credentials, compute_engine.Credentials):
            from google.auth.transport import requests as auth_requests
            request = auth_requests.Request()
            credentials.refresh(request)
            return credentials.service_account_email, credentials.token
    except Exception:
        pass
    return None, None


def generate_signed_upload_url(
    job_id: str,
    filename: str,
    folder: str = "input",
    content_type: str = "application/octet-stream",
    expiration_minutes: int = 60,
) -> dict:
    """Generate a signed URL for uploading a file to GCS.

    Args:
        job_id: The job identifier
        filename: Name of the file to upload
        folder: Subfolder within the job (input, images, audio, output)
        content_type: MIME type of the file
        expiration_minutes: How long the URL is valid

    Returns:
        Dict with upload_url, gcs_path, and expires timestamp
    """
    bucket = get_bucket()
    blob_path = get_job_path(job_id, folder, filename)
    blob = bucket.blob(blob_path)

    expiration = timedelta(minutes=expiration_minutes)

    # Get service account email and token for IAM-based signing (Cloud Run)
    sa_email, access_token = _get_signing_info()

    sign_kwargs = {
        "version": "v4",
        "expiration": expiration,
        "method": "PUT",
        "content_type": content_type,
    }

    # Use IAM signing for Cloud Run (no private key available)
    if sa_email and access_token:
        sign_kwargs["service_account_email"] = sa_email
        sign_kwargs["access_token"] = access_token

    url = blob.generate_signed_url(**sign_kwargs)

    expires = datetime.now(timezone.utc) + expiration

    return {
        "upload_url": url,
        "gcs_path": f"gs://{get_bucket_name()}/{blob_path}",
        "expires": expires.isoformat(),
    }


def generate_signed_download_url(
    job_id: str,
    filename: str,
    folder: str = "output",
    expiration_hours: int = 24,
) -> dict:
    """Generate a signed URL for downloading a file from GCS.

    Args:
        job_id: The job identifier
        filename: Name of the file to download
        folder: Subfolder within the job
        expiration_hours: How long the URL is valid

    Returns:
        Dict with download_url, filename, size_bytes, and expires timestamp
    """
    bucket = get_bucket()
    blob_path = get_job_path(job_id, folder, filename)
    blob = bucket.blob(blob_path)

    # Reload blob to get metadata
    blob.reload()

    expiration = timedelta(hours=expiration_hours)

    # Get service account email and token for IAM-based signing (Cloud Run)
    sa_email, access_token = _get_signing_info()

    sign_kwargs = {
        "version": "v4",
        "expiration": expiration,
        "method": "GET",
    }

    # Use IAM signing for Cloud Run (no private key available)
    if sa_email and access_token:
        sign_kwargs["service_account_email"] = sa_email
        sign_kwargs["access_token"] = access_token

    url = blob.generate_signed_url(**sign_kwargs)

    expires = datetime.now(timezone.utc) + expiration

    return {
        "download_url": url,
        "filename": filename,
        "size_bytes": blob.size,
        "expires": expires.isoformat(),
    }


def upload_file(
    local_path: Path,
    job_id: str,
    folder: str = "input",
    filename: Optional[str] = None,
) -> str:
    """Upload a local file to GCS.

    Args:
        local_path: Path to the local file
        job_id: The job identifier
        folder: Subfolder within the job
        filename: Override filename (defaults to local file name)

    Returns:
        GCS URI (gs://bucket/path)
    """
    bucket = get_bucket()
    filename = filename or local_path.name
    blob_path = get_job_path(job_id, folder, filename)
    blob = bucket.blob(blob_path)

    blob.upload_from_filename(str(local_path))

    return f"gs://{get_bucket_name()}/{blob_path}"


def download_file(
    job_id: str,
    filename: str,
    local_path: Path,
    folder: str = "output",
) -> Path:
    """Download a file from GCS to local path.

    Args:
        job_id: The job identifier
        filename: Name of the file in GCS
        local_path: Local path to save the file
        folder: Subfolder within the job

    Returns:
        Path to the downloaded file
    """
    bucket = get_bucket()
    blob_path = get_job_path(job_id, folder, filename)
    blob = bucket.blob(blob_path)

    local_path.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local_path))

    return local_path


def list_job_files(job_id: str, folder: Optional[str] = None) -> list[dict]:
    """List files in a job directory.

    Args:
        job_id: The job identifier
        folder: Optional subfolder to list

    Returns:
        List of dicts with name, size, and updated timestamp
    """
    bucket = get_bucket()
    prefix = get_job_path(job_id, folder) if folder else get_job_path(job_id)

    files = []
    for blob in bucket.list_blobs(prefix=prefix + "/"):
        files.append({
            "name": blob.name.split("/")[-1],
            "path": blob.name,
            "size_bytes": blob.size,
            "updated": blob.updated.isoformat() if blob.updated else None,
        })

    return files


def delete_job(job_id: str) -> int:
    """Delete all files for a job.

    Args:
        job_id: The job identifier

    Returns:
        Number of files deleted
    """
    bucket = get_bucket()
    prefix = get_job_path(job_id)

    blobs = list(bucket.list_blobs(prefix=prefix + "/"))
    for blob in blobs:
        blob.delete()

    return len(blobs)


# Job status management

def get_job_status(job_id: str) -> Optional[dict]:
    """Get the status of a job from status.json.

    Args:
        job_id: The job identifier

    Returns:
        Status dict or None if not found
    """
    bucket = get_bucket()
    blob_path = get_job_path(job_id, "status.json")
    blob = bucket.blob(blob_path)

    try:
        content = blob.download_as_text()
        return json.loads(content)
    except Exception:
        return None


def update_job_status(
    job_id: str,
    status: str,
    step: Optional[str] = None,
    current: Optional[int] = None,
    total: Optional[int] = None,
    message: Optional[str] = None,
    error: Optional[dict] = None,
    output: Optional[dict] = None,
) -> dict:
    """Update the status of a job.

    Args:
        job_id: The job identifier
        status: Job status (pending, processing, completed, failed)
        step: Current processing step (pdf, script, audio, video)
        current: Current progress within step
        total: Total items in step
        message: Human-readable progress message
        error: Error information if failed
        output: Output information if completed

    Returns:
        Updated status dict
    """
    bucket = get_bucket()
    blob_path = get_job_path(job_id, "status.json")
    blob = bucket.blob(blob_path)

    # Try to load existing status
    try:
        existing = json.loads(blob.download_as_text())
    except Exception:
        existing = {
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Update fields
    now = datetime.now(timezone.utc).isoformat()
    existing["status"] = status
    existing["updated_at"] = now

    if status == "processing" and "started_at" not in existing:
        existing["started_at"] = now

    if status == "completed":
        existing["completed_at"] = now

    if step or current is not None or total is not None or message:
        existing["progress"] = {
            "step": step or existing.get("progress", {}).get("step"),
            "current": current if current is not None else existing.get("progress", {}).get("current"),
            "total": total if total is not None else existing.get("progress", {}).get("total"),
            "message": message or existing.get("progress", {}).get("message"),
        }

    if error:
        existing["error"] = error

    if output:
        existing["output"] = output

    # Save updated status
    blob.upload_from_string(
        json.dumps(existing, indent=2),
        content_type="application/json",
    )

    return existing


def create_job(job_id: Optional[str] = None, pipeline: str = "video") -> dict:
    """Create a new job with initial status.

    Args:
        job_id: Optional job ID (generated if not provided)
        pipeline: Pipeline type (video, localize, script, audio)

    Returns:
        Initial status dict with job_id
    """
    if job_id is None:
        job_id = generate_job_id()

    status = update_job_status(
        job_id=job_id,
        status="pending",
        message=f"Job created for {pipeline} pipeline",
    )
    status["pipeline"] = pipeline

    # Re-save with pipeline
    bucket = get_bucket()
    blob_path = get_job_path(job_id, "status.json")
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        json.dumps(status, indent=2),
        content_type="application/json",
    )

    return status
