"""FastAPI application for montaigne cloud video generation."""

import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import __version__
from .video import check_ffmpeg


# Pydantic models for API requests/responses


class UploadUrlRequest(BaseModel):
    """Request for generating a signed upload URL."""

    filename: str = Field(..., description="Name of the file to upload")
    content_type: str = Field(default="application/pdf", description="MIME type")
    size_bytes: Optional[int] = Field(default=None, description="File size in bytes")


class UploadUrlResponse(BaseModel):
    """Response with signed upload URL."""

    job_id: str
    upload_url: str
    gcs_path: str
    expires: str


class StartJobRequest(BaseModel):
    """Request to start processing a job."""

    pipeline: str = Field(default="video", description="Pipeline: video, localize, script, audio")
    resolution: str = Field(default="1920:1080", description="Video resolution")
    voice: str = Field(default="Orus", description="TTS voice")
    context: str = Field(default="", description="Additional context for script generation")
    lang: Optional[str] = Field(default=None, description="Target language for localization")


class JobStatusResponse(BaseModel):
    """Response with job status."""

    job_id: str
    status: str
    pipeline: Optional[str] = None
    progress: Optional[dict] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: Optional[dict] = None
    error: Optional[dict] = None


class DownloadResponse(BaseModel):
    """Response with signed download URL."""

    download_url: str
    filename: str
    size_bytes: int
    expires: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    ffmpeg: bool


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting montaigne API v{__version__}")
    yield
    # Shutdown
    print("Shutting down montaigne API")


# Create FastAPI app
app = FastAPI(
    title="Montaigne Cloud API",
    description="Cloud API for video generation from presentations",
    version=__version__,
    lifespan=lifespan,
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check API health and dependencies."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        ffmpeg=check_ffmpeg(),
    )


# Upload URL endpoint
@app.post("/jobs/upload-url", response_model=UploadUrlResponse, tags=["Jobs"])
async def get_upload_url(request: UploadUrlRequest):
    """Get a signed URL for uploading a file.

    Use this to upload your PDF before starting a job.
    """
    from .cloud_storage import generate_job_id, generate_signed_upload_url, create_job

    job_id = generate_job_id()

    # Create the job first
    create_job(job_id=job_id, pipeline="video")

    # Generate signed upload URL
    upload_info = generate_signed_upload_url(
        job_id=job_id,
        filename=request.filename,
        folder="input",
        content_type=request.content_type,
    )

    return UploadUrlResponse(
        job_id=job_id,
        upload_url=upload_info["upload_url"],
        gcs_path=upload_info["gcs_path"],
        expires=upload_info["expires"],
    )


# Start job endpoint
@app.post("/jobs/{job_id}/start", response_model=JobStatusResponse, tags=["Jobs"])
async def start_job(job_id: str, request: StartJobRequest, background_tasks: BackgroundTasks):
    """Start processing a job.

    The job must have a PDF uploaded before calling this.
    Processing happens in the background.
    """
    from .cloud_storage import get_job_status, update_job_status, list_job_files

    # Check if job exists
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Check if already processing
    if status.get("status") == "processing":
        raise HTTPException(status_code=400, detail="Job is already processing")

    # Check if PDF was uploaded
    input_files = list_job_files(job_id, "input")
    pdf_files = [f for f in input_files if f["name"].endswith(".pdf")]
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF file uploaded. Upload a PDF first.")

    # Update status to processing
    updated = update_job_status(
        job_id=job_id,
        status="processing",
        step="pdf",
        message="Starting video generation pipeline",
    )
    updated["pipeline"] = request.pipeline

    # Start background processing
    background_tasks.add_task(
        process_video_job,
        job_id=job_id,
        pdf_filename=pdf_files[0]["name"],
        resolution=request.resolution,
        voice=request.voice,
        context=request.context,
    )

    return JobStatusResponse(**updated)


# Job status endpoint
@app.get("/jobs/{job_id}/status", response_model=JobStatusResponse, tags=["Jobs"])
async def get_status(job_id: str):
    """Get the current status of a job."""
    from .cloud_storage import get_job_status

    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(**status)


# Download endpoint
@app.get("/jobs/{job_id}/download", response_model=DownloadResponse, tags=["Jobs"])
async def get_download_url(job_id: str, file: str = "video"):
    """Get a signed URL for downloading job output.

    Args:
        job_id: The job identifier
        file: File to download (video, script, images, audio)
    """
    from .cloud_storage import get_job_status, generate_signed_download_url, list_job_files

    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if status.get("status") != "completed":
        raise HTTPException(
            status_code=400, detail=f"Job is not completed. Current status: {status.get('status')}"
        )

    # Determine folder and find file
    folder_map = {
        "video": "output",
        "script": "scripts",
        "images": "images",
        "audio": "audio",
    }

    folder = folder_map.get(file, "output")
    files = list_job_files(job_id, folder)

    if not files:
        raise HTTPException(status_code=404, detail=f"No {file} files found for job")

    # Get the main file (first one, or specific patterns)
    if file == "video":
        target_files = [f for f in files if f["name"].endswith(".mp4")]
    elif file == "script":
        target_files = [f for f in files if f["name"].endswith(".md")]
    else:
        target_files = files

    if not target_files:
        raise HTTPException(status_code=404, detail=f"No {file} files found for job")

    target_file = target_files[0]

    download_info = generate_signed_download_url(
        job_id=job_id,
        filename=target_file["name"],
        folder=folder,
    )

    return DownloadResponse(**download_info)


