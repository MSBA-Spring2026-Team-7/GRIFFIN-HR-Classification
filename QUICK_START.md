# GRIFFIN Quick Start

## Prerequisites
- Windows 10/11
- Conda (Miniconda or Anaconda) installed
- Google Gemini API key (free at https://aistudio.google.com/app/apikey)

## One-Click Setup
1. Open a terminal in this project folder
2. Run: `setup_and_run.bat`
3. The script will create the environment, install packages, and launch the app
4. Add your API key when prompted (or edit `.env` manually)

## Manual Setup (if the script doesn't work)
```
conda env create -f environment.yml
conda activate griffin
pip install google-generativeai python-dotenv
cp .env.example .env
# Edit .env → add GOOGLE_API_KEY=your-key
streamlit run app/streamlit_app.py
```

## Usage
- **Fast Mode**: ML prediction only (instant, no API key needed)
- **Full Analysis**: ML + Gemini AI (needs API key, slower but detailed)
- Paste a position description → Click "Classify PD" → Review results

## Troubleshooting
- "ModuleNotFoundError": Run `pip install google-generativeai python-dotenv`
- "GOOGLE_API_KEY not found": Edit `.env` file with your key
- App won't start: Make sure `conda activate griffin` worked (prompt shows `(griffin)`)
