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

```
conda env create -f environment-local.yml
conda activate griffin
pip install polars pyarrow
copy .env.example .env
```
Then edit `.env` and add your Gemini API key: `GEMINI_API_KEY=your-actual-key-here`

Then run:
```
streamlit run app/streamlit_app.py
```

## Usage
- **Fast Mode**: ML prediction only -- instant results, no API key needed
- **Full Analysis**: ML + LangChain agent pipeline (Gemini AI) -- needs API key, provides 3 ranked matches with AI rationale and downloadable Word report
- Paste a position description, choose your mode, click "Classify PD", review results
- Click "Download Classification Report" to save results as a Word document

## What You'll See (Full Analysis)
1. **ML Classification** -- occupational family prediction with statistical probability
2. **Best Match** -- top-ranked DHRM role with pay band and salary range
3. **Alternative Role** -- second-best role in the same career group
4. **Alternative Group** -- best role in a different career group (for triangulation)
5. **AI Rationale** -- detailed explanation of the classification reasoning

Each card shows dual confidence metrics: **ML Probability** (statistical) and **AI Assessment** (LLM judgment).

## Troubleshooting
- **"ModuleNotFoundError"**: Run `pip install langchain langgraph langchain-google-genai google-generativeai python-dotenv python-docx`
- **"GEMINI_API_KEY not found"**: Edit `.env` file and add your key (or switch to Fast Mode -- no key needed)
- **App won't start**: Make sure `conda activate griffin` worked -- your prompt should show `(griffin)`
- **H2O is slow on first run**: Normal -- the Java runtime boots in the background during page load. Subsequent classifications use the cached model.
- **Only 1 card instead of 3**: The AI agent may not have returned alternatives. Try again -- LLM responses can vary.
