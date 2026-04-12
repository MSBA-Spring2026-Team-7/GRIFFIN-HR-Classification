# GRIFFIN Project Task List

> W&M HR Position Classification & Pay Matching Tool
> Updated: April 6, 2026 | AI poster: April 15 | Big Data deck: April 17

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

## Done (22 items)

All Workstream 1 (Data Collection) tasks are complete, plus the full ML pipeline (A1-A5) and Assignment 5 (B1-B3).

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
- [x] **A1 -- Environment setup** -- Conda env `griffin` created via Anaconda (Python 3.11, 16 packages). Kernel registered as "GRIFFIN (conda)". H2O deferred -- follow Big Data lab process.
- [x] **A2 -- Workday scrape (CQM orchestrated)** -- 150 postings fetched, 103 staff retained, 47 faculty excluded. Labels extracted: comp_grade (100%), job_profile_code (95%), job_family (97%). Raw JSON cached in raw_workday/. CQM Three-Phase, 4 checkpoints, 36 criteria -- all passed.
- [x] **A3 -- Label stripping + censored PDs** -- Classification fields stripped from PD text. Zero label leakage confirmed (7-pattern scan across all 103 rows, 15 spot-checks). Outputs: workday_training.csv (103 rows), workday_postings.csv (full), workday_exclusions.csv (47 faculty).
- [x] **B1 -- LangChain multi-agent PoC (Assignment 5)** -- All 8 required components: LLM init (Gemini), 2 agents (Classifier + Pay Matcher), multi-turn messages, streaming, 3 custom tools (search_career_groups, search_roles, match_pay_band), 2 external APIs (CareerOneStop Virginia salary + Tavily), agent memory (InMemorySaver), orchestration. 767-line script. CQM Three-Phase, 21/21 criteria passed. Owner: Steven (Apr 6).
- [x] **B2 -- skill.md + template files** -- Classifier skill (duty blocks → career group mapping → compensable factors) and Pay Matcher skill (DHRM crosswalk → W&M grades → Virginia salary). Typed parameters, step-by-step instructions. Zipped for Gradescope. Owner: Steven (Apr 6).
- [x] **B3 -- Design rationale report (1 page)** -- Architecture description (3 agents, 5 tools, orchestration pattern), design decisions (Gemini, CareerOneStop, tool decomposition), GRIFFIN integration (Layer 3 with H2O plug-in point). ~700 words. Owner: Steven (Apr 6).
- [x] **A4 -- Feature engineering** -- 15 structured features extracted from 103 censored PDs via regex: budget, supervision (gives/receives/count), education level (ordinal 0-5), years experience, text length, 6 domain keyword counts (leadership, technical, research, healthcare, facilities, finance), is_exempt, is_salaried. 30 W&M job families mapped to 7 DHRM occupational families. Output: workday_features.csv. Owner: Steven (Apr 6).
- [x] **A5 -- H2O AutoML training** -- 80 models trained (GBM, DRF, GLM, Deep Learning) on 100 rows x 15 features. 5-fold stratified CV. Best model: GBM (logloss ~0.95, ~48% accuracy, top-3 accuracy ~100%). Variable importance, SHAP (global + local), PDP generated. OpenJDK 25 installed into conda env. Notebook: griffin_h2o_automl.ipynb. Owner: Steven (Apr 6).

---

## In Progress (0 items)

