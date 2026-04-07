# GRIFFIN DHRM Pipeline - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Jupyter notebook that scrapes 56 DHRM career group pages, parses them into 4 structured DataFrames, and loads them into MySQL (with CSV fallback).

**Architecture:** Section-based parsers (5 functions for HTML, 1 for PDF) extract structured dicts from cached raw pages. An orchestrator loops all URLs, calling the appropriate parser, and assembles results into DataFrames. Phased development: validate against Financial Services (#19030) first, then scale.

**Tech Stack:** Python, Jupyter, requests, BeautifulSoup4, re, pandas, pdfplumber, sqlalchemy, pymysql

---

## Task 1: Create Notebook with Setup Cell

**Files:**
- Create: `griffin_dhrm_pipeline.ipynb`

**Step 1: Create the notebook with Cell 1 (markdown + code)**

Markdown cell explaining the project, then code cell with imports:

```python
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from sqlalchemy import create_engine
import pdfplumber
import os
import time
```

Markdown should explain:
- What GRIFFIN is (DHRM career group data pipeline)
- What each library does and which course week it maps to
- The deliverable: 4 tables loaded into MySQL

**Step 2: Verify the cell runs**

Run the cell. Expected: no errors. If pdfplumber is not installed, run `pip install pdfplumber` first.

---

## Task 2: Define Source URLs and Constants

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 2)

**Step 1: Add markdown cell**

Explain the DHRM data structure: 7 occupational families, ~56 career groups, 50 HTML pages + 6 PDF pages. Explain why they are separate formats.

**Step 2: Add code cell with source URL definitions**

```python
# Each tuple: (career_group_code, career_group_name, occupational_family, url, source_format)
HTML_SOURCES = [
    ("19010", "Administration and Office Support", "Administrative Services",
     "https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/AdminOfficeSupport19010.htm", "html"),
    # ... all 50 HTML sources from GRIFFIN_CLAUDE_MD.md ...
]

PDF_SOURCES = [
    ("59010", "Agricultural Services", "Natural Resources and Applied Science",
     "https://www.dhrm.virginia.gov/docs/default-source/compensationdocuments/agricultural-services-cgd-final44306F8E3605.pdf", "pdf"),
    # ... all 6 PDF sources from GRIFFIN_CLAUDE_MD.md ...
]

ALL_SOURCES = HTML_SOURCES + PDF_SOURCES

# Cache directories
RAW_HTML_DIR = "raw_pages/html"
RAW_PDF_DIR = "raw_pages/pdf"
os.makedirs(RAW_HTML_DIR, exist_ok=True)
os.makedirs(RAW_PDF_DIR, exist_ok=True)

# For Phase 1 testing: just Financial Services
TEST_SOURCES = [
    ("19030", "Financial Services", "Administrative Services",
     "https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/FinancialServices19030.htm", "html"),
]
```

The full URL list comes from `GRIFFIN_CLAUDE_MD.md` lines 94-153. Copy all entries exactly.

**Step 3: Run the cell**

Expected: directories created, no errors.

---

## Task 3: Build the Scrape-and-Cache Function

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 3a)

**Step 1: Add markdown cell**

Explain the caching strategy: save raw HTML/PDF to disk on first fetch, skip re-downloading on subsequent runs. Explain rate limiting (1-2 second delay) and ethical scraping.

**Step 2: Add code cell with fetch function**

```python
def fetch_and_cache(url, source_format, career_group_code):
    """Fetch a DHRM page and cache it locally. Returns the cached filepath."""
    if source_format == "html":
        cache_dir = RAW_HTML_DIR
        filename = f"{career_group_code}.htm"
    else:
        cache_dir = RAW_PDF_DIR
        filename = f"{career_group_code}.pdf"

    filepath = os.path.join(cache_dir, filename)

    if os.path.exists(filepath):
        print(f"  [CACHED] {career_group_code}")
        return filepath

    print(f"  [FETCHING] {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    write_mode = "w" if source_format == "html" else "wb"
    content = response.text if source_format == "html" else response.content

    with open(filepath, write_mode, encoding="utf-8" if source_format == "html" else None) as f:
        f.write(content)

    time.sleep(1.5)  # Rate limiting - be respectful to DHRM servers
    return filepath
```

**Step 3: Test with Financial Services**

```python
# Quick test
test_path = fetch_and_cache(TEST_SOURCES[0][3], "html", "19030")
print(f"Cached to: {test_path}")
print(f"File size: {os.path.getsize(test_path)} bytes")
```

Expected: file downloaded and cached, file size > 0.

