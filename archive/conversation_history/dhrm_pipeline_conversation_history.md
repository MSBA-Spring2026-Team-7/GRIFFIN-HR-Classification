# GRIFFIN DHRM Pipeline -- AI Use & Orchestration Supplement

**Steven Alvarado** | BUAD 5722: Big Data & Cloud Analytics | April 2026

---

## Purpose of This Document

This supplement explains how I used Claude Code (an AI coding assistant) to build the GRIFFIN DHRM pipeline notebook, what decisions I made and why, how I verified the work at each stage, and what I learned. The notebook itself is the deliverable; this document shows the thinking behind it.

---

## Tool Used

**Claude Code** (Anthropic, Opus 4.6 model with 1M token context window). Claude Code is a terminal-based AI assistant that can read files, write code, execute commands, and dispatch sub-tasks to specialized agents. It does not autonomously decide what to build -- it requires human direction for every architectural and process decision.

---

## The Work Spanned Three Sessions

| Session | Focus | Process Used | Outcome |
|---------|-------|-------------|---------|
| 1 (this conversation) | Design + HTML parsers + scaling | Subagent-driven development | 50 HTML pages parsing, 21-cell notebook |
| 2 | PDF parser + integration + full pipeline | CQM Full Three-Phase | 56 career groups, 294 roles, 28-cell notebook |
| 3 | Parser fix for 39 broken pages + salary structures + HR export | CQM Full Three-Phase | 100% field coverage, 36-cell final notebook |

---

## Session 1: Design & HTML Parsers

### I set the constraints before any code was written

