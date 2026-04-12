# GRIFFIN

**AI-Powered HR Position Classification & Pay Tool for William & Mary**

| | |
|---|---|
| **Course** | BUAD 5722 Big Data Analytics / BUAD 5742 AI -- Spring 2026 |
| **Team** | Steven Alvarado, Anmol Motwani, JR Jones, Brynn Vetrano |
| **Built for** | William & Mary Human Resources |
| **Acronym** | Government Role Identification and Financial Framework Integration Network |

> Built with CQM (Construction Quality Management) orchestration framework for structured quality control.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
4. [Quick Start](#quick-start)
5. [Project Structure](#project-structure)
6. [Data Pipeline](#data-pipeline)
7. [ML Performance](#ml-performance)
8. [Responsible AI](#responsible-ai)
9. [What's Next](#whats-next)
10. [Technology Stack](#technology-stack)
11. [References](#references)
12. [Acknowledgments](#acknowledgments)

---

## Project Overview

William & Mary's Human Resources department manages over 500 position descriptions (PDs) across dozens of occupational families. Classifying each PD into the correct Virginia DHRM career group and matching it to an appropriate W&M pay grade is a manual, time-intensive process that can produce inconsistent results when done by different reviewers.

GRIFFIN automates this classification using a **dual-method approach**:

- **H2O AutoML (Traditional ML):** A gradient boosted machine trained on 103 W&M position descriptions, extracting 15 structured features via regex and keyword counting. Provides instant, explainable predictions with SHAP feature importance.
- **Google Gemini AI (Agentic Classification):** A LangChain multi-agent system that reads the full position description text, reasons over DHRM classification criteria (Complexity, Results, Accountability), and produces a structured narrative explaining its recommendation.

Both methods feed into a Streamlit web application where HR professionals paste a position description, receive ranked career group matches with confidence scores, and review pay grade estimates -- all with full transparency into the AI's reasoning. GRIFFIN is an **advisory tool**: the AI recommends, the human decides.

---

## Key Features

**Dual-Method Classification**
- **Fast Mode** -- ML-only classification; returns results in seconds
- **Full Analysis** -- ML + Gemini AI; produces detailed reasoning narratives alongside ML predictions

**Ranked Match Cards**
- Top 3 career group matches displayed as cards with confidence scores (1-100)
- Each card includes the career group name, matched role, and classification rationale

**W&M Pay Grade Estimation**
- Midpoint-as-ceiling method maps DHRM pay bands to W&M salary grades
- Crosswalk table links state pay bands to university compensation structure

**SHAP Explainability**
- Global feature importance shows which of the 15 features drive the model overall
- Individual prediction explanations show why the model chose a specific career group for a given PD

**Human-in-the-Loop Design**
- AI produces recommendations with confidence scores and reasoning
- HR professional reviews, accepts, modifies, or overrides the suggestion
- The tool never auto-submits or writes to any HR system

**GCP Cloud SQL Ready**
- SQLAlchemy-based database layer with 9-table schema
- Graceful SQLite fallback when Cloud SQL is unavailable
- Migration path ready for production GCP deployment

---

## Architecture

GRIFFIN is a 4-layer stack. Each layer is independently testable and connects through well-defined interfaces.

```
Layer 1: Data Pipeline         Notebooks 1-5 (scrape, parse, engineer, train)
            |
Layer 2: ML Model              H2O AutoML GBM + sklearn fallback
            |
Layer 3: LangChain Agents      Multi-agent system (Gemini API + reference data tools)
            |
Layer 4: Streamlit App          Web UI for HR professionals
```

### Course Tools Used

| Category | Tools |
|---|---|
| Data Collection | requests, BeautifulSoup, pdfplumber |
| Database | SQLAlchemy, SQLite (GCP Cloud SQL optional) |
| Feature Engineering | pandas, regex |
| ML Training | H2O AutoML, SHAP |
| Agent Framework | LangChain, LangGraph, Google Gemini |
| External API | CareerOneStop REST API |
| Visualization | Streamlit, Plotly, Seaborn, Matplotlib |
| Environment | Conda (Python 3.11), OpenJDK 11 (for H2O) |

---

## Quick Start

Follow these steps exactly to run GRIFFIN from a fresh clone. Tested on Windows 10/11 and macOS.

### Step 1: Clone the Repository

```bash
git clone https://github.com/Steven-Alvarado7/GRIFFIN-HR-Classification.git
cd GRIFFIN-HR-Classification
```

### Step 2: Create the Conda Environment

```bash
conda env create -f environment.yml
conda activate griffin
```

This installs Python 3.11, all required packages (pandas, streamlit, langchain, shap, etc.), and OpenJDK 11 (required for H2O in Notebook 5). See `environment.yml` for the full dependency list.

### Step 3: Set Up API Keys

```bash
cp .env.example .env
```

Open the `.env` file in a text editor and add your actual keys:

```
GOOGLE_API_KEY=your-actual-google-gemini-key
TAVILY_API_KEY=your-tavily-key-here
CAREERONESTOP_TOKEN=your-careeronestop-token-here
CAREERONESTOP_USER_ID=your-careeronestop-user-id-here
```

**Minimum requirement:** Only `GOOGLE_API_KEY` is needed to run the Streamlit app with Full Analysis mode. The other keys enable optional features (web search, labor market data).

### Step 4: Run the Streamlit App

```bash
streamlit run app/streamlit_app.py
```

The app opens in your browser at `http://localhost:8501`.

### Step 5: Classify a Position Description

1. Paste a position description into the text area
2. Choose a classification mode:
   - **Fast Mode** -- ML only, returns results in seconds
   - **Full Analysis** -- ML + Gemini AI, takes 15-30 seconds, includes detailed reasoning
3. Click **Classify PD**
4. Review the results:
   - Top 3 career group matches with confidence scores
   - Matched DHRM role within each career group
   - W&M pay grade estimate (band, grade, salary range)
   - AI reasoning narrative (Full Analysis mode)
   - SHAP feature importance for the prediction

### Optional: Run the Notebook Pipeline

If you want to reproduce the data pipeline and model training from scratch:

```bash
# Run notebooks in order (1 through 5)
# 1_environment_setup.ipynb    -- verify packages and Java
# 2_dhrm_pipeline.ipynb        -- scrape 56 DHRM career groups
# 3_workday_scrape.ipynb       -- scrape W&M Workday postings
# 4_feature_engineering.ipynb  -- extract 15 features from PDs
# 5_h2o_automl.ipynb           -- train H2O AutoML, generate SHAP
```

**Note on H2O:** If Notebook 5 fails with a Java error, verify that `openjdk=11` is installed in your conda environment. Run `java -version` to confirm. See `docs/griffin-operations-guide.html` Section 7 for troubleshooting.

### Optional: Run the LangChain Terminal Demo

```bash
python app/run_demo.py
```

This runs the Assignment 5 multi-agent demo in the terminal (no Streamlit UI). Useful for testing the LangChain agent pipeline directly.

---

## Project Structure

```
GRIFFIN-HR-Classification/
|
|-- app/                              Application layer
|   |-- streamlit_app.py              Main Streamlit web application
|   |-- feature_extraction.py         15-feature regex extraction from PD text
|   |-- ml_classifier.py              H2O AutoML classifier + sklearn fallback
|   |-- cloud_sql_config.py           GCP Cloud SQL connection (SQLite fallback)
|   |-- griffin_langchain_agents.py    LangChain multi-agent system (767 lines)
|   |-- run_demo.py                   Terminal-based LangChain demo (Assignment 5)
|   |-- prompts/                      Classification prompt templates
|   |-- skills/                       Agent skill definitions (classifier, pay matcher)
|
|-- data/
|   |-- reference/                    7 DHRM reference Excel files
|   |   |-- career_groups.xlsx        56 career group definitions
|   |   |-- roles.xlsx                Role-level detail within each group
|   |   |-- dhrm_pay_bands.xlsx       State pay band structure
|   |   |-- crosswalk.xlsx            DHRM-to-W&M grade mapping
|   |   |-- wm_pay_grades.xlsx        W&M salary grades and ranges
|   |   |-- (+ 2 additional reference files)
|   |-- training/                     ML training data
|   |   |-- workday_training.csv      103 censored PDs with labels
|   |   |-- features_matrix.csv       15 extracted features per PD
|   |   |-- exclusions.csv            Excluded records with reasons
|   |-- cache/                        Raw scrape cache (gitignored, regenerable)
|   |-- schema/                       SQL schema (9 tables) + visual diagram
|
|-- notebooks/
|   |-- 1_environment_setup.ipynb     Verify packages, Java, and data inventory
|   |-- 2_dhrm_pipeline.ipynb         DHRM web scraping (56 career groups)
|   |-- 3_workday_scrape.ipynb        Workday PD extraction + censoring pipeline
|   |-- 4_feature_engineering.ipynb   15 ML features via regex/keyword counting
|   |-- 5_h2o_automl.ipynb           H2O AutoML training + SHAP explainability
|
|-- reports/                          Ethical reflection + analysis reports
|-- ppt/                              Big Data presentation deck
|-- docs/                             Operations guide, task tracker, project plans
|-- archive/                          Legacy files preserved for reference
|-- assignment5/                      Original A5 submission (preserved for provenance)
|-- models/                           H2O saved models (gitignored, regenerable)
|
|-- .streamlit/config.toml            W&M branded theme (green/gold)
|-- environment.yml                   Conda environment specification
|-- .env.example                      API key template (copy to .env)
|-- .gitignore                        Excludes .env, cache/, models/
```

---

## Data Pipeline

The pipeline is split across five numbered notebooks, designed to run in order. Each notebook is self-contained and produces output files consumed by the next.

### Notebook 1: Environment Setup

Verifies that all required packages are installed, confirms Java is available for H2O, and inventories the data directory.

### Notebook 2: DHRM Pipeline

Scrapes the Virginia Department of Human Resource Management website to build a complete taxonomy of 56 career groups.

- **50 HTML pages** parsed with BeautifulSoup
- **6 PDF pages** parsed with pdfplumber
- Rate-limited scraping: 1.5-second delay between requests, local caching
- Produces 7 reference Excel files used throughout the system

### Notebook 3: Workday Scraping

Extracts position descriptions from William & Mary's Workday system.

- **150 postings scraped**, 103 staff PDs retained after filtering
- **Censoring pipeline:** Two-phase process strips classification-revealing metadata
  - Removes job profile codes (JP numbers), compensation grades (S/H codes), dollar amounts, salary ranges, job family labels, FLSA status, EEO boilerplate
  - 30+ skip patterns applied line-by-line
  - Rationale: these fields constitute data leakage in a classification model

### Notebook 4: Feature Engineering

Extracts 15 structured features from each censored PD using regex and keyword counting.

- Features include: word count, supervisory indicators, budget language, technical terms, education requirements, complexity markers, and more
- All features derived from `censored_text` column (no leakage from raw metadata)

### Notebook 5: H2O AutoML

Trains a multi-class classifier to predict occupational family from the 15 features.

- 80 models trained via H2O AutoML with 5-fold stratified cross-validation
- Best model: GBM with learning rate annealing
- SHAP explainability: global feature importance + individual prediction explanations
- Partial dependence plots (PDP) for top features

---

## ML Performance

| Metric | Value |
|---|---|
| Models Trained | 80 (via H2O AutoML) |
| Best Model | GBM with learning rate annealing |
| Top-1 Accuracy | 69% |
| Top-3 Accuracy | 90% |
| Macro F1 | 0.54 |
| Cross-Validation | 5-fold stratified |

**Class Imbalance Context:** The training dataset has significant class imbalance. Administrative Services accounts for 55 of 103 records, while the smallest classes (Engineering and Technology, Health and Human Services) have only 3-4 records each. This imbalance is why GRIFFIN uses a dual-method approach -- the Gemini AI agent can reason about career group criteria even for classes with limited training data.

---

## Responsible AI

GRIFFIN was designed with responsible AI principles embedded in the engineering, not added as an afterthought. Full details are in `reports/ethical_reflection.md`.

**Public Data Ethics**
All DHRM reference data is public government information. The scraping pipeline uses rate-limited requests (1.5-second delays) and local caching so each URL is fetched at most once.

**Classification Bias Awareness**
The 103-PD training dataset is small and imbalanced. GRIFFIN is explicitly designed as an advisory tool, not a decision-maker. Confidence scores and alternative matches give HR professionals the information needed to evaluate recommendations critically.

**Human-in-the-Loop**
The tool never auto-submits classifications, never writes to any HR system, and never removes the human from the decision loop. Classification decisions affect employee compensation and career progression -- that authority remains with qualified HR professionals.

**LLM Transparency**
Every AI classification includes a structured reasoning narrative that references specific duties from the PD and maps them to DHRM criteria. The LangChain agent pipeline is auditable from end to end, with 8 distinct components producing traceable output.

**Data Privacy**
Position descriptions undergo a rigorous censoring pipeline (30+ skip patterns) before ML training. No personally identifiable information appears in the training data. The `budget_amount_max` feature was dropped because dollar amounts were already stripped during censoring.

**API Key Security**
All credentials are managed through `.env` files excluded from version control. The repository includes `.env.example` with placeholder values. At no point are API keys hardcoded in source files.

---

## What's Next

- **GCP Cloud SQL Deployment** -- The 9-table SQL schema and SQLAlchemy migration layer are ready. Moving from SQLite to Cloud SQL enables multi-user access and persistent classification history.
- **Expanded Training Data** -- Adding more PDs from additional W&M departments would improve accuracy for underrepresented career groups.
- **H2O Counterbalance Weights** -- Applying class weights during training to address the imbalance between Administrative Services (55 records) and smaller classes (3-4 records).
- **Agent Refinement** -- Adding conversation memory and additional tools to the LangChain agent system for multi-turn classification sessions.

---

## Technology Stack

| Layer | Tools |
|---|---|
| Data Collection | requests, BeautifulSoup, pdfplumber |
| Database | SQLAlchemy, SQLite (GCP Cloud SQL optional) |
| Feature Engineering | pandas, regex |
| ML Training | H2O AutoML, SHAP |
| Agent Framework | LangChain, LangGraph, Google Gemini |
| External API | CareerOneStop REST API |
| Visualization | Streamlit, Plotly, Seaborn, Matplotlib |
| Environment | Conda (Python 3.11), OpenJDK 11 (for H2O) |

---

## References

- Virginia DHRM: https://www.dhrm.virginia.gov/
- CareerOneStop API: https://www.careeronestop.org/Developers/WebAPI/web-api.aspx
- H2O AutoML: https://docs.h2o.ai/h2o/latest-stable/h2o-docs/automl.html
- LangChain: https://python.langchain.com/
- Streamlit: https://streamlit.io/
- SHAP: https://shap.readthedocs.io/

---

## Acknowledgments

GRIFFIN was built for William & Mary's Human Resources department as a joint deliverable for BUAD 5722 (Big Data Analytics) and BUAD 5742 (AI), Spring 2026, at the Mason School of Business.

We thank our professors for their guidance on responsible AI development and practical machine learning, and William & Mary HR for the domain context that shaped this tool.