---

## Task 4: Build parse_header()

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 3b)

**Step 1: Add markdown cell**

Explain the header structure: career group name, code, occupational family, pay band range, and concept of work. Explain the regex patterns used.

**Step 2: Add code cell**

```python
def parse_header(soup):
    """Extract career group header info: name, code, family, pay bands, concept of work."""
    header = {}

    # Get full page text for regex extraction
    text = soup.get_text()

    # Career group name and code - pattern: "Name, #Code" or "Name #Code"
    # Look in title, h1, or first bold text
    code_match = re.search(r'#(\d{5})', text)
    if code_match:
        header['career_group_code'] = code_match.group(1)

    # Occupational Family
    family_match = re.search(r'Occupational\s+Family:\s*(.+?)(?:\n|Pay\s+Band)', text, re.IGNORECASE)
    if family_match:
        header['occupational_family'] = family_match.group(1).strip()

    # Pay Band Range
    band_match = re.search(r'Pay\s+Band\s+Range:\s*(\d+)\s*-\s*(\d+)', text, re.IGNORECASE)
    if band_match:
        header['pay_band_min'] = int(band_match.group(1))
        header['pay_band_max'] = int(band_match.group(2))

    # Career group name - text before the code
    name_match = re.search(r'^(.+?)(?:,\s*)?#\d{5}', text.strip(), re.MULTILINE)
    if name_match:
        header['career_group_name'] = name_match.group(1).strip()

    # Derived: occ_family_code is first 2 digits
    if 'career_group_code' in header:
        header['occ_family_code'] = header['career_group_code'][:2]

    # Concept of Work - paragraph after "Concept of Work" heading
    cow_match = re.search(r'Concept\s+of\s+Work\s*[:\-]?\s*(.+?)(?=Role\s|PAY\s+BAND|$)',
                          text, re.IGNORECASE | re.DOTALL)
    if cow_match:
        header['concept_of_work'] = cow_match.group(1).strip()

    return header
```

**Step 3: Test against Financial Services**

```python
with open("raw_pages/html/19030.htm", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

header = parse_header(soup)
print("Code:", header.get('career_group_code'))       # Expected: 19030
print("Name:", header.get('career_group_name'))         # Expected: Financial Services
print("Family:", header.get('occupational_family'))     # Expected: Administrative Services
print("Band min:", header.get('pay_band_min'))          # Expected: 4
print("Band max:", header.get('pay_band_max'))          # Expected: 8
print("OCC code:", header.get('occ_family_code'))       # Expected: 19
print("CoW preview:", header.get('concept_of_work', '')[:100])  # Should start with "This Career Group..."
```

Expected: all values match the reference data in career_groups.csv. If any don't match, adjust regex patterns based on the actual HTML structure.

---

## Task 5: Build parse_role_matrix()

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 3c)

**Step 1: Add markdown cell**

Explain the role matrix table structure: PAY BAND | PRACTITIONER ROLES | ROLE CODE | MANAGEMENT ROLES | ROLE CODE. Explain dual career tracks.

**Step 2: Add code cell**

```python
def parse_role_matrix(soup):
    """Extract role matrix table into list of {role_name, role_code, pay_band, track} dicts."""
    roles = []

    # Find the role matrix table - it has headers like PAY BAND, PRACTITIONER, etc.
    tables = soup.find_all('table')
    matrix_table = None
    for table in tables:
        header_text = table.get_text().upper()
        if 'PAY BAND' in header_text and 'PRACTITIONER' in header_text:
            matrix_table = table
            break

    if not matrix_table:
        print("  WARNING: No role matrix table found")
        return roles

    rows = matrix_table.find_all('tr')
    for row in rows[1:]:  # Skip header row
        cells = row.find_all(['td', 'th'])
        if len(cells) < 5:
            continue

        pay_band_text = cells[0].get_text().strip()
        if not pay_band_text.isdigit():
            continue
        pay_band = int(pay_band_text)

        # Practitioner role (columns 1-2)
        pract_name = cells[1].get_text().strip()
        pract_code = cells[2].get_text().strip()
        if pract_name and pract_code:
            roles.append({
                'role_name': pract_name,
                'role_code': pract_code,
                'pay_band': pay_band,
                'track': 'practitioner'
            })

        # Management role (columns 3-4)
        mgmt_name = cells[3].get_text().strip()
        mgmt_code = cells[4].get_text().strip()
        if mgmt_name and mgmt_code:
            roles.append({
                'role_name': mgmt_name,
                'role_code': mgmt_code,
                'pay_band': pay_band,
                'track': 'management'
            })

    return roles
```

