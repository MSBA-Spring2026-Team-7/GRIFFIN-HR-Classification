#!/usr/bin/env bash
# ============================================================
# GRIFFIN Project -- GitHub Issues + Project Board Setup
# ============================================================
# Prerequisites:
#   1. Install GitHub CLI: https://cli.github.com
#   2. Authenticate: gh auth login
#   3. Create a repo (or use existing): gh repo create GRIFFIN --public
#   4. cd into the repo directory
#   5. Run this script: bash github-issues-setup.sh
#
# What this does:
#   - Creates color-coded labels for courses, workstreams, and priorities
#   - Creates all project issues with descriptions and acceptance criteria
#   - Each issue gets appropriate labels
#   - Team members can then drag issues into a GitHub Project board
#
# After running:
#   1. Go to your repo on github.com
#   2. Click "Projects" tab > "New project" > "Board"
#   3. Add the repo as a source -- all issues appear automatically
#   4. Drag issues into Done / In Progress / To Do columns
# ============================================================

set -e

echo "=== Creating Labels ==="

# Course labels
gh label create "AI Course (TP3)"   --color "17a2b8" --description "BUAD 5742 deliverable (April 15 poster)" --force
gh label create "Big Data (5722)"   --color "8e44ad" --description "BUAD 5722 deliverable (April 17 deck)"   --force
gh label create "HR Handoff"        --color "27ae60" --description "Client deliverable for W&M HR"            --force
gh label create "Shared"            --color "e67e22" --description "Serves both courses"                      --force

# Workstream labels
gh label create "WS1: Data"         --color "e91e63" --description "Workstream 1: Data Collection"            --force
gh label create "WS2: Prompts"      --color "1565c0" --description "Workstream 2: Prompt Engineering"         --force
gh label create "WS3: App"          --color "f9a825" --description "Workstream 3: Application & Integration"  --force
gh label create "WS4: Validation"   --color "2e7d32" --description "Workstream 4: Validation & Documentation" --force

# Status labels
gh label create "blocked"           --color "6c757d" --description "Waiting on external dependency"           --force
gh label create "good first issue"  --color "7057ff" --description "Good for team members to pick up"         --force
gh label create "priority: high"    --color "d73a4a" --description "Must complete before deadline"             --force
gh label create "priority: medium"  --color "fbca04" --description "Important but not blocking"               --force

echo ""
echo "=== Creating Issues ==="

# -------------------------------------------------------
# Helper: create-and-close avoids race condition by
# capturing the issue number from the create output.
# -------------------------------------------------------
create_closed_issue() {
  local num
  num=$(gh issue create "$@" --json number -q '.number')
  gh issue close "$num"
  echo "  Created and closed #$num"
}

# -------------------------------------------------------
# DONE issues (create as closed so board history shows them)
# -------------------------------------------------------

create_closed_issue \
  --title "Scrape all 56 DHRM career groups" \
  --label "WS1: Data,Big Data (5722)" \
  --body "$(cat <<'EOF'
## Description
Scrape all 56 DHRM career group pages (50 HTML + 6 PDF) and cache raw responses in `raw_pages/`.

