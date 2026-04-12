# AI-Assisted Development Report

**GRIFFIN HR Classification Project**
BUAD 5722 / BUAD 5742 — Spring 2026 — Team 7
Steven Alvarado, Anmol Motwani, JR Jones, Brynn Vetrano

---

## Overview

This project leveraged Claude Code (Anthropic) as an AI development partner throughout the pipeline. The team maintained full decision authority — AI supported execution of the team's vision, not the other way around. This document details where and how AI assistance was used, what value it provided, and where human judgment remained essential.

---

## 1. Code Development and Execution

**What AI did:**
- Translated the team's classification concept into working Python code across the full stack: web scraping (BeautifulSoup, requests), feature engineering (regex, pandas), ML training (H2O AutoML), and Streamlit web application
- Built the LangChain multi-agent system — 3 specialized agents (Classifier, Pay Matcher, Orchestrator), 5 integrated tools, and an orchestration pattern that delegates tasks across agents
- Implemented the dual-classification architecture: H2O AutoML for traditional ML predictions alongside Gemini AI for agentic role-level classification with explainable reasoning
- Created the 15-feature extraction pipeline matching Notebook 4's engineering specifications

**What the team decided:**
- The classification approach (dual-method ML + AI), the target taxonomy (DHRM career groups), the data sources (DHRM, Workday, CareerOneStop), and the user-facing design (Fast Mode vs Full Analysis) were all team decisions
- AI implemented these decisions; it did not originate them

---

## 2. Troubleshooting and Environment Management

**What AI did:**
- Diagnosed and resolved conda environment issues: missing `google-generativeai` and `python-dotenv` packages that were declared in `environment.yml` but not installed in the live environment
- Identified that the Streamlit app must be launched via `streamlit run` (not `python app.py`) — a common beginner mistake that produces confusing "missing ScriptRunContext" warnings
- Resolved H2O Java dependency issues: the JVM requires `JAVA_HOME` set correctly within the conda environment, and `openjdk=11` must be in the conda dependencies
- Fixed branch naming confusion in GitHub (mastercopy vs master_copy) by merging branches and pushing to the correct default

**What the team learned:**
- Modifying `environment.yml` declares dependencies but does not install them into an existing environment — you must run `conda env update` or `pip install` separately
- Environment management is a critical part of reproducibility, not just a setup step

---

## 3. Quality Assurance — Red Team Review

**What AI did:**
- Conducted an adversarial Red Team review of all deliverables against both course rubrics (BUAD 5722 Big Data + BUAD 5742 AI), producing 12 findings rated by severity
- **Caught a fabricated claim:** Slide 5 of the presentation claimed "TF-IDF text vectorization" as a feature engineering technique. The project never uses TF-IDF — it uses regex-based keyword counting. This was corrected before submission. A professor reading the notebooks would have immediately flagged this inconsistency.
- **Caught a data discrepancy:** "53 models" in TASKS.md vs "80 models" in the slides. The correct number (80, from the latest H2O AutoML run) was reconciled across all documents.
- **Identified stale README:** Quick Start instructions pointed to `python run_demo.py` (the terminal-based LangChain demo) instead of `streamlit run app/streamlit_app.py` (the actual web app). Updated before submission.
- Verified security: no API keys in committed files, `.env` properly gitignored, `.env.example` contains only placeholders

**What the team decided:**
- Which findings to fix (both CRITICALs and the README) vs. accept as known limitations (GCP Cloud SQL not deployed, framed as "deployment-ready")
- The Red Team found the issues; the team decided what to do about them

---

## 4. Research and Design Exploration

**What AI did:**
- **Display technology evaluation:** Researched Canvas Design (programmatic art generation) vs HTML/CSS vs python-pptx for the conference poster. Concluded that HTML-to-PDF via Chrome Print was optimal for data-dense academic content — Canvas Design is built for abstract visual art, not structured information layouts with readable text and data charts.
- **Streamlit theming investigation:** Read the official Streamlit agent-skills documentation and discovered that our extensive CSS overrides were causing invisible text (toggles, captions, expanders). The proper approach is `.streamlit/config.toml` for native component theming, with CSS only for custom HTML elements. This resolved persistent visibility bugs.
- **W&M pay grade matching:** Researched the midpoint-as-ceiling compensation principle — that W&M hiring targets cluster at or below the grade midpoint. Implemented salary extraction from position descriptions to improve grade matching accuracy.