**Step 3: Test against Financial Services**

```python
role_matrix = parse_role_matrix(soup)
print(f"Found {len(role_matrix)} roles")  # Expected: 7
for r in role_matrix:
    print(f"  {r['role_code']} | {r['role_name']} | Band {r['pay_band']} | {r['track']}")
```

Expected: 7 roles matching roles.csv (Specialist I-III as practitioner, Manager I-IV as management).

---

## Task 6: Build parse_role_descriptions()

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 3d)

**Step 1: Add markdown cell**

Explain compensable factors (Complexity, Results, Accountability) and how they are used for classification. Explain the parsing approach: locate each role heading, then extract the three factor sections.

**Step 2: Add code cell**

```python
def parse_role_descriptions(soup, role_list):
    """Enrich role_list with role_summary and compensable factors from role description sections."""
    text = soup.get_text()

    for role in role_list:
        role_name = role['role_name']
        role_code = role['role_code']

        # Find the section for this role by looking for its name + code pattern
        # Pattern: role name followed by code somewhere nearby
        pattern = re.escape(role_name) + r'.*?' + re.escape(role_code)
        section_start = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if not section_start:
            # Try just the role name
            section_start = re.search(re.escape(role_name), text, re.IGNORECASE)

        if not section_start:
            print(f"  WARNING: Could not find section for {role_name} ({role_code})")
            role['role_summary'] = None
            role['complexity'] = None
            role['results'] = None
            role['accountability'] = None
            continue

        # Get text from this role's section to the next role or end
        start_pos = section_start.end()

        # Find the next role section or end of document
        next_role_names = [r['role_name'] for r in role_list if r['role_code'] != role_code]
        next_positions = []
        for nr in next_role_names:
            nm = re.search(re.escape(nr) + r'.*?\d{5}', text[start_pos:], re.DOTALL | re.IGNORECASE)
            if nm:
                next_positions.append(start_pos + nm.start())

        end_pos = min(next_positions) if next_positions else len(text)
        section_text = text[start_pos:end_pos]

        # Role summary - text before first compensable factor
        summary_match = re.search(r'^(.*?)(?:COMPLEXITY|Complexity)', section_text, re.DOTALL)
        if summary_match:
            role['role_summary'] = summary_match.group(1).strip()
        else:
            role['role_summary'] = None

        # Compensable factors
        complexity_match = re.search(
            r'(?:COMPLEXITY|Complexity)\s*(.*?)(?:RESULTS|Results)',
            section_text, re.DOTALL | re.IGNORECASE)
        role['complexity'] = complexity_match.group(1).strip() if complexity_match else None

        results_match = re.search(
            r'(?:RESULTS|Results)\s*(.*?)(?:ACCOUNTABILITY|Accountability)',
            section_text, re.DOTALL | re.IGNORECASE)
        role['results'] = results_match.group(1).strip() if results_match else None

        accountability_match = re.search(
            r'(?:ACCOUNTABILITY|Accountability)\s*(.*?)$',
            section_text, re.DOTALL | re.IGNORECASE)
        role['accountability'] = accountability_match.group(1).strip() if accountability_match else None

    return role_list
```

**Step 3: Test against Financial Services**

```python
enriched_roles = parse_role_descriptions(soup, role_matrix)
for r in enriched_roles:
    print(f"\n{r['role_name']} ({r['role_code']}):")
    print(f"  Summary: {(r.get('role_summary') or '')[:80]}...")
    print(f"  Complexity: {'YES' if r.get('complexity') else 'MISSING'}")
    print(f"  Results: {'YES' if r.get('results') else 'MISSING'}")
    print(f"  Accountability: {'YES' if r.get('accountability') else 'MISSING'}")
```

Expected: all 7 roles have non-empty summary, complexity, results, and accountability. Compare a sample (e.g., Specialist I) against the text in roles.csv.

---

## Task 7: Build parse_soc_codes()

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 3e)

**Step 1: Add markdown cell**

Explain SOC codes: BLS Standard Occupational Classification used for federal reporting. Explain the two mapping levels (career_group vs role).

**Step 2: Add code cell**

