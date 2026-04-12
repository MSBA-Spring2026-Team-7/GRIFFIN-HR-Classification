# GRIFFIN Quick Start

---

## How to Run the App (3 commands)

Open any terminal (PowerShell, Anaconda Prompt, or VS Code terminal):

```
conda activate griffin
cd "C:\Users\salva\Desktop\MSBA\Claude Skills\Courses\AI Course\HR_Classification_Project"
streamlit run app/streamlit_app.py
```

The app opens automatically in your browser at http://localhost:8501

To stop the app: press **Ctrl+C** in the terminal.

---

## Prerequisites (first time only)
- Windows 10/11
- Conda (Miniconda or Anaconda) installed
- Google Gemini API key (free at https://aistudio.google.com/app/apikey)

## First-Time Setup

### Option A: One-Click
1. Open a terminal in this project folder
2. Run: `setup_and_run.bat`
3. The script creates the environment, installs packages, and launches the app
4. Add your API key when prompted

### Option B: Manual
```
conda env create -f environment.yml
conda activate griffin
pip install google-generativeai python-dotenv
copy .env.example .env
```
Then edit `.env` and add your Google API key: `GOOGLE_API_KEY=your-actual-key-here`

Then run:
```
streamlit run app/streamlit_app.py
```

## Usage
- **Fast Mode**: ML prediction only — instant results, no API key needed
- **Full Analysis**: ML + Gemini AI — needs API key, slower but gives 3 ranked matches with AI rationale
- Paste a position description, choose your mode, click "Classify PD", review results

## Troubleshooting
- **"ModuleNotFoundError"**: Run `pip install google-generativeai python-dotenv`
- **"GOOGLE_API_KEY not found"**: Edit `.env` file and add your key (or switch to Fast Mode — no key needed)
- **App won't start**: Make sure `conda activate griffin` worked — your prompt should show `(griffin)`
- **H2O is slow on first run**: Normal — the Java runtime boots once, then subsequent classifications are fast
