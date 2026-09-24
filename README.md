# 🧑‍🍳 Smart Chef & Pantry Concierge

An AI culinary concierge powered by **Google Agent Development Kit (ADK)**, **Gemini 2.5 Flash**, **Vertex AI Agent Runtime**, **A2UI (Agent-to-User Interface)**, **Firestore**, and **Cloud Storage**.

---

## ✨ Features

- **Pantry Inventory Tracking**: Automatically checks and manages fresh ingredients and shelf-stable staples in Google Cloud Firestore.
- **Dynamic Dish Suggestions**: Provides 3–4 tailored dish recommendations based on available pantry items, tagged with prep time, difficulty, and pantry-match scores.
- **Standardized Recipe Cards**:
  - **Completed Dish Photography**: Generates a high-definition photograph of the completed dish via Vertex AI Imagen 3 and hosts it on Cloud Storage.
  - **Portioned Ingredients**: Lists exact portioned amounts and units.
  - **Interactive Ingredient Previews**: Each ingredient line includes an interactive checkbox, ingredient thumbnail, and floating hover popover preview.
  - **Numbered Action Steps**: Clearly labeled, numbered preparation and cooking steps.
  - **Chef's Pro Tips**: Actionable culinary techniques.
- **A2UI Rich Display Components**: Natively renders cards, columns, rows, images, and checklist items in both the local development playground and custom Cloud Run web frontend.
- **Copy to Clipboard**: One-click recipe copying directly from the web chat.

---

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│     Cloud Run Web Frontend      │ (FastAPI + A2UI HTML/CSS/JS)
└────────────────┬────────────────┘
                 │ A2A Protocol (Agent-to-Agent)
                 ▼
┌─────────────────────────────────┐
│ Vertex AI Reasoning Engine      │ (ADK Agent Runtime + Gemini 2.5 Flash)
└───────┬──────────────┬──────────┘
        │              │
        ▼              ▼
┌──────────────┐ ┌───────────────────────────┐
│  Firestore   │ │ Public Cloud Storage      │
│  (Inventory) │ │ (Generated Dish Photos)   │
└──────────────┘ └───────────────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- **Python 3.11+**
- **uv**: Python package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **agents-cli**: Google Agent Development Kit CLI (`uv tool install google-agents-cli`)
- **Google Cloud SDK**: (`gcloud auth login` and `gcloud auth application-default login`)

### 2. Install Dependencies
```bash
agents-cli install
```

### 3. Launch Local Playground
```bash
agents-cli playground
```
This starts the local ADK Web interactive development UI at `http://localhost:8080/dev-ui/?app=app`.

---

## ☁️ Deploying to Your Own Google Cloud Project

You can easily reproduce and launch this entire application on your personal Google Cloud account.

### Method 1: One-Click Setup Script
Ensure you are logged into your Google Cloud account and have your target project selected:
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

Then run the automated setup script:
```bash
./setup_gcp.sh
```
This script automatically:
1. Enables required GCP APIs (`aiplatform`, `run`, `firestore`, `storage`, `artifactregistry`, `cloudbuild`).
2. Creates the public Cloud Storage bucket `gs://smart-chef-pantry-<YOUR_PROJECT_ID>` for dish photos.
3. Initializes Firestore and seeds initial pantry ingredients (`scripts/seed_firestore.py`).
4. Deploys the ADK Agent to **Vertex AI Reasoning Engine** (`agents-cli deploy`).
5. Builds and deploys the web frontend to **Cloud Run**.

---

### Method 2: Manual Step-by-Step Deployment

If you prefer running each step individually:

#### Step 1: Enable Google Cloud APIs
```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-east1"

gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project="${PROJECT_ID}"
```

#### Step 2: Create Public Storage Bucket for Dish Photos
```bash
export BUCKET_NAME="smart-chef-pantry-${PROJECT_ID}"

gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}" --project="${PROJECT_ID}"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="allUsers" \
  --role="roles/storage.objectViewer"
```

#### Step 3: Initialize Firestore & Seed Pantry Items
```bash
gcloud firestore databases create --location=nam5 --project="${PROJECT_ID}" || true
export GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"
python3 scripts/seed_firestore.py
```

#### Step 4: Deploy Agent to Vertex AI Reasoning Engine
```bash
agents-cli deploy --project="${PROJECT_ID}" --no-confirm-project
```
Note the **Agent Runtime ID** returned in the terminal (e.g., `projects/.../locations/us-east1/reasoningEngines/...`).

#### Step 5: Deploy Frontend to Cloud Run
```bash
RE_ID=$(python3 -c 'import json; print(json.load(open("deployment_metadata.json"))["remote_agent_runtime_id"])')

gcloud run deploy smart-chef-pantry-frontend \
  --source frontend \
  --region="${REGION}" \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=${RE_ID},AGENT_DIRECTORY=app,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},IMAGE_BUCKET_NAME=${BUCKET_NAME}" \
  --project="${PROJECT_ID}"
```

---

## 🛠️ Agent Skills (prerequisite)

This project was built in **Antigravity** using the Google Agents CLI skill suite
(Apache-2.0, © Google LLC) plus workshop lab skills from Google's Build with Gemini
event. Those skills are **development tooling, not runtime dependencies** — they are
installed into your own Antigravity environment rather than vendored here.

```bash
./install_skills.sh          # installs skills into ~/.gemini/antigravity/skills/
```

If you do not have the skills locally, the application still builds and deploys
normally — they assist authoring, not execution.

---

## 📂 Project Structure

```
├── app/
│   ├── agent.py               # Root ADK agent with Gemini 2.5 Flash & A2UI
│   ├── tools.py               # Custom function tools (Firestore, Imagen 3, RAG)
│   ├── a2ui_prompt.txt        # A2UI system design prompt
│   └── a2ui_utils.py          # A2UI callback transformer
├── frontend/
│   ├── main.py                # FastAPI proxy server (A2A protocol client)
│   ├── static/index.html      # Responsive chat UI with A2UI renderer & hover tooltips
│   └── Dockerfile             # Container definition for Cloud Run
├── scripts/
│   ├── seed_firestore.py      # Seeds sample pantry inventory into Firestore
│   └── setup_rag.py           # Sets up Vertex AI RAG corpus
├── install_skills.sh          # Installs Antigravity skills into your environment
├── setup_gcp.sh               # One-command GCP reproduction script
├── deployment_metadata.json   # Deployed reasoning engine metadata
└── pyproject.toml             # Python dependencies and build config
```

---

## 🙏 Built With

- **[Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/)** — agent runtime and primitives
- **Gemini 2.5 Flash** on **Vertex AI Agent Runtime** (Reasoning Engine)
- **A2A** (Agent-to-Agent) protocol for frontend ↔ agent transport
- **A2UI** for agent-rendered cards, rows, and checklists
- **Vertex AI RAG Engine** over a public-domain recipe corpus
- **Imagen 3** for generated dish photography
- **Firestore**, **Cloud Storage**, **Cloud Run**

Built during Google's *Build with Gemini* event. Google ADK and the Google Agents
CLI are © Google LLC, licensed under Apache-2.0, and are used here as dependencies.

---

## 📄 License

Copyright 2026 Kuoshih (Tony) Yang

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE) for details.