```python
def parse_soc_codes(soup, career_group_code):
    """Extract SOC codes from Statistical Reporting section and role headers."""
    soc_entries = []
    text = soup.get_text()

    # Find the Statistical Reporting section
    stat_match = re.search(
        r'(?:Statistical\s+Reporting|Standard\s+Occupational\s+Classification)(.*?)(?:History|$)',
        text, re.DOTALL | re.IGNORECASE)

    if stat_match:
        stat_text = stat_match.group(1)
        # Extract SOC codes: pattern like "13-2010 Accountants and Auditors"
        soc_pattern = r'(\d{2}-\d{4})\s+(.+?)(?=\d{2}-\d{4}|\n\n|$)'
        for match in re.finditer(soc_pattern, stat_text):
            soc_entries.append({
                'career_group_code': career_group_code,
                'role_code': None,
                'soc_code': match.group(1),
                'soc_title': match.group(2).strip(),
                'mapping_level': 'career_group',
                'data_source': 'DHRM_PUBLIC'
            })

    # Also check individual role headers for role-level SOC codes
    # These appear as "SOC: XX-XXXX" in the role description headers
    role_soc_pattern = r'(\d{5}).*?(?:SOC|S\.O\.C\.)\s*:?\s*(\d{2}-\d{4})'
    for match in re.finditer(role_soc_pattern, text, re.IGNORECASE):
        role_code = match.group(1)
        soc_code = match.group(2)
        # Only add if not already captured at group level
        soc_entries.append({
            'career_group_code': career_group_code,
            'role_code': role_code,
            'soc_code': soc_code,
            'soc_title': None,  # May not be listed at role level
            'mapping_level': 'role',
            'data_source': 'DHRM_PUBLIC'
        })

    return soc_entries
```

**Step 3: Test against Financial Services**

```python
soc_codes = parse_soc_codes(soup, "19030")
print(f"Found {len(soc_codes)} SOC code entries")  # Expected: 12 (5 group + 7 role)
for s in soc_codes:
    level = s['mapping_level']
    role = s['role_code'] or 'GROUP'
    print(f"  [{level}] {role} -> {s['soc_code']} {s['soc_title'] or ''}")
```

Expected: 12 entries matching soc_codes.csv (5 career_group level, 7 role level).

---

## Task 8: Build parse_historical_titles()

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 3f)

**Step 1: Add markdown cell**

Explain historical titles: former Virginia state classification codes/titles that were folded into the current career group system. Explain why this data matters for reclassification.

**Step 2: Add code cell**

```python
def parse_historical_titles(soup, role_list):
    """Extract historical title mappings from the History section."""
    titles = []
    text = soup.get_text()

    # Find the History section
    history_match = re.search(r'History(.*?)$', text, re.DOTALL | re.IGNORECASE)
    if not history_match:
        print("  WARNING: No History section found")
        return titles

    history_text = history_match.group(1)

    # Build a lookup from role name to role code
    role_lookup = {r['role_name']: r['role_code'] for r in role_list}

    # Find all tables in the History section
    # First, locate the History heading in the DOM
    history_heading = None
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'b', 'strong']):
        if 'history' in heading.get_text().lower():
            history_heading = heading
            break

    if not history_heading:
        print("  WARNING: Could not find History heading in DOM")
        return titles

    # Walk siblings/descendants after the History heading
    current_role_code = None

    # Find all elements after the history heading
    for element in history_heading.find_all_next():
        element_text = element.get_text().strip()

        # Check if this is a role name subheading
        for role_name, role_code in role_lookup.items():
            if role_name in element_text and element.name in ['h3', 'h4', 'b', 'strong', 'p']:
                current_role_code = role_code
                break

        # Check if this is a history table
        if element.name == 'table' and current_role_code:
            rows = element.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    code_text = cells[0].get_text().strip()
                    title_text = cells[1].get_text().strip()
                    grade_text = cells[2].get_text().strip()

                    # Skip header rows
                    if code_text.upper() in ['CLASS CODE', 'CODE', '']:
                        continue

                    grade = int(grade_text) if grade_text.isdigit() else None

                    titles.append({
                        'role_code': current_role_code,
                        'former_class_code': code_text,
                        'former_class_title': title_text,
                        'former_grade': grade,
                        'data_source': 'DHRM_PUBLIC'
                    })

    return titles
```

**Step 3: Test against Financial Services**

```python
hist_titles = parse_historical_titles(soup, role_matrix)
print(f"Found {len(hist_titles)} historical titles")  # Expected: 59
# Show distribution by role
from collections import Counter
role_counts = Counter(t['role_code'] for t in hist_titles)
for code, count in sorted(role_counts.items()):
    print(f"  {code}: {count} titles")
```

Expected: 59 total historical titles matching historical_titles.csv.

---

## Task 9: Build HTML Orchestrator and Run Phase 1

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 3g orchestrator, then Cell 5 for execution)

**Step 1: Add orchestrator function**

