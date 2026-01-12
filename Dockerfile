# Dockerfile for Montaigne Cloud API
# Deploys to Google Cloud Run for video generation

FROM python:3.11-slim

# Install ffmpeg and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Copy source code
COPY montaigne/ montaigne/

# Install montaigne with cloud dependencies
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir \
    fastapi[standard] \
    uvicorn[standard] \
    google-cloud-storage \
    python-multipart \
    requests

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run FastAPI with uvicorn
CMD ["uvicorn", "montaigne.cloud_api:app", "--host", "0.0.0.0", "--port", "8080"]
