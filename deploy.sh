#!/bin/bash
# Deploy Montaigne API to Google Cloud Run
#
# Prerequisites:
#   - Google Cloud SDK installed (gcloud)
#   - Authenticated with: gcloud auth login
#   - Project set: gcloud config set project YOUR_PROJECT_ID
#   - GEMINI_API_KEY environment variable set
#
# Usage:
#   ./deploy.sh
#   GCP_PROJECT_ID=my-project GCP_REGION=us-east1 ./deploy.sh

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="montaigne-api"
BUCKET_NAME="montaigne-${PROJECT_ID}"

# Validate configuration
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No project ID configured."
    echo "Set GCP_PROJECT_ID or run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY environment variable not set."
    echo "Export your Gemini API key: export GEMINI_API_KEY=your-api-key"
    exit 1
fi

echo "=== Montaigne API Deployment ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Bucket: $BUCKET_NAME"
echo ""

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com \
    --quiet

# Create storage bucket if it doesn't exist
echo "Setting up Cloud Storage bucket..."
if ! gsutil ls -b "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "Creating bucket: gs://${BUCKET_NAME}"
    gsutil mb -l "$REGION" "gs://${BUCKET_NAME}"
else
    echo "Bucket already exists: gs://${BUCKET_NAME}"
fi

# Set lifecycle policy to auto-delete old jobs
echo "Setting lifecycle policy (auto-delete after 7 days)..."
cat > /tmp/lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 7,
          "matchesPrefix": ["jobs/"]
        }
      }
    ]
  }
}
EOF
gsutil lifecycle set /tmp/lifecycle.json "gs://${BUCKET_NAME}"
rm /tmp/lifecycle.json

# Set CORS for signed URL uploads
echo "Setting CORS policy..."
cat > /tmp/cors.json << 'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "PUT", "POST", "DELETE"],
    "responseHeader": ["Content-Type", "Content-Length"],
    "maxAgeSeconds": 3600
  }
]
EOF
gsutil cors set /tmp/cors.json "gs://${BUCKET_NAME}"
rm /tmp/cors.json

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
echo "This may take a few minutes for the first deployment."
echo ""

gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --min-instances 0 \
    --max-instances 5 \
    --concurrency 1 \
    --set-env-vars="GCS_BUCKET=${BUCKET_NAME},GEMINI_API_KEY=${GEMINI_API_KEY},GCP_PROJECT_ID=${PROJECT_ID}"

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "To use with the CLI:"
echo "  export MONTAIGNE_API_URL=$SERVICE_URL"
echo "  essai cloud health"
echo "  essai cloud video --pdf presentation.pdf"
echo ""
echo "Or update DEFAULT_API_URL in montaigne/cloud_config.py"