```python
def parse_html_page(filepath, career_group_code, career_group_name, occupational_family):
    """Orchestrate all section parsers for one HTML career group page."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Parse header
    header = parse_header(soup)
    # Override with known values from our source list (more reliable)
    header['career_group_code'] = career_group_code
    header['career_group_name'] = career_group_name
    header['occupational_family'] = occupational_family
    header['occ_family_code'] = career_group_code[:2]

    # Parse role matrix
    role_list = parse_role_matrix(soup)

    # Enrich with descriptions
    role_list = parse_role_descriptions(soup, role_list)

    # Parse SOC codes
    soc_list = parse_soc_codes(soup, career_group_code)

    # Parse historical titles
    hist_list = parse_historical_titles(soup, role_list)

    return header, role_list, soc_list, hist_list
```

**Step 2: Add execution cell (Cell 5) - Phase 1 only**

```python
# Phase 1: Test with Financial Services only
sources_to_process = TEST_SOURCES  # Switch to ALL_SOURCES for full run

all_career_groups = []
all_roles = []
all_soc_codes = []
all_historical_titles = []
errors = []

for code, name, family, url, fmt in sources_to_process:
    print(f"\nProcessing: {name} ({code})")
    try:
        filepath = fetch_and_cache(url, fmt, code)

        if fmt == "html":
            header, roles, socs, hist = parse_html_page(filepath, code, name, family)
        else:
            # PDF parsing - Phase 3
            print(f"  [SKIP] PDF parsing not yet implemented")
            continue

        # Add metadata to header
        header['source_url'] = url
        header['source_format'] = fmt
        header['data_source'] = 'DHRM_PUBLIC'

        all_career_groups.append(header)
        all_roles.extend(roles)
        all_soc_codes.extend(socs)
        all_historical_titles.extend(hist)

        print(f"  OK: {len(roles)} roles, {len(socs)} SOC codes, {len(hist)} historical titles")

    except Exception as e:
        print(f"  ERROR: {e}")
        errors.append((code, name, str(e)))

# Summary
print(f"\n{'='*50}")
print(f"Career groups: {len(all_career_groups)}")
print(f"Roles: {len(all_roles)}")
print(f"SOC codes: {len(all_soc_codes)}")
print(f"Historical titles: {len(all_historical_titles)}")
if errors:
    print(f"Errors: {len(errors)}")
    for code, name, err in errors:
        print(f"  {code} {name}: {err}")
```

**Step 3: Run and validate Phase 1**

Expected output for Financial Services:
- 1 career group
- 7 roles
- 12 SOC codes
- 59 historical titles
- 0 errors

If counts don't match, debug the individual parser that's off before proceeding.

---

## Task 10: Build DataFrames and Validation (Cell 6)

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 6)

**Step 1: Add markdown cell**

Explain data validation: pattern checks, referential integrity, and comparison against known reference data.

**Step 2: Add code cell**

```python
# Build DataFrames
df_career_groups = pd.DataFrame(all_career_groups)
df_roles = pd.DataFrame(all_roles)
df_soc_codes = pd.DataFrame(all_soc_codes)
df_historical_titles = pd.DataFrame(all_historical_titles)

print("DataFrame shapes:")
print(f"  career_groups: {df_career_groups.shape}")
print(f"  roles: {df_roles.shape}")
print(f"  soc_codes: {df_soc_codes.shape}")
print(f"  historical_titles: {df_historical_titles.shape}")

# Validation checks
print("\n--- Validation ---")

# 1. Code pattern checks
bad_cg_codes = df_career_groups[~df_career_groups['career_group_code'].str.match(r'^\d{5}$')]
print(f"Invalid career_group_codes: {len(bad_cg_codes)}")

bad_role_codes = df_roles[~df_roles['role_code'].str.match(r'^\d{5}$')]
print(f"Invalid role_codes: {len(bad_role_codes)}")

bad_soc = df_soc_codes[~df_soc_codes['soc_code'].str.match(r'^\d{2}-\d{4}$')]
print(f"Invalid SOC codes: {len(bad_soc)}")

# 2. Pay band range check
bad_bands = df_roles[(df_roles['pay_band'] < 1) | (df_roles['pay_band'] > 10)]
print(f"Pay bands out of range (1-10): {len(bad_bands)}")

# 3. Referential integrity: every role's career_group_code exists in career_groups
orphan_roles = df_roles[~df_roles['career_group_code'].isin(df_career_groups['career_group_code'])]
print(f"Orphan roles (no matching career group): {len(orphan_roles)}")

# 4. Required fields check
for col in ['career_group_code', 'career_group_name', 'concept_of_work']:
    nulls = df_career_groups[col].isna().sum()
    if nulls > 0:
        print(f"  career_groups.{col}: {nulls} nulls")

for col in ['role_code', 'role_name', 'role_summary', 'complexity', 'results', 'accountability']:
    nulls = df_roles[col].isna().sum()
    if nulls > 0:
        print(f"  roles.{col}: {nulls} nulls")

# 5. Financial Services reference check (Phase 1)
fs_roles = df_roles[df_roles['career_group_code'] == '19030']
fs_soc = df_soc_codes[df_soc_codes['career_group_code'] == '19030']
fs_hist = df_historical_titles[df_historical_titles['role_code'].isin(fs_roles['role_code'])]
print(f"\nFinancial Services reference check:")
print(f"  Roles: {len(fs_roles)} (expected 7)")
print(f"  SOC codes: {len(fs_soc)} (expected 12)")
print(f"  Historical titles: {len(fs_hist)} (expected 59)")

print("\n--- Validation complete ---")
```

