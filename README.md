# GRIFFIN -- W&M HR Position Classification & Pay Matching

GRIFFIN is an AI-powered HR classification system built for William & Mary's Human Resources department. It combines web-scraped DHRM reference data, supervised machine learning (H2O AutoML), and LangChain multi-agent orchestration to classify position descriptions into Virginia's Career Group framework and recommend appropriate pay grades. Developed as a joint deliverable for BUAD 5742 (AI) and BUAD 5722 (Big Data), Spring 2026.

## Folder Structure

```
HR_Classification_Project/
├── README.md
├── environment.yml              Conda environment spec
├── .env.example                 API key template (no real keys)
├── .gitignore
│
├── notebooks/                   Jupyter pipeline (run 1-5 in order)
│   ├── 1_environment_setup.ipynb
│   ├── 2_dhrm_pipeline.ipynb    DHRM scrape + parse + reference tables
│   ├── 3_workday_scrape.ipynb   Workday scrape + label censoring
│   ├── 4_feature_engineering.ipynb   Regex feature extraction (15 features)
│   └── 5_h2o_automl.ipynb       H2O AutoML training + SHAP/PDP
│
├── data/
│   ├── reference/               7 DHRM reference Excel files
│   ├── training/                ML pipeline CSVs (postings, features, exclusions)
│   ├── cache/                   Raw scrape cache (gitignored, regenerable)
│   │   ├── raw_workday/
│   │   └── raw_pages/
│   └── schema/                  SQL schema + visual diagram
│
├── .streamlit/
│   └── config.toml              Streamlit theme configuration
├── app/                         LangChain agents + Streamlit app
│   ├── streamlit_app.py         Main Streamlit web interface
│   ├── feature_extraction.py    Regex-based feature extraction (15 features)
│   ├── ml_classifier.py         H2O/ML fallback classifier
│   ├── cloud_sql_config.py      GCP Cloud SQL connection config
│   ├── griffin_langchain_agents.py   Multi-agent classification system
│   ├── run_demo.py              LangChain agent terminal demo (Assignment 5)
│   ├── skills/                  Skill templates (classifier, pay matcher)
│   └── prompts/                 Classification prompt templates
│
├── models/                      H2O saved models (gitignored, regenerable)
├── reports/                     Analysis reports and visualizations
├── ppt/                         Presentation slide decks
├── docs/                        Project management (kanban, schedule, tasks)
├── archive/                     Legacy files preserved for reference
└── assignment5/                 Original A5 submission (preserved for provenance — use data/ instead)
```

## Quick Start

1. **Create the conda environment:**
   ```
   conda env create -f environment.yml
   conda activate griffin
   ```

2. **Set up API keys:**
   ```
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

3. **Install H2O (required for Notebook 5):**
   ```
   pip install h2o
   ```
   > Java is included via `openjdk=11` in environment.yml. If NB5 fails with a Java error, see `docs/griffin-operations-guide.html` Section 7.

4. **Run the notebook pipeline in order:**
   - `1_environment_setup.ipynb` -- verify packages and Java (needed for H2O)
   - `2_dhrm_pipeline.ipynb` -- scrape and parse all 56 DHRM career groups
   - `3_workday_scrape.ipynb` -- scrape W&M Workday postings, censor labels
   - `4_feature_engineering.ipynb` -- extract 15 structured features from PDs
   - `5_h2o_automl.ipynb` -- train classifier, generate SHAP explanations

5. **Run the Streamlit app:**
   ```
   streamlit run app/streamlit_app.py
   ```
   > **Note:** `app/run_demo.py` is the LangChain agent terminal-based demo (Assignment 5). Use `streamlit run` for the main web interface.

## Team

Mason School of Business MSBA, William & Mary -- Spring 2026

## Technology Stack

| Layer | Tools |
|-------|-------|
| Data Collection | requests, BeautifulSoup, pdfplumber |
| Database | SQLAlchemy, SQLite (MySQL optional) |
| Feature Engineering | pandas, regex |
| ML Training | H2O AutoML, SHAP |
| Agent Framework | LangChain, Google Gemini |
| App Layer | Streamlit |
| Environment | Conda (Python 3.11), Java (for H2O) |