## Acceptance Criteria
- [x] 50 HTML pages fetched and cached
- [x] 6 PDF pages fetched and cached
- [x] 1-2 second delay between requests
- [x] All files stored in raw_pages/ for offline re-parsing

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Parse HTML career groups (50 pages)" \
  --label "WS1: Data,Big Data (5722)" \
  --body "$(cat <<'EOF'
## Description
Parse all 50 HTML career group pages using BeautifulSoup + regex into structured DataFrames matching the database schema.

## Acceptance Criteria
- [x] career_groups DataFrame populated for all 50 HTML groups
- [x] roles DataFrame with all compensable factors (complexity, results, accountability)
- [x] soc_codes DataFrame with group-level and role-level mappings
- [x] historical_titles DataFrame with class code, title, and grade

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Parse PDF career groups (6 pages)" \
  --label "WS1: Data,Big Data (5722)" \
  --body "$(cat <<'EOF'
## Description
Parse all 6 PDF career group pages using pdfplumber. Handles 3 format variants:
1. Embedded layout (factors inside header table as extra rows)
2. Split factor tables (factors split across 2-3 separate table elements)
3. Transitional format (no Code:/SOC: headers)

## Acceptance Criteria
- [x] All 6 PDF groups parsed with 100% role coverage
- [x] All compensable factors extracted for every role
- [x] SOC codes and historical titles captured
- [x] 24 PDF role summaries populated

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "FY26 DHRM salary structure (PDF parse)" \
  --label "WS1: Data,Shared" \
  --body "$(cat <<'EOF'
## Description
Parse the official FY26 DHRM salary structure PDF into the dhrm_pay_bands table.

## Acceptance Criteria
- [x] 9 pay bands with min/max salary values
- [x] Effective date captured (June 10, 2025)

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "W&M salary structure + DHRM-to-W&M crosswalk" \
  --label "WS1: Data,Shared" \
  --body "$(cat <<'EOF'
## Description
Build W&M pay grade tables (S01-S23 salaried, H01-H23 hourly) and the crosswalk mapping DHRM bands to W&M grades.

## Acceptance Criteria
- [x] 46 pay grades (23 S + 23 H) with min/midpoint/max
- [x] 9-row crosswalk table
- [x] Band 7 -> S18 validated against Assistant Controller example

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Database load + Excel export" \
  --label "WS1: Data,Big Data (5722),HR Handoff" \
  --body "$(cat <<'EOF'
## Description
Load all DataFrames to SQLite via sqlalchemy. Export 7 Excel files to hr_handoff/.

## Acceptance Criteria
- [x] 7 tables loaded: career_groups, roles, soc_codes, historical_titles, dhrm_pay_bands, wm_pay_grades, crosswalk
- [x] Verification queries passing (56 groups, 294 roles)
- [x] 7 .xlsx files in hr_handoff/

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Data validation (56 groups, 294 roles)" \
  --label "WS1: Data,Big Data (5722)" \
  --body "$(cat <<'EOF'
## Description
Validated 100% coverage: all 56 career groups, 294 roles, and all 4 compensable factors present for every role.

## Acceptance Criteria
- [x] 56 career groups accounted for
- [x] 294 roles with complexity, results, accountability, and role_summary
- [x] 666 SOC codes
- [x] 1,469 historical titles

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Database schema design (9 tables)" \
  --label "WS1: Data,Shared" \
  --body "$(cat <<'EOF'
## Description
Designed 9-table MySQL schema: 6 reference tables + 3 classification output tables. 4 pre-built views.

## Acceptance Criteria
- [x] SQL file with CREATE TABLE statements
- [x] Pre-built views: v_classification_lookup, v_title_search, v_career_group_summary, v_classification_report
- [x] data_source column for DHRM_PUBLIC vs PROPRIETARY tagging

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Project spec document (v3)" \
  --label "Shared" \
  --body "$(cat <<'EOF'
## Description
Full project specification: architecture, workstreams, deliverables checklist, validated example (Assistant Controller).

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Proof of Concept" \
  --label "Shared" \
  --body "$(cat <<'EOF'
## Description
Early prototype demonstrating classification logic end-to-end against the Assistant Controller example.

## Status: COMPLETE
EOF
)"

create_closed_issue \
  --title "Classification prompt template v1" \
  --label "WS2: Prompts,Shared" \
  --body "$(cat <<'EOF'
## Description
Draft classification prompt with blend logic, duty mapping, and explanation generation.

## Status: COMPLETE (v1 draft, iteration ongoing)
EOF
)"

# -------------------------------------------------------
# IN PROGRESS issues (open, not yet assignable to team)
# -------------------------------------------------------

echo ""
echo "--- In Progress Issues ---"

gh issue create \
  --title "URL refactoring in notebook" \
  --label "Big Data (5722),WS1: Data" \
  --body "$(cat <<'EOF'
## Description
Refactor HTML_SOURCES and PDF_SOURCES from full URLs to a static base URL + dynamic path dictionary with f-strings.

## Acceptance Criteria
- [ ] Base URL defined once
- [ ] No full URLs hardcoded in source dictionaries
- [ ] All 56 URLs still resolve correctly
- [ ] Notebook runs end-to-end

## Status: IN PROGRESS (Salva / Claude Code)
EOF
)"

gh issue create \
  --title "Notebook gap analysis vs. rubrics" \
  --label "Big Data (5722),AI Course (TP3)" \
  --body "$(cat <<'EOF'
## Description
Review the notebook against both course rubrics (Big Data: technical depth, visualization, ethics; AI: code demo, repo, poster) to identify gaps before the final push.

## Acceptance Criteria
- [ ] Gap list produced
- [ ] Each gap mapped to a rubric criterion
- [ ] Priority assigned to each gap

## Status: IN PROGRESS (Salva / Claude Code)
EOF
)"

# -------------------------------------------------------
# TO DO issues (open, assignable)
# -------------------------------------------------------

echo ""
echo "--- AI Course Issues ---"

gh issue create \
  --title "GitHub README with project documentation" \
  --label "AI Course (TP3),WS4: Validation,good first issue,priority: high" \
  --body "$(cat <<'EOF'
## Description
Create a comprehensive README for the GitHub repo per the TP3 rubric.

## Required Sections (from rubric)
- [ ] Nice visuals illustrating main concepts and business importance
- [ ] Author list with links to each member's GitHub profile page
- [ ] Each member's GitHub page has a proper readme profile with bio
- [ ] Project Scope (narrowly focused, specific)
- [ ] Project Details (logical organization, clear writeups)
- [ ] "What's Next?" section with future developments and concerns
- [ ] Responsible AI considerations
- [ ] Reference list with at least one research paper (< 3 years old)
- [ ] Do NOT list client identity without permission

## Rubric Points
- "Github repo is organized and covers everything required for the project effectively" (7%)
- References cited properly (1%)

## Tips
- Use the project spec (wm-hr-classification-project-prompt-v3.md) as source material
- Include an architecture diagram (the three-layer model)
- Keep it professional -- judges and faculty will read this
EOF
)"

gh issue create \
  --title "GitHub Projects kanban board (live)" \
  --label "AI Course (TP3),good first issue,priority: high" \
  --body "$(cat <<'EOF'
## Description
Create a GitHub Projects board with Done / In Progress / To Do columns. Migrate all issues to the board.

## Acceptance Criteria
- [ ] Project board created on the repo
- [ ] All issues added to the board
- [ ] Columns: Done, In Progress, To Do
- [ ] Board shows active use during semester (not just created last minute)

## Rubric Points
- "Github project kanban board is visually organized" (7%)

## How To
1. Go to repo > Projects tab > New project > Board
2. Add repo as data source
3. Drag closed issues to Done, open issues to To Do
4. As team works, move cards to In Progress
EOF
)"

gh issue create \
  --title "Streamlit web app with agentic AI" \
  --label "AI Course (TP3),WS3: App,priority: high" \
  --body "$(cat <<'EOF'
## Description
Build a Streamlit app where HR pastes a position description and gets:
1. Classification (career group, role, pay band)
2. Compensation recommendation (W&M pay grade, range)
3. Explanation narrative

Must demonstrate agentic AI design elements per rubric.

## Agentic Design Elements
The tool qualifies as agentic AI because it:
- **Reasons**: analyzes duty blocks against compensable factors
- **Acts**: maps duties to career groups, calculates weighted pay
- **Uses tools**: queries the DHRM database, applies blend threshold
- **Reflects**: generates explanation narratives with caveats and recommendations

## Acceptance Criteria
- [ ] Text input for position description paste
- [ ] LLM API call (Claude, Gemini, or Copilot) with structured prompt
- [ ] Classification output with duty-to-career-group mapping
- [ ] Pay recommendation with math shown
- [ ] Explanation narrative in HR-professional voice
- [ ] Deployed to a URL the team can demo live (Streamlit Cloud, GCP Cloud Run, etc.)

## Rubric Points
- "Website demo: Creative and thoughtful use of vibe coding" (7%)
- "Code demo: Technically challenging, logically sound, and thoughtfully put together" (7%)

## Dependencies
- Classification prompt template (v1 done, needs iteration)
- LLM API key (team decision: Claude vs Gemini vs other)
- Reference data (Excel files in hr_handoff/ or SQLite DB)
EOF
)"