**What the team decided:**
- Color scheme direction (Option C: warm cream with W&M green accents — chosen from 4 options presented)
- The Owner identified the midpoint-as-ceiling pattern from HR domain knowledge; AI implemented the matching logic

---

## 5. Efficiency and Token Optimization

**What AI did:**
- Designed a **local-first architecture** to minimize API costs:
  - H2O AutoML runs entirely locally — zero API tokens for ML predictions
  - Feature extraction (15 features from PD text) runs locally via regex — zero API tokens
  - Gemini API is called only in Full Analysis mode, and only for tasks AI uniquely provides (role-level classification with reasoning)
- Implemented **Fast Mode vs Full Analysis toggle** — giving users explicit control over whether to spend API tokens
- Added **H2O model caching** (`@st.cache_resource`) so the Java Virtual Machine boots once at app startup, not on every classification. This reduced per-classification latency from 10-15 seconds to milliseconds.
- Implemented **graceful degradation** for GCP Cloud SQL: try Cloud SQL first, fall back to local SQLite silently. The app always works, regardless of cloud infrastructure availability.

**Why this matters for a client:**
- An HR department classifying hundreds of positions can use Fast Mode for bulk screening (instant, free) and Full Analysis only for ambiguous cases that need AI reasoning. This is a practical cost-management strategy, not just a technical feature.

---

## 6. Data Acquisition Support

**What AI did:**
- Developed the web scraping strategy for 56 DHRM career group pages: rate-limited requests (1.5-second delays), local caching so each URL is fetched at most once, and dual-path parsing (50 HTML pages + 6 PDF documents via pdfplumber)
- Built the Workday API parsing pipeline: two-stage extraction (list pagination to discover postings, then detail fetch for each position description), with em-dash sanitization for Workday's encoding quirks
- Implemented the censoring pipeline: 30+ regex skip patterns that remove classification-revealing metadata (JP codes, compensation grades, salary ranges, EEO boilerplate) to prevent data leakage in ML training
- Integrated CareerOneStop REST API for Virginia salary benchmarking as a validation data source

**What the team decided:**
- Which data sources to use, what to censor (and why), and the ethical framework for scraping public government data

---

## 7. Human-AI Collaboration Model

Throughout this project, AI functioned as an **execution partner**, not a decision-maker:

| Dimension | Human (Team) | AI (Claude Code) |
|---|---|---|
| Problem definition | Team identified W&M HR's classification challenge | AI helped articulate it for different audiences |
| Technical approach | Team chose dual ML + AI method | AI implemented the architecture |
| Design decisions | Team chose W&M colors, layout, display format | AI generated options, team selected |
| Quality standards | Team set the bar ("respect the grade") | AI executed CQM framework for verification |
| Domain knowledge | Team knew midpoint-as-ceiling HR practice | AI coded the matching logic |
| Ethical judgment | Team defined responsible AI principles | AI documented them in the reflection |
| Final deliverables | Team reviewed, edited, and approved everything | AI produced drafts and revisions |

**Key principle:** AI amplified the team's capacity but did not replace domain expertise, professional judgment, or academic integrity. Every deliverable was human-reviewed before submission.

---

## Tools and Frameworks Used

- **Claude Code** (Anthropic) — AI development partner for code, QA, and research
- **CQM Orchestration Framework** — Structured quality control adapted from USACE Construction Quality Management: Preparatory Phase, Initial Phase with independent QC, Follow-up Phase with checkpoints, Red Team adversarial review
- **Streamlit Agent Skills** (official Streamlit documentation) — Best practices for theming, layouts, and performance
- **Google Gemini 2.5 Flash** — LLM for position description classification and explanation generation
- **H2O AutoML** — Automated machine learning for traditional classification
