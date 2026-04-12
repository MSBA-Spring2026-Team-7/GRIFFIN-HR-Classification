# GRIFFIN Project Task List

> W&M HR Position Classification & Pay Matching Tool
> Updated: April 12, 2026 | AI poster: April 15 | Big Data deck: April 17

---

## How to Use This File

1. **Read it** to see what's done, what's in progress, and what needs doing
2. **Claim a task** by putting your name next to it and telling the team
3. **Run the script** `docs/github-issues-setup.sh` in the GitHub repo to auto-create all of these as GitHub Issues with labels
4. **Track on the board** using GitHub Projects (Done / In Progress / To Do)

### Labels

| Label | Meaning |
|-------|---------|
| AI Course (TP3) | BUAD 5742 deliverable, April 15 poster |
| Big Data (5722) | BUAD 5722 deliverable, April 17 presentation |
| HR Handoff | Client deliverable for W&M HR |
| Shared | Serves both courses |
| WS1: Data | Workstream 1: Data Collection |
| WS2: Prompts | Workstream 2: Prompt Engineering |
| WS3: App | Workstream 3: Application & Integration |
| WS4: Validation | Workstream 4: Validation & Documentation |
| priority: high | Must complete before deadline |
| priority: medium | Important but not blocking |
| good first issue | Good for team members to pick up |
| blocked | Waiting on external dependency |

---

## Done (33 items)

All Workstream 1 (Data Collection) tasks are complete, plus the full ML pipeline (A1-A5), Assignment 5 (B1-B3), and all sprint deliverables for both courses.

### Workstream 1: Data Collection (previously completed)

- [x] **Scrape all 56 DHRM career groups** -- 50 HTML + 6 PDF, raw pages cached
- [x] **Parse HTML career groups (50)** -- BeautifulSoup + regex, all fields extracted
- [x] **Parse PDF career groups (6)** -- pdfplumber, 3 format variants handled
- [x] **FY26 DHRM salary structure** -- 9 pay bands from official PDF
- [x] **W&M salary structure** -- 46 pay grades (S01-S23 + H01-H23)
- [x] **DHRM-to-W&M crosswalk** -- 9-row mapping, Band 7->S18 validated
- [x] **Database load (SQLite)** -- 7 tables via sqlalchemy, verification queries passing
- [x] **Excel export** -- 7 .xlsx files in hr_handoff/
- [x] **Data validation** -- 56 career groups, 294 roles, 100% coverage
- [x] **Database schema design** -- 9-table SQL (6 reference + 3 classification output)
- [x] **Classification prompt v1** -- Draft with blend logic and explanation generation
- [x] **Project spec document (v3)** -- Full architecture and deliverables checklist
- [x] **Proof of Concept** -- Early prototype of classification logic
- [x] **Client response received (Mar 27)** -- Chas directed us to Workday job board (~149 postings with pay band labels). Confirmed Copilot/Gemini approved. Faculty excluded.

### ML Pipeline A1-A5 (previously completed)

- [x] **A1 -- Environment setup** -- Conda env `griffin` created via Anaconda (Python 3.11, 16 packages). Kernel registered as "GRIFFIN (conda)". H2O deferred -- follow Big Data lab process.
- [x] **A2 -- Workday scrape (CQM orchestrated)** -- 150 postings fetched, 103 staff retained, 47 faculty excluded. Labels extracted: comp_grade (100%), job_profile_code (95%), job_family (97%). Raw JSON cached in raw_workday/. CQM Three-Phase, 4 checkpoints, 36 criteria -- all passed.
- [x] **A3 -- Label stripping + censored PDs** -- Classification fields stripped from PD text. Zero label leakage confirmed (7-pattern scan across all 103 rows, 15 spot-checks). Outputs: workday_training.csv (103 rows), workday_postings.csv (full), workday_exclusions.csv (47 faculty).
- [x] **A4 -- Feature engineering** -- 15 structured features extracted from 103 censored PDs via regex: budget, supervision (gives/receives/count), education level (ordinal 0-5), years experience, text length, 6 domain keyword counts (leadership, technical, research, healthcare, facilities, finance), is_exempt, is_salaried. 30 W&M job families mapped to 7 DHRM occupational families. Output: workday_features.csv. Owner: Steven (Apr 6).
- [x] **A5 -- H2O AutoML training** -- 80 models trained (GBM, DRF, GLM, Deep Learning) on 100 rows x 15 features. 5-fold stratified CV. Best model: GBM (logloss ~0.95, ~48% accuracy, top-3 accuracy ~100%). Variable importance, SHAP (global + local), PDP generated. OpenJDK 25 installed into conda env. Notebook: griffin_h2o_automl.ipynb. Owner: Steven (Apr 6).