Expected: all checks pass with 0 invalid entries.

---

## Task 11: Database Load with CSV Fallback (Cell 7)

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 7)

**Step 1: Add markdown cell**

Explain the database connection: local MySQL for development, Cloud SQL for production. Explain the CSV fallback strategy. Mask credentials in the explanation.

**Step 2: Add code cell**

```python
# Database connection configuration
# For local MySQL: mysql+pymysql://username:password@localhost/wm_hr_classification
# For Cloud SQL: mysql+pymysql://username:password@cloud-sql-ip/wm_hr_classification
DB_CONNECTION_STRING = "mysql+pymysql://root:password@localhost/wm_hr_classification"

CSV_OUTPUT_DIR = "output_csv"
os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)

try:
    engine = create_engine(DB_CONNECTION_STRING)
    # Test connection
    with engine.connect() as conn:
        conn.execute("SELECT 1")
    print("MySQL connection successful!")

    # Load DataFrames to MySQL
    # Order matters due to foreign keys: career_groups first, then roles, then dependent tables
    df_career_groups.to_sql('career_groups', engine, if_exists='append', index=False)
    print(f"  Loaded {len(df_career_groups)} career groups")

    df_roles.to_sql('roles', engine, if_exists='append', index=False)
    print(f"  Loaded {len(df_roles)} roles")

    df_soc_codes.to_sql('soc_codes', engine, if_exists='append', index=False)
    print(f"  Loaded {len(df_soc_codes)} SOC codes")

    df_historical_titles.to_sql('historical_titles', engine, if_exists='append', index=False)
    print(f"  Loaded {len(df_historical_titles)} historical titles")

    print("\nAll tables loaded to MySQL successfully!")
    db_loaded = True

except Exception as e:
    print(f"MySQL connection failed: {e}")
    print("Falling back to CSV export...")

    df_career_groups.to_csv(os.path.join(CSV_OUTPUT_DIR, "career_groups.csv"), index=False)
    df_roles.to_csv(os.path.join(CSV_OUTPUT_DIR, "roles.csv"), index=False)
    df_soc_codes.to_csv(os.path.join(CSV_OUTPUT_DIR, "soc_codes.csv"), index=False)
    df_historical_titles.to_csv(os.path.join(CSV_OUTPUT_DIR, "historical_titles.csv"), index=False)

    print(f"Exported 4 CSV files to {CSV_OUTPUT_DIR}/")
    db_loaded = False
```

---

## Task 12: Verification Queries (Cell 8)

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (add Cell 8)

**Step 1: Add markdown cell**

Explain each verification query and what it validates.

**Step 2: Add code cell**

