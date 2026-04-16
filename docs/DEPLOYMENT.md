# GRIFFIN — Streamlit Community Cloud Deployment Runbook

## Overview
The GRIFFIN HR Classification app is deployed on Streamlit Community Cloud
from the `main` branch of `MSBA-Spring2026-Team-7/GRIFFIN-HR-Classification`.

## Live URL
https://griffin-hr-classifier.streamlit.app

## Architecture
- **Source:** GitHub `MSBA-Spring2026-Team-7/GRIFFIN-HR-Classification` (public)
- **Branch:** `main`
- **Entry point:** `app/streamlit_app.py`
- **Python version:** 3.11
- **Build sources:** `requirements.txt` (pip, repo root) + `packages.txt` (apt, repo root)

The app uses a sibling-module import pattern (`feature_extraction`,
`ml_classifier`) inside the `app/` directory, so the Streamlit Cloud entry
point must be `app/streamlit_app.py` — not a root-level shim.

## First-time deployment
1. Go to https://share.streamlit.io/
2. Click "New app"
3. Connect the GitHub account that has access to
   `MSBA-Spring2026-Team-7/GRIFFIN-HR-Classification`
4. Select:
   - Repository: `MSBA-Spring2026-Team-7/GRIFFIN-HR-Classification`
   - Branch: `main`
   - Main file path: `app/streamlit_app.py`
   - App URL: choose a slug (e.g. `griffin-hr-classification`)
5. Click "Advanced settings" before first deploy:
   - Python version: 3.11
   - Secrets: paste the TOML block from the "Secrets" section below
6. Click "Deploy". First build takes 5-10 minutes because H2O and
   scikit-learn are heavy wheels.
7. Once the build completes, verify the app loads past the splash screen
   and that the "ML Reference Model" sidebar section is visible.

## Secrets
API keys live in Streamlit Cloud's Secrets vault, NOT in the repo. Format:
```toml
GEMINI_API_KEY = "AIzaSy..."
```
The app also accepts `GOOGLE_API_KEY` as a legacy fallback but new deployments
should use `GEMINI_API_KEY`.

To update secrets:
1. Go to https://share.streamlit.io/
2. Open the GRIFFIN app dashboard
3. Click Settings -> Secrets
4. Edit the TOML and save
5. App restarts automatically (takes ~1 minute)

## Rotating the Gemini API key
1. Go to https://aistudio.google.com/app/apikey
2. Revoke the current key
3. Generate a new key
4. Update `GEMINI_API_KEY` in Streamlit Cloud Secrets (see above)
5. Delete the old value from any local `.env` files
6. Notify the team so anyone running locally pulls the new key

## Local dev vs Cloud
- **Local:** reads `GEMINI_API_KEY` / `GOOGLE_API_KEY` from `.env` via
  `python-dotenv`.
- **Cloud:** reads `GEMINI_API_KEY` from `st.secrets`.
- Same code path; the resolver is `_load_gemini_api_key()` in
  `app/streamlit_app.py`.

To run locally:
```bash
conda activate griffin
cd HR_Classification_Project
streamlit run app/streamlit_app.py
```

## Redeployment
Push to `main` triggers automatic redeploy via Streamlit Cloud webhook. Build
takes 5-10 min on first push, 2-5 min on subsequent pushes (pip cache warm).

## Memory considerations
Free tier is 1 GB RAM. H2O ML reference model is lazy-loaded behind a sidebar
button (`Load ML reference model`) to stay under the cap. The sklearn fallback
classifier is always available and runs automatically during classification;
H2O is only needed if the user explicitly opts in to see the H2O AutoML
reference prediction used during training.

Do not call `h2o.init()` at app import time — it will OOM the free tier.

## API Key Monitoring (Important for Ongoing Use)

The Gemini API key stored in Streamlit Cloud Secrets has no automated monitoring.
If the key expires, is revoked, or hits its quota, Full Analysis mode will fail
with a generic error. Fast Mode (ML-only) continues to work regardless.

**Recommended monitoring for production use:**
- Check the Streamlit Cloud logs weekly for Gemini API errors
- Set a calendar reminder to verify the API key before each semester/fiscal year
- Consider adding a health-check banner to the app that tests the API on startup
  and displays "AI classification temporarily unavailable — using ML-only mode"
  rather than failing silently (see Future Development Taskers in the Technical
  Transition Guide)
- Rotate the key at https://aistudio.google.com/app/apikey if compromised

**To update the key:** Streamlit Cloud dashboard → App settings → Secrets → edit
`GEMINI_API_KEY` value → save. The app restarts automatically.

## Owner
Steven Alvarado (Team 7 lead). For access questions, contact via GitHub
@Steven-Alvarado7.