### Assignment 5: LangChain PoC (previously completed)

- [x] **B1 -- LangChain multi-agent PoC (Assignment 5)** -- All 8 required components: LLM init (Gemini), 2 agents (Classifier + Pay Matcher), multi-turn messages, streaming, 3 custom tools (search_career_groups, search_roles, match_pay_band), 2 external APIs (CareerOneStop Virginia salary + Tavily), agent memory (InMemorySaver), orchestration. 767-line script. CQM Three-Phase, 21/21 criteria passed. Owner: Steven (Apr 6).
- [x] **B2 -- skill.md + template files** -- Classifier skill (duty blocks -> career group mapping -> compensable factors) and Pay Matcher skill (DHRM crosswalk -> W&M grades -> Virginia salary). Typed parameters, step-by-step instructions. Zipped for Gradescope. Owner: Steven (Apr 6).
- [x] **B3 -- Design rationale report (1 page)** -- Architecture description (3 agents, 5 tools, orchestration pattern), design decisions (Gemini, CareerOneStop, tool decomposition), GRIFFIN integration (Layer 3 with H2O plug-in point). ~700 words. Owner: Steven (Apr 6).

### AI Course Sprint (completed Apr 12)

- [x] **#1 -- GitHub README** -- Full README with architecture diagram, author bios, responsible AI section, references. Owner: Anmol (Apr 12).
- [x] **#2 -- GitHub Projects kanban board** -- Board created with issues, active use throughout semester. Owner: Anmol (Apr 12).
- [x] **#3 -- Streamlit web app** -- Dual ML+AI classification pipeline with Fast/Full modes, 3 ranked classification cards, pay matching, explanations. Owner: Anmol + Steven (Apr 12).
- [x] **#4 -- Conference poster** -- 36x48 HTML poster with SHAP visualizations, architecture diagram, responsible AI section. Owner: JR Jones (Apr 12).
- [x] **#6 -- Responsible AI section** -- Standalone report + slide 12 content + README section covering bias, HITL, privacy, explainability, transparency. Owner: Brynn (Apr 12).

### Big Data Sprint (completed Apr 12)

- [x] **#7 -- GCP Cloud SQL** -- cloud_sql_config.py with graceful degradation (SQLite fallback when GCP unavailable). Owner: Steven (Apr 12).
- [x] **#8 -- Visualizations** -- SHAP plots, variable importance, PDP in Notebook 5. Owner: Steven (Apr 12).
- [x] **#9 -- Slide deck** -- 13 slides with W&M branding, SHAP images, architecture diagram. Owner: JR Jones + Steven (Apr 12).
- [x] **#10 -- Ethical reflection** -- reports/ethical_reflection.md covering 6 dimensions (data sourcing, scraping ethics, classification bias, LLM disclosure, privacy, human oversight). Owner: Brynn (Apr 12).
- [x] **#11 -- Project folder structure** -- Clean semantic directory structure (data/, notebooks/, reports/, ppt/, app/, docs/, archive/). Owner: JR Jones (Apr 12).

### Shared (completed Apr 12)

- [x] **#12 -- Pay estimation prompt** -- Midpoint-as-ceiling W&M grade matching with weighted math for blended roles. Owner: Steven (Apr 12).