```python
if db_loaded:
    # Verification queries against MySQL
    print("=== Verification Queries ===\n")

    # 1. Record counts
    for table in ['career_groups', 'roles', 'soc_codes', 'historical_titles']:
        count = pd.read_sql(f"SELECT COUNT(*) as cnt FROM {table}", engine).iloc[0]['cnt']
        print(f"{table}: {count} rows")

    # 2. Career groups by occupational family
    print("\nCareer groups by Occupational Family:")
    family_counts = pd.read_sql(
        "SELECT occupational_family, COUNT(*) as cnt FROM career_groups GROUP BY occupational_family ORDER BY cnt DESC",
        engine)
    print(family_counts.to_string(index=False))

    # 3. Roles per career group (spot check)
    print("\nRoles per career group (top 10):")
    roles_per_group = pd.read_sql(
        """SELECT cg.career_group_name, COUNT(r.role_code) as role_count
           FROM career_groups cg
           LEFT JOIN roles r ON cg.career_group_code = r.career_group_code
           GROUP BY cg.career_group_name
           ORDER BY role_count DESC
           LIMIT 10""",
        engine)
    print(roles_per_group.to_string(index=False))

    # 4. Track distribution
    print("\nRoles by track:")
    track_dist = pd.read_sql(
        "SELECT track, COUNT(*) as cnt FROM roles GROUP BY track",
        engine)
    print(track_dist.to_string(index=False))

    # 5. Sample role with compensable factors
    print("\nSample role (Financial Services Specialist I):")
    sample = pd.read_sql(
        "SELECT role_name, pay_band, track, LEFT(complexity, 100) as complexity_preview FROM roles WHERE role_code = '19031'",
        engine)
    print(sample.to_string(index=False))

else:
    # Verification against CSV DataFrames
    print("=== Verification (from DataFrames) ===\n")
    print(f"career_groups: {len(df_career_groups)} rows")
    print(f"roles: {len(df_roles)} rows")
    print(f"soc_codes: {len(df_soc_codes)} rows")
    print(f"historical_titles: {len(df_historical_titles)} rows")

    print("\nCareer groups by Occupational Family:")
    print(df_career_groups.groupby('occupational_family').size().sort_values(ascending=False).to_string())

    print("\nRoles by track:")
    print(df_roles['track'].value_counts().to_string())

    print("\nSample role (Financial Services Specialist I):")
    sample = df_roles[df_roles['role_code'] == '19031'][['role_name', 'pay_band', 'track']]
    print(sample.to_string(index=False))
```

---

## Task 13: Scale to All HTML Pages (Phase 2)

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (Cell 5 - change source list)

**Step 1: Update the execution cell**

Change `sources_to_process = TEST_SOURCES` to `sources_to_process = HTML_SOURCES`.

**Step 2: Run and review**

Run Cells 5 and 6. Check for:
- Any pages with 0 roles (parsing failure)
- Any pages with 0 historical titles (may be legitimate or parsing issue)
- Any validation failures

**Step 3: Fix edge cases**

Adjust parser regex patterns for any pages with formatting variations. Re-run until all HTML pages parse cleanly.

---

## Task 14: Build PDF Parser (Phase 3)

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (Cell 4)

**Step 1: Add markdown cell**

Explain why 6 career groups are PDFs instead of HTML. Explain pdfplumber approach.

**Step 2: Add code cell**