Before touching code, I had Claude read the full project spec (`GRIFFIN_CLAUDE_MD.md`) which I wrote to define:
- The exact database schema (6 tables, specific column types)
- Which Python libraries were allowed (only course-approved tools)
- All 56 source URLs (50 HTML + 6 PDF)
- The expected output for Financial Services (#19030) as a validation reference
- The requirement that every notebook cell include professor-readable markdown

I also reviewed which Claude Code plugins and skills were available, and explicitly selected which ones to use vs. skip.

### I chose the architecture from multiple options

Claude presented three approaches:
- **Approach A:** One big function that parses the entire page
- **Approach B:** Five modular functions, each parsing one section of the HTML
- **Approach C:** A configuration-driven generic parser

I chose **Approach B** because the DHRM pages have five distinct sections (header, role matrix, role descriptions, SOC codes, history), and a modular design means I can debug one section at a time when pages have formatting variations. This turned out to be the right call -- when we scaled to all 50 pages, the role matrix parser needed fixes while the other four worked fine.

### I insisted on iterative development

When Claude proposed building all parsers and running them against all 56 pages at once, I redirected: **"Let's start with a small sample to test and then go for the rest instead of trying to do everything everywhere all at once."**

This became the four-phase strategy:
1. Build and validate parsers against Financial Services only (known reference data)
2. Scale to all 50 HTML pages, fix edge cases
3. Build a separate PDF parser for the 6 PDF career groups
4. Full pipeline run with validation and database load

### I caught issues Claude missed

| Issue | How I caught it | Fix |
|-------|----------------|-----|
| Missing spaces in extracted text | Reviewed sample output in Phase 1 | Changed `get_text(strip=True)` to `get_text(separator=' ')` |
| Source HTML typo (wrong role code) | Compared parser output to schema spec | Added name-based matching as fallback |
| URL hardcoding in first draft | Recognized it violated DRY principle from class | Refactored to base URL + suffix pattern |

The URL hardcoding example is documented in the notebook itself (Cell 3, "Thought Process"). Claude's first version listed all 50 URLs as complete strings. I recognized this was inflexible and directed the refactoring to use a base URL with path suffixes, following the in-class principle of programmatic thinking over tactical repetition.

### I pivoted the process mid-stream

After scaling to 50 HTML pages, edge cases surfaced reactively (9 pages had different table structures, some used en-dashes instead of hyphens). I concluded that the ad-hoc testing approach was slower than structured quality control. I directed Claude to use **CQM orchestration** (a three-phase quality framework) for all remaining work. This is recorded in Claude's memory system as a learned preference.

**Session 1 result:** 50 HTML pages parsing (50 career groups, 259 roles, 581 SOC codes, 1,108 historical titles). All validation checks passing.

---

## Session 2: PDF Parser & Full Pipeline (CQM-Orchestrated)

After Session 1, I switched to CQM (Construction Quality Management) orchestration. CQM is a three-phase quality framework:
- **Preparatory Phase:** Archive existing state, verify inputs, define acceptance criteria, identify risks
- **Initial Phase:** Build and test on a small segment, get independent QC inspection
- **Follow-up Phase:** Scale production with QC checkpoints at 25/50/75/100%

### Preparatory Phase

The CQM Preparatory Phase archived the 21-cell notebook, verified all 56 source files existed (including downloading the 6 PDFs), analyzed the PDF structures, and froze 24 acceptance criteria across 2 work packages:
- **D-001 (PDF Parser):** 14 criteria covering functional, structural, content, and preservation requirements
- **D-002 (Full Pipeline Integration):** 10 criteria covering end-to-end execution

The PDF structure analysis revealed that all 6 PDFs followed a similar layout to the HTML pages but with text-position-based parsing instead of DOM-based parsing.

### Initial Phase

A Superintendent agent built the `parse_pdf_page()` function using pdfplumber. Test results: 35 roles, 85 SOC codes, 171 historical titles. A separate QC agent independently verified the output against the acceptance criteria -- all 12 verifiable criteria passed.

### Integration & Full Pipeline

The PDF parser was integrated into the notebook. The full pipeline ran across all 56 sources: **56 career groups, 294 roles, 666 SOC codes, 1,279 historical titles, 0 errors.**

### Pre-Final QC caught a structural issue

A fresh QC agent (with no prior context) inspected the notebook and found that code cells 7-11 lacked individual markdown cells. This violated the "professor-readable" requirement. Five markdown cells were added explaining each parser function. After re-execution, all counts remained unchanged.

**Session 2 result:** 28-cell notebook with full PDF support and all 56 career groups.

---

## Session 3: Parser Fix & Completions (CQM-Orchestrated)

### The problem: 39 of 56 pages had incomplete role descriptions

When I ran the full pipeline, 39 career group pages returned NULL for complexity, results, and accountability fields. The parsers from Session 1 assumed a specific HTML layout that only 17 pages actually followed.

### Diagnostic phase identified 3 root causes

A diagnostic agent examined the failing pages and identified three distinct HTML layout variants:

1. **Embedded Layout (13 groups):** Role descriptions and compensable factors were nested *inside* the header table as additional rows, not as separate sibling elements after it
2. **Split Factor Tables (8+ groups):** Each compensable factor (Complexity, Results, Accountability) was in its own separate table rather than all three in one table
3. **Transitional Format (1 group, 39010):** No "Code:" or "SOC:" headers at all -- completely different structure

### Acceptance criteria included regression protection

The CQM process defined 10 criteria, including 2 specifically for regression:
- **R-001:** The 17 career groups that already parsed correctly must produce identical output after the fix
- **R-002:** Total role count must remain 294

This is critical -- fixing broken parsers must not break working ones. The archived original served as the regression baseline.

### The fix: a 723-line parser replacing the 122-line original

The new `parse_role_descriptions()` function handles all three layout variants with a multi-strategy approach. It tries embedded layout first, then split factor tables, then the standard sibling layout. Each strategy uses different heuristics to locate the compensable factor text.

**Result after fix:** 294/294 roles with all 4 description fields populated (100% coverage). 17 baseline groups produced identical output to the archived original (zero regression).

### I directed additional scope: salary structures and HR handoff

After the parser was fixed, I directed three additional features based on the project requirements:
- **DHRM salary structure table** (FY26 pay bands with min/max salaries, parsed from PDF)
- **W&M university salary structure** (46 pay grades: S01-S23 salaried + H01-H23 hourly)
- **DHRM-to-W&M crosswalk** (maps state pay bands to university grades by salary range overlap)
- **Excel export** (7 .xlsx files in hr_handoff/ for non-technical HR staff)

The crosswalk initially used midpoint matching (wrong -- gave S19 for Band 7). I validated against a known example from the project spec (Assistant Controller, Band 7 should map to S18) and directed the switch to range-containment matching.

**Session 3 result:** 36-cell notebook (later 37 after a final thought-process cell). Final pipeline: 56 career groups, 294 roles, 666 SOC codes, 1,469 historical titles, 9 pay bands, 46 W&M grades, 9 crosswalk mappings, 7 Excel files.

---

## How I Verified the Work

### Reference Data Validation
The project spec defines expected counts for Financial Services (#19030): 1 career group, 7 roles, 59 historical titles, 12 SOC codes. Every parser was tested against these exact numbers before scaling.

### Regression Testing
After the Session 3 parser rewrite, I required that the 17 previously-working career groups produce identical output to the archived pre-modification version. This was verified by SHA-256 hash comparison.

### Independent QC Agents
In the CQM sessions, QC agents operated independently from the builder agents. The QC agent read the code and output without seeing the builder's design notes or reasoning. This caught the missing markdown cells issue in Session 2's pre-final review.

### Manual Validation
I validated the crosswalk output against a known real-world example (Assistant Controller, Band 7 = S18). When the initial algorithm produced S19, I caught the error and directed the fix before it went into the notebook.

---

## Key Decisions Summary

| Decision | Rationale |
|----------|-----------|
| Section-based parsers (Approach B) | Maps to HTML structure, easier to debug per-section |
| Iterative development (test one, then scale) | Catches parser bugs before they multiply |
| Financial Services as reference case | Has known expected counts to validate against |
| Switch from ad-hoc to CQM orchestration | Edge cases proved structured QC is worth the overhead |
| Regression protection in parser rewrite | Fixing 39 broken pages must not break 17 working ones |
| Range-containment for crosswalk | Midpoint matching gave wrong results, validated against real example |
| Cache raw HTML/PDF before parsing | Decouples scraping rate limit from parser iteration speed |
| 1.5s delay between requests | Respectful rate limiting for government servers |
| CSV fallback for DB load | Ensures notebook runs on any machine without MySQL |
| Excel export for HR handoff | Non-technical stakeholders need files they can open in Excel |

---

## What I Learned

### About Web Scraping
- Government websites generated from Microsoft Word produce HTML without CSS classes or semantic structure. All parsing must be positional and tag-based, making it fragile to layout variations.
- The same government website can have *three different HTML layouts* across its pages (embedded, split, standard). You cannot assume consistency even within one domain.
- Even official state government pages have data entry errors (wrong role codes, inconsistent punctuation). Parsers need fallback strategies.
- Caching raw responses before parsing is essential -- it decouples the scraping rate limit from parser development iteration speed.

### About AI-Assisted Development
- **AI is execution, not decision-making.** Every architecture choice, process pivot, and quality judgment came from me. Claude wrote the code, but it wrote what I told it to write, in the order I specified, validated against criteria I defined.
- **Iterative beats monolithic.** When I let Claude run the full pipeline at once, edge cases piled up. When I forced single-page testing first, issues were isolated and fixable.
- **Review the output, not just the code.** I caught the text spacing bug by reading the extracted data, not by reading the parser source code. The code looked correct -- the output proved it wasn't.
- **Quality processes scale better than reactive debugging.** Switching from ad-hoc testing to CQM orchestration produced cleaner results with fewer iterations. The Preparatory Phase catches problems before code is written.
- **Regression testing is non-negotiable for rewrites.** The Session 3 parser rewrite was 6x longer than the original. Without explicit regression criteria, it would have been easy to break the 17 working pages while fixing the 39 broken ones.

### About Course Tools
- **BeautifulSoup** handles DOM traversal well but `get_text()` behavior with nested `<font>` tags is not intuitive -- the `separator` parameter is critical for Word-generated HTML.
- **regex** was essential for extracting structured data (codes, band ranges, dates) from messy narrative text embedded in styled HTML.
- **pandas DataFrames** provided the validation layer -- pattern checks, null detection, and referential integrity are natural DataFrame operations.
- **pdfplumber** requires a fundamentally different parsing strategy than HTML. PDF parsing is text-position-based, not DOM-based, which makes it more fragile and harder to generalize across documents.
- **sqlalchemy** with a CSV fallback made the notebook portable -- it runs on any machine regardless of database availability.

---

## Final Pipeline Statistics

| Table | Records |
|-------|---------|
| career_groups | 56 |
| roles | 294 (100% factor coverage) |
| soc_codes | 666 |
| historical_titles | 1,469 |
| dhrm_pay_bands | 9 |
| wm_pay_grades | 46 |
| pay_band_crosswalk | 9 |
| **Excel files exported** | **7** |

---

## Disclosure

This notebook was built with AI assistance from Claude Code across three supervised sessions. All architectural decisions, quality judgments, process direction, and validation criteria were mine. Claude Code wrote the implementation code, executed the scraping pipeline, and performed validation checks under my supervision. I reviewed all outputs at each phase before approving progression to the next. The CQM quality framework ensured independent verification at every stage -- the agent that built something never certified its own quality.