---

## In Progress (2 items)

| # | Task | Priority | Assignee | Notes |
|---|------|----------|----------|-------|
| 5 | **Research paper citation** | MEDIUM | Brynn | Academic paper < 3 years old on LLM classification, agentic AI, or HR automation |
| 13 | **Validate against 10+ W&M positions** | HIGH | Everyone | 4-5 tested so far, need 5-6 more for full coverage |

---

## To Do -- HR Handoff Package

| # | Task | Priority | Assignee |
|---|------|----------|----------|
| 14 | **Data dictionary** | MEDIUM | Unassigned |
| | Every field documented: description, type, source, update frequency. Instructions for proprietary data. | | |
| 15 | **User guide / SOP** | MEDIUM | Unassigned |
| | Step-by-step workflow for classifying a position using prompts with Copilot/Gemini | | |
| 16 | **Validation report** | MEDIUM | Steven |
| | Test results, accuracy metrics, edge cases, recommendations. Depends on task #13. | | |

---

## Blocked / Waiting (1 item)

| Item | Blocker | Workaround |
|------|---------|------------|
| Proprietary data integration | Depends on client providing internal position data | Schema is designed for it, will slot in when available |

**Resolved:** LLM API selection -- LangChain confirmed as production framework (Prof. Chung, verbal Mar 30). `init_chat_model()` makes the app LLM-agnostic (Copilot/Gemini/Claude via config string).

---

## Team Contributions

| Member | Domain | Key Deliverables |
|--------|--------|------------------|
| **Steven Alvarado** | Pipeline + ML + App | A1-A5 pipeline, B1-B3 LangChain agents, Streamlit app (co-dev), feature engineering, H2O AutoML, GCP Cloud SQL, visualizations, pay estimation prompt, slide deck (co-dev) |
| **Anmol Motwani** | UI + Repo | Streamlit UI design (co-dev), GitHub README, GitHub Projects kanban board |
| **JR Jones** | Design + Delivery | Conference poster (36x48 HTML), slide deck (co-dev), project folder structure |
| **Brynn Vetrano** | Research + Ethics | Responsible AI report, ethical reflection (6 dimensions), research paper (in progress) |

---

## Timeline

```
Mar 30-31 (DONE)     A1 env setup, A2 Workday scrape, A3 label stripping. Docs updated.
Apr 1-5              Feature engineering (A4). Quick wins: research paper, folder restructure.
Apr 5-8              H2O AutoML training (A5). Set up H2O via Big Data lab process. Visualizations.
Apr 6 (DONE)         Assignment 5 submitted (B1 LangChain PoC + B2 skill.md + B3 report).
Apr 7-11             Streamlit app (#3). Position validation (#13). Cloud SQL (#7).
Apr 11-12 (DONE)     Sprint: all AI + Big Data deliverables completed.
APRIL 15             AI COURSE POSTER PRESENTATION
April 16             Big Data slide deck finalized (#9).
APRIL 17             BIG DATA PRESENTATION
April 18+            HR handoff package (#14, #15, #16).
```

---

## Quick Start for New Team Members

1. Clone the repo
2. Set up the conda environment: `conda create -n griffin python=3.11 -y` then `conda activate griffin` and install deps (see `griffin_environment_setup.ipynb`)
3. Open `00_START_HERE.html` in your browser -- interactive team briefing portal
4. Open `griffin_dhrm_pipeline.ipynb` -- core WS1 data pipeline notebook
5. Open `griffin_workday_scrape.ipynb` -- Workday scrape + label stripping notebook
6. Look at `workday_training.csv` -- 103 censored PDs, our ML training data
7. Look at `hr_handoff/` -- 7 Excel files for the client
8. Read `Course References/wm-hr-classification-project-prompt-v3.md` -- full project spec
9. Pick a task from the "To Do" section above and tell the team
10. Run `docs/github-issues-setup.sh` in the repo to create GitHub Issues (needs `gh` CLI)
