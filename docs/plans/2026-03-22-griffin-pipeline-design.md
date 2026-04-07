# GRIFFIN DHRM Pipeline - Design Document

**Date:** 2026-03-22
**Deliverable:** `griffin_dhrm_pipeline.ipynb` -- Jupyter notebook for BUAD 5722

## Overview

A Jupyter notebook that scrapes all ~56 DHRM career group pages, parses them into structured data, and loads them into a MySQL database. The notebook IS the deliverable -- every cell has markdown explanations demonstrating mastery of course tools.

## Architecture: Section-Based Parsers (Approach B)

Rather than one monolithic parser, we use 5 focused parsing functions that each handle one logical section of the DHRM HTML template. An orchestrator calls them in sequence and assembles the results.

### Data Flow

```
Source URLs (hardcoded list of 56 tuples)
    |
    v
[Scrape & Cache] -- raw HTML/PDF saved to raw_pages/html/ and raw_pages/pdf/
    |
    v
[Section Parsers] -- 5 functions extract structured dicts
    |
    v
[Assemble DataFrames] -- 4 DataFrames (career_groups, roles, historical_titles, soc_codes)
    |
    v
[Validate] -- pattern checks, count checks vs Financial Services reference
    |
    v
[Load to MySQL] -- sqlalchemy + pymysql, CSV fallback if connection fails
    |
    v
[Verify via SQL] -- SELECT queries confirming loaded data
```

## Course Tools Used

| Step | Tool | Course Week |
|---|---|---|
| Web scraping | BeautifulSoup | Week 5 |
| Text parsing | regex (re module) | Week 6 |
| Data structuring | pandas DataFrames | Week 2-3 |
| Database connection | sqlalchemy + pymysql | Week 2-3 |
| Database target | MySQL (local, production on Cloud SQL) | Week 2-3 |
| HTTP requests | requests library | Week 4 |
| PDF parsing | pdfplumber | Week 5 |

## Section Parsers

### `parse_header(soup)` -> dict
Extracts career_group_name, career_group_code, occupational_family, pay_band_min, pay_band_max, occ_family_code, and concept_of_work from the page header. Uses BeautifulSoup DOM traversal + regex for code/band extraction.

### `parse_role_matrix(soup)` -> list of dicts
Parses the role matrix table (PAY BAND | PRACTITIONER | CODE | MANAGEMENT | CODE). Returns list of {role_name, role_code, pay_band, track} dicts.

### `parse_role_descriptions(soup, role_list)` -> list of dicts
Takes role list from matrix parser, enriches with role_summary and three compensable factors (complexity, results, accountability). Finds each role's section by heading, extracts text between COMPLEXITY/RESULTS/ACCOUNTABILITY subheadings.

### `parse_soc_codes(soup, career_group_code)` -> list of dicts
Finds "Statistical Reporting" section. Extracts group-level SOC codes (role_code=NULL) and role-level SOC codes from individual role headers. Regex pattern: `r'\d{2}-\d{4}'`.

### `parse_historical_titles(soup)` -> list of dicts
Finds "History" section. Parses CLASS CODE | CLASS TITLE | GRADE tables under each role subheading. Associates rows with role_code via role name matching.

### `parse_pdf_page(filepath, career_group_info)` -> same outputs
Separate function for 6 PDF career groups using pdfplumber text extraction + similar regex patterns.

## Development Strategy (Phased)

**Phase 1: Single-page prototype** -- Build and test all parsers against Financial Services (#19030). Validate against known reference counts: 1 group, 7 roles, 59 historical titles, 12 SOC codes.

**Phase 2: Scale to all HTML** -- Run across all 50 HTML pages. Review summary counts, fix edge cases.

**Phase 3: PDF pages** -- Build PDF parser, test on one, then run all 6.

**Phase 4: Validate, Load, Verify** -- Full validation, DB load (MySQL primary, CSV fallback), verification queries.

## Error Handling

- HTTP failures: log and skip, don't crash the loop
- Missing sections: return empty list/dict with warning, not exception
- Post-scrape summary of success/failure counts
- Validation checks: code patterns, band ranges, FK integrity, required field completeness

## Database Connection

- Primary: local MySQL via sqlalchemy (`mysql+pymysql://user:pass@localhost/wm_hr_classification`)
- Fallback: export DataFrames to CSV if MySQL connection fails
- Production target: Google Cloud SQL (same schema, different connection string)
- Load strategy: `df.to_sql()` with `if_exists='append'`

## Notebook Cell Structure

1. **Setup and Libraries** -- imports + markdown explaining each tool
2. **Define Source URLs** -- hardcoded list + markdown on DHRM data structure
3. **HTML Parsing Functions** -- 5 section parsers + orchestrator + markdown on strategy
4. **PDF Parsing Function** -- pdfplumber-based parser + markdown on PDF differences
5. **Execute the Scrape** -- loop with caching, delays, progress tracking + markdown on ethics
6. **Data Validation** -- pattern checks, count checks, summary stats + markdown on QA
7. **Load to Database** -- MySQL connection + CSV fallback + markdown on connection approach
8. **Verification Queries** -- SQL queries confirming correct load + markdown on each query

## Key Constraints

- Never use em-dashes in any content
- Add 1-2 second delays between HTTP requests
- Cache raw HTML/PDF to disk before parsing
- All code must use course-approved tools (no novel libraries)
- Every cell needs professor-readable markdown explanations