# List jobs endpoint
@app.get("/jobs", tags=["Jobs"])
async def list_jobs(limit: int = 20, status: Optional[str] = None):
    """List recent jobs.

    Note: This is a simplified implementation that lists jobs from storage.
    For production, consider using a database for job tracking.
    """
    from .cloud_storage import get_bucket, get_job_status

    bucket = get_bucket()
    jobs = []

    # List job prefixes (this is not efficient for large numbers of jobs)
    # In production, use a database
    seen_jobs = set()
    for blob in bucket.list_blobs(prefix="jobs/", delimiter="/"):
        pass  # Skip files at root

    # Get job IDs from prefixes
    for prefix in bucket.list_blobs(prefix="jobs/").prefixes:
        job_id = prefix.strip("/").split("/")[-1]
        if job_id and job_id not in seen_jobs:
            seen_jobs.add(job_id)
            job_status = get_job_status(job_id)
            if job_status:
                if status is None or job_status.get("status") == status:
                    jobs.append(
                        {
                            "job_id": job_id,
                            "status": job_status.get("status"),
                            "pipeline": job_status.get("pipeline"),
                            "created_at": job_status.get("created_at"),
                        }
                    )

            if len(jobs) >= limit:
                break

    return {"jobs": jobs[:limit]}


# Delete job endpoint
@app.delete("/jobs/{job_id}", tags=["Jobs"])
async def delete_job(job_id: str):
    """Delete a job and all its files."""
    from .cloud_storage import get_job_status, delete_job as gcs_delete_job

    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    deleted_count = gcs_delete_job(job_id)

    return {"job_id": job_id, "deleted_files": deleted_count}


# Background processing function
def process_video_job(
    job_id: str,
    pdf_filename: str,
    resolution: str = "1920:1080",
    voice: str = "Orus",
    context: str = "",
):
    """Process a video generation job in the background.

    This function runs the full video pipeline:
    1. Download PDF from GCS
    2. Extract PDF pages to images
    3. Generate voiceover script
    4. Generate audio
    5. Generate video
    6. Upload results to GCS
    """
    from .cloud_storage import (
        download_file,
        upload_file,
        update_job_status,
        generate_signed_download_url,
        get_bucket_name,
        get_job_path,
    )
    from .pdf import extract_pdf_pages
    from .scripts import generate_scripts
    from .audio import generate_audio
    from .video import generate_video

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Step 1: Download PDF
            update_job_status(
                job_id=job_id,
                status="processing",
                step="pdf",
                message="Downloading PDF from storage",
            )

            pdf_path = temp_path / pdf_filename
            download_file(job_id, pdf_filename, pdf_path, folder="input")

            # Step 2: Extract PDF pages
            update_job_status(
                job_id=job_id,
                status="processing",
                step="pdf",
                message="Extracting PDF pages to images",
            )

            images_dir = temp_path / "images"
            images = extract_pdf_pages(pdf_path, output_dir=images_dir)

            # Upload images to GCS
            for i, img_path in enumerate(images):
                upload_file(img_path, job_id, folder="images")
                update_job_status(
                    job_id=job_id,
                    status="processing",
                    step="pdf",
                    current=i + 1,
                    total=len(images),
                    message=f"Uploaded image {i + 1}/{len(images)}",
                )

            # Step 3: Generate script
            update_job_status(
                job_id=job_id,
                status="processing",
                step="script",
                message="Generating voiceover script with AI",
            )

            script_path = generate_scripts(pdf_path, context=context)

            # Upload script to GCS
            upload_file(script_path, job_id, folder="scripts", filename="voiceover.md")

            # Step 4: Generate audio
            update_job_status(
                job_id=job_id,
                status="processing",
                step="audio",
                current=0,
                total=len(images),
                message="Generating audio narration",
            )

            audio_dir = temp_path / "audio"

            # Custom progress callback for audio generation
            def audio_progress(current: int, total: int):
                update_job_status(
                    job_id=job_id,
                    status="processing",
                    step="audio",
                    current=current,
                    total=total,
                    message=f"Generating audio for slide {current}/{total}",
                )

            generate_audio(script_path, output_dir=audio_dir, voice=voice)

            # Upload audio files to GCS
            audio_files = sorted(audio_dir.glob("slide_*.wav"))
            for i, audio_path in enumerate(audio_files):
                upload_file(audio_path, job_id, folder="audio")
                update_job_status(
                    job_id=job_id,
                    status="processing",
                    step="audio",
                    current=i + 1,
                    total=len(audio_files),
                    message=f"Uploaded audio {i + 1}/{len(audio_files)}",
                )

            # Step 5: Generate video
            update_job_status(
                job_id=job_id,
                status="processing",
                step="video",
                message="Generating video with ffmpeg",
            )

            base_name = pdf_path.stem
            video_path = temp_path / f"{base_name}_video.mp4"

            generate_video(images_dir, audio_dir, video_path, resolution=resolution)

            # Upload video to GCS
            update_job_status(
                job_id=job_id,
                status="processing",
                step="video",
                message="Uploading video to storage",
            )

            upload_file(video_path, job_id, folder="output", filename=f"{base_name}_video.mp4")

            # Get download URL for output
            download_info = generate_signed_download_url(
                job_id=job_id,
                filename=f"{base_name}_video.mp4",
                folder="output",
            )

            # Mark as completed
            update_job_status(
                job_id=job_id,
                status="completed",
                step="video",
                message="Video generation complete",
                output={
                    "video_url": download_info["download_url"],
                    "video_size_bytes": download_info["size_bytes"],
                    "download_expires": download_info["expires"],
                },
            )

    except Exception as e:
        # Mark as failed
        update_job_status(
            job_id=job_id,
            status="failed",
            error={
                "message": str(e),
                "type": type(e).__name__,
            },
        )
        raise
