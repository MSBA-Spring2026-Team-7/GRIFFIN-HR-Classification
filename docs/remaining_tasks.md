# GRIFFIN — Remaining Tasks

**Updated:** April 12, 2026 (end of CQM Final Sprint session)
**Team 7:** Steven Alvarado, Anmol Motwani, JR Jones, Brynn Vetrano

---

## Before Tomorrow (April 13) — CRITICAL

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| 1 | Research paper citation | Brynn Vetrano | In Progress | Academic paper <3 years old on LLM classification, agentic AI, or HR automation. Add to README references + slides. |
| 2 | Validate 5-6 more W&M positions | Everyone | In Progress | Have 4-5 tested, need 10+ total. Each team member test 2-3 via the Streamlit app. |
| 3 | Verify environment.yml for clean install | Steven Alvarado | Open | Confirm h2o + openjdk are installable. Note: H2O requires separate install per Big Data lab process — document this in README if needed. |

---

## Before Wednesday (April 15) — AI Poster Conference

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| 4 | Print poster | JR Jones | Pending | Open `ppt/GRIFFIN_Poster_36x48.html` in Chrome → Ctrl+P → Save as PDF (48x36, background graphics ON, margins NONE) → send to print shop. |
| 5 | Add research paper to poster + slides | Brynn + Steven | Blocked on #1 | Once Brynn has the citation, add to References sections. |
| 6 | Poster session setup / logistics | JR Jones | Pending | Confirm location, time, easel/stand, digital display option. |

---

## Before Thursday (April 17) — Big Data Oral Presentation

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| 7 | Rehearse 10-min presentation | Steven + JR | Pending | 15 slides = ~40 sec/slide. 1-2 presenters. Practice transitions. |
| 8 | Prepare professor Q&A talking points | Steven | Pending | See "Professor Q&A Prep" section below. |
| 9 | Demo plan | Steven | Pending | Fast Mode first (instant, shows ML), then Full Analysis (shows AI + ranking). Have backup if API is slow. |

---

## After Courses (April 18+) — Client Deliverables for W&M HR

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| 10 | **Data Dictionary** | Unassigned | Pending | Document every field across 7 reference xlsx files + training data + schema: name, type, source, update frequency, instructions for proprietary data integration. |
| 11 | **User Guide / SOP** | Unassigned | Pending | Step-by-step for HR staff: how to paste a PD, choose Fast/Full mode, interpret results (confidence scores, ranked matches, W&M grades), when to override AI. Written for non-technical HR professionals. |
| 12 | **Validation Report** | Steven | Blocked on #2 | Test results from 10+ positions: accuracy by career group, edge cases, misclassifications, recommendations. This is the "confidence baseline" for HR. |

---

## Future Work (Post-Course)

| # | Task | Owner | Notes |
|---|---|---|---|
| 13 | GCP Cloud SQL deployment | Steven | Code ready (`cloud_sql_config.py`), schema ready (`wm_hr_classification_schema.sql`). Just needs Cloud SQL instance + `.env` credentials. |
| 14 | Expanded training data | Steven + HR | Connect to W&M HR systems for more PDs beyond the 103 currently available. Critical for improving minority-class accuracy. |
| 15 | H2O counterbalance weights | Steven | Add `balance_classes=True` to H2O AutoML config. Quick win for class imbalance. |
| 16 | Agent refinement | Steven | Conversation memory (multi-turn classification sessions), additional tools, refined reasoning prompts. |
| 17 | Fine-tuned embeddings + ensemble scoring | Steven | Research direction: custom embeddings trained on DHRM data, ensemble ML+LLM scoring. Potential thesis/independent study. |
| 18 | Migrate google.generativeai to google.genai | Steven | Current package is deprecated. Functional but should migrate before it breaks. |

---

## Professor Q&A Prep

Likely questions and prepared answers:

### "Why train H2O if the app uses Gemini?"
H2O validates the task is learnable from engineered features — it proves the classification problem has structure. The Streamlit app shows BOTH predictions: ML predicts the occupational family (instant, free, local), Gemini provides specific role matching with explainable rationale. When they agree, confidence is high. When they disagree, it flags positions that warrant human review. This is the dual-method transparency design.

### "Can you trust results with only 100 training rows and 4 Engineering examples?"
No — and that's exactly why GRIFFIN is advisory, not deterministic. The class imbalance is a known limitation documented in the ethical reflection. We used stratified 5-fold CV to preserve class proportions, and the human-in-the-loop architecture exists precisely because small-class predictions are unreliable. The AI reasoning compensates by analyzing duty descriptions against DHRM compensable factors (Complexity, Results, Accountability) — it doesn't rely solely on the ML patterns.

### "What makes this 'big data' and not just pandas on a laptop?"
The pipeline uses 8 course tools: H2O AutoML (automated ML at scale — 80 models evaluated), LangChain (multi-agent orchestration), Gemini API (LLM reasoning), CareerOneStop REST API (external salary data), BeautifulSoup (web scraping 56 DHRM pages), SQLAlchemy (database ORM with Cloud SQL migration path), Streamlit (interactive web app), and SHAP (ML explainability). The data acquisition alone involves 56 web pages scraped, 150 API calls, and 294 roles parsed. Cloud SQL infrastructure is deployment-ready with graceful SQLite fallback.

### "How did you handle the ethical considerations?"
Six dimensions documented: (1) Public data ethics — rate-limited scraping of government data with local caching. (2) Classification bias — acknowledged class imbalance, advisory framing. (3) Human-in-the-loop — AI recommends, HR decides, no auto-submission. (4) LLM transparency — reasoning narratives with confidence scores, not black-box. (5) Data privacy — 30+ pattern censoring pipeline removes PII before ML training. (6) API security — .env excluded from git, .env.example with placeholders.

### "What role did AI tools play in building this?"
Documented in `reports/ai_assisted_development.md`. Claude Code supported code development, troubleshooting, quality assurance (Red Team found and fixed a fabricated TF-IDF claim before submission), design research, and token optimization. The team maintained full decision authority — AI implemented the team's vision, it didn't originate it. All deliverables were human-reviewed before submission.

---

## GitHub PR Instructions

To push from your fork to the team repo:

1. Go to `https://github.com/Steven-Alvarado7/GRIFFIN-HR-Classification`
2. Click **"Contribute"** → **"Open pull request"**
3. Base: `MSBA-Spring2026-Team-7/GRIFFIN-HR-Classification` branch `master`
4. Compare: `Steven-Alvarado7/GRIFFIN-HR-Classification` branch `master_copy`
5. Title: "GRIFFIN Final Sprint: Streamlit app, slide deck, poster, ethical reflection"
6. Click **"Create pull request"**
7. If you have merge permissions: **"Merge pull request"** → **"Confirm merge"**

---

## Quick Reference

| Command | What it does |
|---|---|
| `conda activate griffin` | Activate the project environment |
| `streamlit run app/streamlit_app.py` | Launch the classification app |
| `setup_and_run.bat` | One-click setup + launch (Windows) |
| Open `ppt/GRIFFIN_Poster_36x48.html` in Chrome → Ctrl+P → PDF | Generate print-ready poster |