gh issue create \
  --title "Conference poster for April 15" \
  --label "AI Course (TP3),WS4: Validation,priority: high" \
  --body "$(cat <<'EOF'
## Description
Create a conference-style poster for the April 15 presentation.

## Required Content
- [ ] Problem statement
- [ ] Architecture / approach diagram
- [ ] Demo screenshots (Streamlit app + code)
- [ ] Key findings / results
- [ ] Research paper reference
- [ ] Responsible AI considerations
- [ ] Team members

## Rubric Points
- "Poster is visually effective and covers everything that's required for the project" (7%)

## Presentation Rubric (verbal)
- Problem statement clearly articulated (1%)
- Business opportunities and challenges explained (1%)
- Technical components explained clearly for non-technical audience (1%)
- Judges learned significant new AI knowledge (1%)
- Creativity in approach (1%)
- Effective team collaboration, all members engaged in Q&A (1%)

## Notes
- Three awards given: Agentic Design Excellence, Innovation, Communication Excellence
- Keep code demo SIMPLE -- illustrate essential concept, not full walkthrough
EOF
)"

gh issue create \
  --title "Find and cite research paper (< 3 years old)" \
  --label "AI Course (TP3),WS4: Validation,good first issue,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Find at least one relevant, high-quality research paper published within the last 3 years.