No tasks currently in progress. Next up: visualizations (#8), Streamlit app (#3), and team-assigned tasks below.

---

## To Do -- Critical Path (Do First)

> A1-A5 and B1-B3 are DONE. Remaining critical path: Streamlit app -> visualizations -> presentations.

| # | Task | Priority | Depends On | Assignee |
|---|------|----------|------------|----------|
| ~~A1~~ | ~~Environment setup~~ | DONE | -- | Steven |
| ~~A2~~ | ~~Workday scrape~~ | DONE | A1 | Steven |
| ~~A3~~ | ~~Label stripping~~ | DONE | A2 | Steven |
| ~~A4~~ | ~~Feature engineering on censored PDs~~ | DONE | A3 | Steven |
| ~~A5~~ | ~~H2O AutoML training~~ | DONE | A4 | Steven |

---

## Done -- Assignment 5: LangChain Proof-of-Concept (PoC)

> Assignment 5 completed April 6, 2026. All deliverables in `assignment5/` folder. CQM-orchestrated (Full Three-Phase, 21/21 criteria passed).

| # | Task | Status | Assignee | Completed |
|---|------|--------|----------|-----------|
| ~~B1~~ | ~~LangChain multi-agent PoC~~ | DONE | Steven | Apr 6 |
| ~~B2~~ | ~~skill.md + template files~~ | DONE | Steven | Apr 6 |
| ~~B3~~ | ~~Design rationale report (1 page)~~ | DONE | Steven | Apr 6 |

---

## To Do -- AI Course (April 15 poster)

> Rubric weights shown in parentheses. Items marked with a star are good for team pickup.

| # | Task | Priority | Rubric Weight | Assignee |
|---|------|----------|--------------|----------|
| 1 | **GitHub README** | HIGH | 7% (repo organization) | Anmol |
| | Sections: visuals, author bios w/ GitHub links, project scope, details, "What's Next?", responsible AI, references | | | |
| 2 | **GitHub Projects kanban board** | HIGH | 7% (board organization) | Anmol |
| | Create board, add all issues, show active use during semester | | | |
| 3 | **Streamlit web app (agentic AI)** | HIGH | 7% + 7% (website + code demo) | Anmol |
| | Paste PD, get classification + pay + explanation. Must show agentic design (reasoning, tool use, reflection) | | | |
| 4 | **Conference poster** | HIGH | 7% (poster) + 6% (presentation) | Anmol |
| | Problem, architecture, demo screenshots, research paper, responsible AI, team | | | |
| 5 | **Research paper citation** | MEDIUM | 7% (paper quality + discussion) | Brynn |
| | Academic paper < 3 years old on LLM classification, agentic AI, or HR automation | | | |
| 6 | **Responsible AI section** | MEDIUM | Part of README + poster | Brynn |
| | Bias risks, human-in-the-loop, data privacy, explainability, transparency | | | |

---

## To Do -- Big Data Course (April 17 presentation)

| # | Task | Priority | Rubric Area | Assignee |
|---|------|----------|-------------|----------|
| 7 | **Deploy to Google Cloud SQL** | HIGH | Technical Depth | Steven |
| | Migrate SQLite to MySQL on GCP. Update notebook connection. Evidence of GCP usage. | | | |
| 8 | **Add visualizations to notebook** | HIGH | Visualization | Steven |
| | matplotlib/seaborn/plotly: roles by family, pay band heatmap, SOC coverage, group sizes | | | |
| 9 | **Slide deck** | HIGH | Presentation | Jhei-R |
| | Problem, architecture, pipeline demo, findings, ethical reflection, next steps | | | |
| 10 | **Ethical reflection** | MEDIUM | Ethics criterion | Brynn |
| | Public data, scraping ethics, classification bias, responsible LLM use | | | |
| 11 | **Project folder structure** | MEDIUM | Organization | Jhei-R |
| | Reorganize into data/, notebooks/, reports/, ppt/ per rubric | | | |

---

## To Do -- Shared (Both Courses)

| # | Task | Priority | Serves | Assignee |
|---|------|----------|--------|----------|
| 12 | **Pay estimation prompt** | MEDIUM | Streamlit + HR | Steven |
| | Separate prompt for compensation with weighted math for blended roles | | | |
| 13 | **Validate against 10+ W&M positions** | HIGH | Both + HR | Everyone |
| | Find real postings on Workday, run through pipeline, compare expected vs. actual | | | |

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

## Team Domains (4 roles, each with immediate work)

Every domain has tasks that can start TODAY -- no waiting on anyone else.

### Domain 1: Infrastructure Lead
> GitHub, project structure, cloud deployment, CI/CD

| Task | Priority | Start Now? |
|------|----------|------------|
| #2 GitHub Projects kanban board (migrate from HTML) | HIGH | YES -- do this first |
| #11 Project folder restructure (data/, notebooks/, reports/, ppt/) | MEDIUM | YES |
| #7 Deploy to Google Cloud SQL (MySQL) | HIGH | YES -- migrate schema now, data later |
| #1 GitHub README (author bios, visuals, responsible AI) | HIGH | YES -- draft structure + bios |

### Domain 2: Research + Content Lead
> Research paper, responsible AI, ethical reflection, written content

| Task | Priority | Start Now? |
|------|----------|------------|
| #5 Research paper citation (<3 years, LLM classification or HR) | MEDIUM | YES -- start searching today |
| #6 Responsible AI section (bias, privacy, HITL) | MEDIUM | YES -- draft from architecture decisions |
| #10 Ethical reflection (scraping ethics, classification bias) | MEDIUM | YES -- overlap with #6, write both |
| #13 Validate against 10+ positions (your share: 2-3) | HIGH | YES -- use MVP prompt + Excel files |

### Domain 3: Design + Delivery Lead
> Poster, slide deck, visual design, presentation rehearsal

| Task | Priority | Start Now? |
|------|----------|------------|
| #4 Conference poster layout + template | HIGH | YES -- design layout, placeholder content |
| #9 Big Data slide deck structure | HIGH | YES -- outline all sections now |
| Presentation rehearsal plan | MEDIUM | YES -- draft who presents what |
| #13 Validate against 10+ positions (your share: 2-3) | HIGH | YES -- results feed into poster/deck |

### Domain 4: Technical Lead -- Steven
> ML pipeline, prompt engineering, LangChain PoC, Streamlit app

| Task | Priority | Status |
|------|----------|--------|
| ~~B1 LangChain multi-agent PoC (Assignment 5)~~ | HIGH | DONE (Apr 6) |
| ~~B2 skill.md + template files~~ | MEDIUM | DONE (Apr 6) |
| ~~B3 Design rationale report~~ | MEDIUM | DONE (Apr 6) |
| ~~A4 Feature engineering~~ | HIGH | DONE (Apr 6) |
| #12 Pay estimation prompt template | MEDIUM | Can draft alongside A4 |
| ~~A5 H2O AutoML training~~ | HIGH | DONE (Apr 6) |
| #3 Streamlit web app (agentic AI) | HIGH | After A5 (Anmol co-owns) |
| #7 Deploy to Google Cloud SQL | HIGH | Can start now |
| #8 Visualizations (SHAP, PDP, distributions) | HIGH | After A5 |
| #13 Validate against 10+ positions (your share: 2-3) | HIGH | Use MVP prompt now |

### Shared (Everyone)
| Task | Notes |
|------|-------|
| #13 Validate against 10+ positions | Each person tests 2-3 PDs through the MVP prompt |
| #14 Data dictionary | After validation -- any domain can contribute |
| #15 User guide / SOP | After validation -- Research + Content Lead drafts |
| #16 Validation report | After validation -- Technical Lead compiles |

---

## Timeline

```
Mar 30-31 (DONE)     A1 env setup, A2 Workday scrape, A3 label stripping. Docs updated.
Apr 1-5              Feature engineering (A4). Quick wins: research paper, folder restructure.
Apr 5-8              H2O AutoML training (A5). Set up H2O via Big Data lab process. Visualizations.
Apr 6 (DONE)         Assignment 5 submitted (B1 LangChain PoC + B2 skill.md + B3 report).
Apr 7-11             Streamlit app (#3). Position validation (#13). Cloud SQL (#7).
Apr 11-14            Polish: poster (#4), SHAP plots (#8), slide deck (#9).
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