```python
def parse_pdf_page(filepath, career_group_code, career_group_name, occupational_family):
    """Parse a PDF career group page using pdfplumber."""
    header = {
        'career_group_code': career_group_code,
        'career_group_name': career_group_name,
        'occupational_family': occupational_family,
        'occ_family_code': career_group_code[:2],
        'data_source': 'DHRM_PUBLIC'
    }
    role_list = []
    soc_list = []
    hist_list = []

    with pdfplumber.open(filepath) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Pay band range
    band_match = re.search(r'Pay\s+Band\s+Range:\s*(\d+)\s*-\s*(\d+)', full_text, re.IGNORECASE)
    if band_match:
        header['pay_band_min'] = int(band_match.group(1))
        header['pay_band_max'] = int(band_match.group(2))

    # Concept of work
    cow_match = re.search(
        r'Concept\s+of\s+Work\s*[:\-]?\s*(.+?)(?=Role\s|PAY\s+BAND|$)',
        full_text, re.IGNORECASE | re.DOTALL)
    if cow_match:
        header['concept_of_work'] = cow_match.group(1).strip()

    # Role matrix - look for tabular data with role names and codes
    # PDF tables are trickier - extract with pdfplumber's table extraction
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                header_row = [str(cell).upper() if cell else '' for cell in table[0]]
                if 'PAY BAND' in ' '.join(header_row) or 'PRACTITIONER' in ' '.join(header_row):
                    for row in table[1:]:
                        if not row or not row[0]:
                            continue
                        pay_band_text = str(row[0]).strip()
                        if not pay_band_text.isdigit():
                            continue
                        pay_band = int(pay_band_text)

                        # Practitioner
                        if len(row) > 2 and row[1] and str(row[1]).strip():
                            role_list.append({
                                'role_name': str(row[1]).strip(),
                                'role_code': str(row[2]).strip() if len(row) > 2 and row[2] else '',
                                'pay_band': pay_band,
                                'track': 'practitioner'
                            })
                        # Management
                        if len(row) > 4 and row[3] and str(row[3]).strip():
                            role_list.append({
                                'role_name': str(row[3]).strip(),
                                'role_code': str(row[4]).strip() if len(row) > 4 and row[4] else '',
                                'pay_band': pay_band,
                                'track': 'management'
                            })

    # Compensable factors from full text (same regex approach as HTML)
    for role in role_list:
        role_name = role['role_name']
        section_match = re.search(re.escape(role_name), full_text)
        if section_match:
            start = section_match.end()
            remaining = full_text[start:start+3000]

            summary_match = re.search(r'^(.*?)(?:COMPLEXITY|Complexity)', remaining, re.DOTALL)
            role['role_summary'] = summary_match.group(1).strip() if summary_match else None

            c_match = re.search(r'(?:COMPLEXITY|Complexity)\s*(.*?)(?:RESULTS|Results)', remaining, re.DOTALL | re.IGNORECASE)
            role['complexity'] = c_match.group(1).strip() if c_match else None

            r_match = re.search(r'(?:RESULTS|Results)\s*(.*?)(?:ACCOUNTABILITY|Accountability)', remaining, re.DOTALL | re.IGNORECASE)
            role['results'] = r_match.group(1).strip() if r_match else None

            a_match = re.search(r'(?:ACCOUNTABILITY|Accountability)\s*(.*?)(?=\n[A-Z]{2,}|\Z)', remaining, re.DOTALL | re.IGNORECASE)
            role['accountability'] = a_match.group(1).strip() if a_match else None

    # SOC codes
    soc_pattern = r'(\d{2}-\d{4})\s+(.+?)(?=\d{2}-\d{4}|\n\n|$)'
    stat_match = re.search(r'(?:Statistical|Standard\s+Occupational)(.*?)(?:History|$)', full_text, re.DOTALL | re.IGNORECASE)
    if stat_match:
        for m in re.finditer(soc_pattern, stat_match.group(1)):
            soc_list.append({
                'career_group_code': career_group_code,
                'role_code': None,
                'soc_code': m.group(1),
                'soc_title': m.group(2).strip(),
                'mapping_level': 'career_group',
                'data_source': 'DHRM_PUBLIC'
            })

    # Historical titles - similar text-based extraction
    hist_match = re.search(r'History(.*?)$', full_text, re.DOTALL | re.IGNORECASE)
    if hist_match:
        hist_text = hist_match.group(1)
        # Try to find class code patterns: 5-digit code followed by title and grade
        title_pattern = r'(\d{5})\s+(.+?)\s+(\d{1,2})\s*$'
        current_role_code = None
        for line in hist_text.split('\n'):
            line = line.strip()
            # Check if this line is a role name
            for role in role_list:
                if role['role_name'] in line:
                    current_role_code = role['role_code']
                    break
            # Check if this line is a historical title entry
            t_match = re.match(title_pattern, line)
            if t_match and current_role_code:
                hist_list.append({
                    'role_code': current_role_code,
                    'former_class_code': t_match.group(1),
                    'former_class_title': t_match.group(2).strip(),
                    'former_grade': int(t_match.group(3)),
                    'data_source': 'DHRM_PUBLIC'
                })

    return header, role_list, soc_list, hist_list
```

**Step 3: Test with one PDF**

Download one PDF, run the parser, check output counts.

**Step 4: Update execution cell to include PDFs**

Change the `if fmt == "html"` block to also handle `"pdf"` using `parse_pdf_page()`.

---

## Task 15: Full Run and Final Validation (Phase 4)

**Files:**
- Modify: `griffin_dhrm_pipeline.ipynb` (Cell 5 - switch to ALL_SOURCES)

**Step 1: Switch to ALL_SOURCES**

Change `sources_to_process = HTML_SOURCES` to `sources_to_process = ALL_SOURCES`.

**Step 2: Run all cells end-to-end**

Run the entire notebook. Review:
- Total counts across all 4 tables
- Any errors in the error list
- Validation cell output
- DB load or CSV export

**Step 3: Final review of notebook markdown**

Ensure every cell has clear, professor-readable markdown. Check that no em-dashes appear anywhere.

---

## Execution Notes

- **Parser code in this plan is a starting point.** The regex patterns are based on the Financial Services page structure observed via WebFetch. Real HTML may need adjustments -- that's expected and is why we test against the reference data first.
- **PDF parser will almost certainly need per-PDF tweaks.** The 6 PDFs may have different layouts. Handle case-by-case in Phase 3.
- **The notebook should work end-to-end even without MySQL** -- the CSV fallback ensures it always produces output.