## Requirements
- [ ] Must be a research paper (NOT news articles, Medium, blog, library docs, or LinkedIn)
- [ ] Less than 3 years old
- [ ] Relevant to: LLM-based classification, agentic AI, HR automation, or NLP for job matching
- [ ] Must be discussed verbally during poster presentation
- [ ] Must appear on the poster
- [ ] Must be in the README reference list

## Rubric Points
- "Research paper is well chosen and well discussed verbally and on the poster" (7%)

## Search Suggestions
- Google Scholar, IEEE Xplore, ACM Digital Library, arXiv
- Keywords: "LLM job classification", "agentic AI enterprise", "automated position classification", "NLP human resources"
EOF
)"

gh issue create \
  --title "Responsible AI considerations" \
  --label "AI Course (TP3),Shared,good first issue,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Document responsible AI considerations for the project. Required in both README and poster.

## Topics to Address
- [ ] Bias risks: LLM may perpetuate historical classification biases
- [ ] Human-in-the-loop: AI recommends, HR decides (never autonomous)
- [ ] Data privacy: no PII in prompts, public DHRM data only
- [ ] Explainability: every classification includes narrative explanation
- [ ] Transparency: show duty mapping and pay math, not just results
- [ ] Configurable thresholds: HR controls the blend percentage
- [ ] AI-agnostic design: not locked to any vendor

## Where This Appears
- README section
- Poster section
- Verbal discussion during Q&A
EOF
)"

echo ""
echo "--- Big Data Course Issues ---"

gh issue create \
  --title "Deploy database to Google Cloud SQL" \
  --label "Big Data (5722),WS3: App,priority: high" \
  --body "$(cat <<'EOF'
## Description
Migrate the SQLite database to Google Cloud SQL (MySQL) to demonstrate GCP tool usage per course requirements.

## Acceptance Criteria
- [ ] Cloud SQL instance created (MySQL)
- [ ] All 7 tables loaded
- [ ] Notebook connection string updated (credentials masked)
- [ ] Verification queries pass against Cloud SQL
- [ ] Screenshots/evidence of GCP console for presentation

## Rubric Context
- "Technical Depth: Appropriate use of big data tools (cloud services)" is a key criterion
- Must leverage GCP tools covered in class

## How To
1. GCP Console > Cloud SQL > Create Instance (MySQL)
2. Create database and user
3. Update sqlalchemy connection string: mysql+pymysql://user:pass@IP/db
4. Re-run load cells against Cloud SQL
5. Mask credentials in notebook (use environment variables)
EOF
)"

gh issue create \
  --title "Add visualizations to notebook" \
  --label "Big Data (5722),WS3: App,good first issue,priority: high" \
  --body "$(cat <<'EOF'
## Description
Add data visualizations to the Jupyter notebook using matplotlib, seaborn, or plotly.

## Suggested Charts
- [ ] Bar chart: number of roles per occupational family (7 families)
- [ ] Heatmap: pay band distribution across career groups
- [ ] Horizontal bar: career group sizes (roles per group)
- [ ] Pie/donut: HTML vs PDF source distribution
- [ ] Box plot: pay band ranges by family
- [ ] Table: SOC code coverage statistics

## Rubric Context
- "Visualization: Create relevant charts, dashboards, or plots to highlight key observations"
- Use course tools: matplotlib, seaborn, Plotly, or Streamlit

## Notes
- Each chart needs a markdown cell explaining what it shows and why it matters
- Keep it clean and professional -- this notebook IS the deliverable
EOF
)"

