#!/usr/bin/env bash
# ==============================================================================
# Smart Chef & Pantry Concierge — One-Click Google Cloud Setup & Deployment
# ==============================================================================
set -euo pipefail

echo "🧑‍🍳 ==========================================================="
echo "   Smart Chef & Pantry Concierge: GCP Reproduce & Deploy Script"
echo "==========================================================="

# 1. Verify gcloud authentication & active project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
if [ -z "${PROJECT_ID}" ] || [ "${PROJECT_ID}" = "(unset)" ]; then
  echo "❌ Error: No Google Cloud project configured."
  echo "   Please run:"
  echo "     gcloud auth login"
  echo "     gcloud config set project <YOUR_PROJECT_ID>"
  exit 1
fi

echo "✅ Active Project ID: ${PROJECT_ID}"
REGION="${GOOGLE_CLOUD_REGION:-us-east1}"
BUCKET_NAME="smart-chef-pantry-${PROJECT_ID}"

# 2. Enable Required APIs
echo ""
echo "📦 Step 1: Enabling Required Google Cloud APIs..."
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="${PROJECT_ID}"

# 3. Create Public Storage Bucket for Dish Photos
echo ""
echo "🪣 Step 2: Setting up Cloud Storage Bucket for dish photos..."
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
  echo "   Creating bucket gs://${BUCKET_NAME} in ${REGION}..."
  gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}" --project="${PROJECT_ID}"
  echo "   Granting public read access for dish image rendering..."
  gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="allUsers" \
    --role="roles/storage.objectViewer" || true
else
  echo "   Bucket gs://${BUCKET_NAME} already exists."
fi

# 4. Set up Firestore & Seed Pantry Inventory
echo ""
echo "🥦 Step 3: Seeding Firestore Pantry Inventory..."
if ! gcloud firestore databases describe --project="${PROJECT_ID}" &>/dev/null; then
  echo "   Creating default Firestore database..."
  gcloud firestore databases create --location=nam5 --project="${PROJECT_ID}" || true
fi
export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
export IMAGE_BUCKET_NAME="${BUCKET_NAME}"
python3 scripts/seed_firestore.py || echo "⚠️ Notice: Firestore seeding skipped or requires local auth."

# 5. Deploy Reasoning Engine using agents-cli
echo ""
echo "🤖 Step 4: Deploying Agent to Vertex AI Reasoning Engine..."
agents-cli deploy --project="${PROJECT_ID}" --no-confirm-project

# 6. Extract deployed Reasoning Engine Resource ID
RE_ID=$(python3 -c 'import json; print(json.load(open("deployment_metadata.json"))["remote_agent_runtime_id"])')
echo "✅ Reasoning Engine Deployed: ${RE_ID}"

# 7. Deploy Cloud Run Frontend
echo ""
echo "🚀 Step 5: Deploying Web Frontend to Cloud Run..."
gcloud run deploy smart-chef-pantry-frontend \
  --source frontend \
  --region="${REGION}" \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=${RE_ID},AGENT_DIRECTORY=app,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},IMAGE_BUCKET_NAME=${BUCKET_NAME}" \
  --project="${PROJECT_ID}"

FRONTEND_URL=$(gcloud run services describe smart-chef-pantry-frontend --region="${REGION}" --project="${PROJECT_ID}" --format="value(status.url)")

echo ""
echo "🎉 ==========================================================="
echo "   Deployment Complete!"
echo "   Your Smart Chef & Pantry Concierge is live at:"
echo "   👉 ${FRONTEND_URL}"
echo "==========================================================="