gh issue create \
  --title "Slide deck for Big Data presentation (April 17)" \
  --label "Big Data (5722),WS4: Validation,priority: high" \
  --body "$(cat <<'EOF'
## Description
Create a slide deck for the April 17 Big Data course presentation.

## Required Sections (from syllabus)
- [ ] Problem statement and business question
- [ ] Data source justification
- [ ] Technology and architecture (pipeline diagram)
- [ ] Data processing and analysis approach
- [ ] Visualizations and key findings
- [ ] Ethical reflection
- [ ] Next steps and scalability

## Rubric Criteria
- Problem Relevance
- Technical Depth (big data tools, analytical techniques)
- Demonstrates understanding of course material
- Code quality and documentation
- Presentation quality
EOF
)"

gh issue create \
  --title "Ethical reflection (Big Data)" \
  --label "Big Data (5722),WS4: Validation,good first issue,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Write an ethical reflection on data practices for the Big Data course deliverable.

## Topics
- [ ] Data is public (DHRM website, no PII)
- [ ] Ethical scraping: rate limiting, robots.txt compliance
- [ ] Bias in DHRM classification taxonomy (historical, structural)
- [ ] Responsible LLM use: disclosure, not replacing human judgment
- [ ] Privacy if HR adds proprietary data later (schema supports data_source tagging)

## Where This Appears
- Notebook markdown cell
- Slide deck section
- "Ethical Reflection" rubric criterion
EOF
)"

gh issue create \
  --title "Organize project folder structure" \
  --label "Big Data (5722),good first issue,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Organize the project into the folder structure required by the Big Data rubric.

## Target Structure
```
data/           -- raw_pages/, hr_handoff/, output_csv/
notebooks/      -- griffin_dhrm_pipeline.ipynb
reports/        -- validation report, data dictionary
ppt/            -- slide deck
docs/           -- project spec, CLAUDE.md, kanban
```

## Acceptance Criteria
- [ ] All files in correct folders
- [ ] No orphan files in root
- [ ] README explains folder structure
EOF
)"

echo ""
echo "--- Shared / Cross-Course Issues ---"

gh issue create \
  --title "Refine classification prompt (v2)" \
  --label "WS2: Prompts,Shared,priority: high" \
  --body "$(cat <<'EOF'
## Description
Iterate the v1 classification prompt. Test against the Assistant Controller example and additional positions.

## Acceptance Criteria
- [ ] Prompt produces correct classification for Assistant Controller (19036, Band 7, S18)
- [ ] Blend threshold logic works (30% default)
- [ ] Explanation narrative reads like an HR professional wrote it
- [ ] Works with at least 2 different LLMs (Claude + one other)

## Test Case: Assistant Controller
- Expected: Financial Services Manager III (19036, Band 7)
- Expected: Single classification (secondary < 30%)
- Expected: W&M Grade S18 ($91,133 - $210,964)
- Expected: Historical title match "Assistant Comptroller" (class code 23136)
EOF
)"

gh issue create \
  --title "Pay estimation prompt template" \
  --label "WS2: Prompts,Shared,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Create a separate prompt template for compensation estimation. Takes classification result + salary data, produces weighted pay recommendation.

## Acceptance Criteria
- [ ] Single classification: full pay band range (min/midpoint/max)
- [ ] Blended classification: weighted average with math shown
- [ ] References both DHRM band and W&M grade
- [ ] Configurable blend threshold
- [ ] Works with any LLM (Copilot, Gemini, Claude)
EOF
)"

gh issue create \
  --title "Validate against 10+ real W&M positions" \
  --label "WS4: Validation,Shared,priority: high" \
  --body "$(cat <<'EOF'
## Description
Find 10+ real W&M job postings on Workday and run them through the classification pipeline.

## Acceptance Criteria
- [ ] 10+ position descriptions collected from W&M Workday postings
- [ ] Each run through classification prompt
- [ ] Expected vs. actual classification compared
- [ ] Accuracy metrics documented
- [ ] Edge cases identified (blended roles, unusual positions)
- [ ] Results feed into validation report

## Where to Find Postings
- https://williammary.wd12.myworkdayjobs.com
- Mix of families: admin, IT, facilities, academic support, etc.
EOF
)"

gh issue create \
  --title "Data dictionary for HR" \
  --label "HR Handoff,WS4: Validation,good first issue,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Document every field in every Excel file for HR. Non-technical audience.

## Files to Document
- career_groups.xlsx (11 columns)
- roles.xlsx (11 columns)
- soc_codes.xlsx (6 columns)
- historical_titles.xlsx (5 columns)
- dhrm_pay_bands.xlsx
- wm_pay_grades.xlsx
- crosswalk.xlsx

## For Each Field
- [ ] Field name
- [ ] Description (plain English)
- [ ] Data type
- [ ] Source (DHRM website, W&M website, derived)
- [ ] Update frequency (annual, as needed, static)

## Also Include
- [ ] Instructions for how HR adds their proprietary data
- [ ] Which files, which columns, what format
EOF
)"

gh issue create \
  --title "User guide / SOP for HR" \
  --label "HR Handoff,WS4: Validation,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Step-by-step guide for HR to use the classification tool. Must be usable by a non-technical HR professional on day one.

## Sections
- [ ] How to classify a position (full workflow)
- [ ] How to use prompts with Copilot/Gemini
- [ ] How to interpret results (single vs. blended)
- [ ] How to adjust the blend threshold
- [ ] How to update data files when salary structures change
- [ ] Troubleshooting common edge cases

## Quality Test
"Could an HR professional with no technical background use this on day one?"
If no, rewrite it.
EOF
)"

gh issue create \
  --title "Validation report with test results" \
  --label "HR Handoff,WS4: Validation,priority: medium" \
  --body "$(cat <<'EOF'
## Description
Document test results from running the classification pipeline against known W&M positions.

## Contents
- [ ] Test methodology
- [ ] Results table: position, expected classification, actual, match (Y/N)
- [ ] Accuracy metrics
- [ ] Edge cases and how they were handled
- [ ] Recommendations for ongoing validation

## Dependencies
- Depends on "Validate against 10+ real W&M positions" issue
EOF
)"

echo ""
echo "--- Blocked Issues ---"

gh issue create \
  --title "[BLOCKED] Client feedback on data files" \
  --label "HR Handoff,blocked" \
  --body "$(cat <<'EOF'
## Description
Awaiting feedback from W&M HR on the Excel data files sent to them.

## What We Need
- Confirmation that taxonomy structure meets their needs
- Feedback on crosswalk mapping
- Guidance on proprietary data column alignment
- Any corrections to career group or role data

## Status
No response from client as of March 27, 2026. Continue building around this -- the data is from the official DHRM source so it should be accurate.
EOF
)"

gh issue create \
  --title "[BLOCKED] Proprietary data integration" \
  --label "HR Handoff,blocked" \
  --body "$(cat <<'EOF'
## Description
HR has internal position data (PDF/Excel) they cannot share. The database schema is designed to accept it (data_source column: DHRM_PUBLIC vs PROPRIETARY), but we need their confirmation on column structure.

## Depends On
- Client feedback on data files

## Workaround
Continue with public DHRM data only. The schema is ready for proprietary data whenever HR provides it.
EOF
)"

gh issue create \
  --title "[BLOCKED] LLM API selection for Streamlit app" \
  --label "AI Course (TP3),WS3: App,blocked" \
  --body "$(cat <<'EOF'
## Description
Team needs to decide which LLM API to use for the Streamlit app demo.

## Options
- **Claude API**: Best prompt quality, team has experience, costs money
- **Gemini API**: Free tier available, HR already has access to Gemini
- **OpenAI API**: Widely known, costs money
- **Local (Ollama)**: Free, no API key, but quality varies

## Decision Needed By
April 10 (5 days before poster presentation)

## Recommendation
Pick one primary + test prompts on a second as backup. The tool is AI-agnostic by design so the choice is about demo quality, not architecture.
EOF
)"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Created labels and issues. Next steps:"
echo "  1. Go to https://github.com/YOUR-ORG/GRIFFIN/projects"
echo "  2. Create a new Board project"
echo "  3. Add this repo as a data source"
echo "  4. All issues will appear -- drag to columns"
echo "  5. Assign team members to open issues"
echo ""
echo "Quick commands:"
echo "  gh issue list                    # see all issues"
echo "  gh issue list --label 'AI Course (TP3)' # filter by course"
echo "  gh issue list --state open       # see what needs doing"
echo "  gh issue edit 12 --add-assignee @teammate  # assign someone"
