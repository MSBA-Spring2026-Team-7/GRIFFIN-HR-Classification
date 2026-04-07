# GRIFFIN: DHRM Data Pipeline
## Claude Code Project Instructions

GRIFFIN (Government Role Identification and Financial Framework Integration Network) is the data pipeline component of the W&M HR Classification & Pay Matching Tool. This Claude Code session focuses exclusively on Workstream 1: scraping, parsing, and loading the DHRM career group data into a structured database.

---

## What This Session Builds

A Jupyter notebook (griffin_dhrm_pipeline.ipynb) that serves as the core deliverable for BUAD 5722: Big Data & Cloud Analytics. The notebook must demonstrate end-to-end big data concepts using course tools, not just produce output files.

The notebook scrapes all ~56 DHRM career group pages, parses them into structured data, and loads them into a MySQL database. Every step must use tools from the Big Data course toolkit and be documented with clear markdown explanations.

---

## Critical Constraint: Big Data Course Tools

This notebook is graded on "Use of Course Tools." The pipeline MUST use:

| Step | Tool | Course Week |
|---|---|---|
| Web scraping | BeautifulSoup and/or Selenium | Week 5 |
| Text parsing | regex (re module) | Week 6 |
| Data structuring | pandas DataFrames | Week 2-3 |
| Database connection | sqlalchemy + pymysql | Week 2-3 |
| Database target | MySQL (Cloud SQL or local) | Week 2-3 |
| HTTP requests | requests library | Week 4 |
| PDF parsing | tabula-py or pdfplumber (for the 6 PDF career groups) | Week 5 |

Do NOT use tools the course hasn't covered unless necessary. The professor wants to see mastery of course material, not novel libraries.

---

## Database Schema

The target database has 6 reference tables. The full SQL schema is in wm_hr_classification_schema.sql (should be in the project folder). The tables to populate are:

### career_groups
| Column | Type | Description |
|---|---|---|
| career_group_code | VARCHAR(5) | 4-digit code, e.g. 19030 |
| career_group_name | VARCHAR(100) | e.g. Financial Services |
| occupational_family | VARCHAR(100) | e.g. Administrative Services |
| occ_family_code | VARCHAR(2) | First 2 digits |
| pay_band_min | INT | Lowest band in group |
| pay_band_max | INT | Highest band in group |
| concept_of_work | TEXT | Full narrative description |
| source_url | VARCHAR(500) | DHRM page URL |
| source_format | VARCHAR(10) | html or pdf |
| effective_date | DATE | Usually 2001-11-01 |
| data_source | VARCHAR(50) | DHRM_PUBLIC |

### roles
| Column | Type | Description |
|---|---|---|
| role_code | VARCHAR(5) | 5-digit code, e.g. 19036 |
| role_name | VARCHAR(150) | e.g. Financial Services Manager III |
| career_group_code | VARCHAR(5) | FK to career_groups |
| pay_band | INT | Single band number |
| track | VARCHAR(20) | practitioner or management |
| role_summary | TEXT | Intro paragraph for the role |
| complexity | TEXT | Compensable factor text |
| results | TEXT | Compensable factor text |
| accountability | TEXT | Compensable factor text |
| data_source | VARCHAR(50) | DHRM_PUBLIC |

### historical_titles
| Column | Type | Description |
|---|---|---|
| role_code | VARCHAR(5) | FK to roles |
| former_class_code | VARCHAR(10) | Previous code |
| former_class_title | VARCHAR(200) | Previous title |
| former_grade | INT | Previous grade |
| data_source | VARCHAR(50) | DHRM_PUBLIC |

### soc_codes
| Column | Type | Description |
|---|---|---|
| career_group_code | VARCHAR(5) | FK to career_groups |
| role_code | VARCHAR(5) | FK to roles (NULL if group-level) |
| soc_code | VARCHAR(10) | BLS SOC code |
| soc_title | VARCHAR(200) | BLS title |
| mapping_level | VARCHAR(15) | career_group or role |
| data_source | VARCHAR(50) | DHRM_PUBLIC |

---

## Source URLs

### HTML Pages (50 pages, consistent template)
All hosted at web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/

```
19010|Administration and Office Support|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/AdminOfficeSupport19010.htm
39050|Architecture and Engineering Services|Engineering and Technology|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/engtechnology/eng39050ArchEngineer.htm
19190|Audit and Management Services|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/AuditMgmt19190.htm
79030|Building Trades|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/BuildingTrades79030.htm
39010|Computer Operations|Engineering and Technology|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/engtechnology/ComputerOperations39010.htm
49010|Counseling Services|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/hea49010Counseling.htm
49030|Dental Services|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/Dental49030.htm
49050|Direct Service|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/DirectSvcs49050.htm
29130|Education Administration|Educational and Media Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/EducMediaServ/edu29130EducAdm.htm
29140|Education Support Services|Educational and Media Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/EducMediaServ/edu29140EducSupportServ.htm
39030|Electronics|Engineering and Technology|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/engtechnology/eng39030Electronics.htm
39070|Engineering Technology|Engineering and Technology|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/engtechnology/eng39070EnginTech.htm
59030|Environmental Services|Natural Resources and Applied Science|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/natresouc/nat59030Environmental.htm
79050|Equipment Service and Repair|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/EquipSvcsRepair79050.htm
19030|Financial Services|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/FinancialServices19030.htm
79210|Food Services|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/FoodService79210.htm
69130|Forensic Science|Public Safety|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/pubsafe/ForensicScience69130.htm
19220|General Administration|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/GenlAdmin19220.htm
49170|Health Care Compliance|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/HealthCareCompliance49170.htm
49090|Health Care Technology|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/HlthCareTechnology49090.htm
19070|Hearing and Legal Services|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/HearingLegal19070.htm
29030|Historical Services and Preservation|Educational and Media Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/EducMediaServ/edu29030HistoricalServ.htm
79070|Housekeeping and Apparel Services|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/HousekeepingApparelSvcs79070.htm
19090|Human Resources Services|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/HumanResource19090.htm
59070|Laboratory and Research Technicians and Specialists|Natural Resources and Applied Science|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/natresouc/nat59070LabResearch.htm
19110|Land Acquisition and Property Management|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/LandAcq19110.htm
69070|Law Enforcement|Public Safety|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/pubsafe/LawEnforcement69070.htm
29050|Library Services|Educational and Media Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/EducMediaServ/edu29050library.htm
59130|Life and Physical Science|Natural Resources and Applied Science|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/natresouc/nat59130LifePhysicalSci.htm
29070|Media and Production Services|Educational and Media Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/EducMediaServ/edu29070MediaProdSvcs.htm
59090|Minerals Regulatory Services|Natural Resources and Applied Science|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/natresouc/nat59090MineralsRegscvcs.htm
59110|Natural Resources Specialists|Natural Resources and Applied Science|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/natresouc/nat59110NatRes.htm
49110|Nursing/Physician Assistance Services|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/NursingPhysAsstance49110.htm
49130|Pharmaceutical Services|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/Pharma49130.htm
49150|Physician Services|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/Physiciansvcs49150.htm
19130|Policy Analysis and Planning|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/PolicyAnalysisPlan19130.htm
79090|Printing Operations|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/PrintingOperations79090.htm
69090|Probation and Parole|Public Safety|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/pubsafe/ProbationParoleSvcs69090.htm
19210|Program Administration|Administrative Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/admin/ProgAdmin19210.htm
49210|Psychological Services|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/Psychologica49210.htm
29090|Public Relations and Marketing|Educational and Media Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/EducMediaServ/edu29090PublicRelationsMarketing.htm
69030|Public Safety Compliance|Public Safety|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/pubsafe/PublicSafetyCompliance69030.htm
49230|Rehabilitation Therapies|Health and Human Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/health/RehabTherapies49230.htm
79110|Retail Operations|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/RetailOperations79110.htm
69110|Security Services|Public Safety|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/pubsafe/SecurityServices69110.htm
79130|Stores and Warehousing Operations|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/StoresWareOperations79130.htm
29110|Training and Instruction|Educational and Media Services|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/EducMediaServ/edu29110Training.htm
79150|Transportation Operations|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/TransportOperations79150.htm
79170|Utility Plant Operations|Trades and Operations|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/trades/UtilityPlantOper79170.htm
59150|Veterinary Science|Natural Resources and Applied Science|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/natresouc/nat59150VeterinaryScience.htm
```

### PDF Pages (6 pages, need PDF parsing)
```
59010|Agricultural Services|Natural Resources and Applied Science|https://www.dhrm.virginia.gov/docs/default-source/compensationdocuments/agricultural-services-cgd-final44306F8E3605.pdf
79010|Aircraft Operations|Trades and Operations|https://www.dhrm.virginia.gov/docs/default-source/hr/career-group-descriptions/aircraft-operations-cgd-final-docx.pdf
69150|Emergency Services|Public Safety|https://web1.dhrm.virginia.gov/itech/DHRMWebAssets/careergroups/pubsafe/EmergencyServicesCareerGroup69150.pdf
39110|Information Technology Specialists|Engineering and Technology|https://www.dhrm.virginia.gov/docs/default-source/compensationdocuments/info-tech-specialists-career-group-update.pdf
19150|Procurement Services|Administrative Services|https://www.dhrm.virginia.gov/docs/default-source/compensationdocuments/procurement-services-career-group-description-update.pdf
79190|Watercraft Operations|Trades and Operations|https://www.dhrm.virginia.gov/docs/default-source/hr/career-group-descriptions/79190-watercraft-operations-career-group.pdf
```

---

## HTML Page Template Structure

Every HTML career group page follows this consistent structure (validated across 3 different occupational families):

1. **Header block**: Career group name, code, occupational family, pay band range
   - Pattern: "[Name], #[5-digit code]\nOccupational Family: [Family]\nPay Band Range: [min] - [max]"

2. **Concept of Work**: Narrative paragraph describing what the career group covers

3. **Role Matrix Table**: Pay Band | Practitioner Roles | Role Code | Management Roles | Role Code
   - Some bands have only practitioner, some only management, some both (dual career track)
   - Dual track roles share a pay band but have different role codes

4. **Role Descriptions**: For each role:
   - Role name, code, pay band, SOC code in the header
   - Role summary paragraph
   - Three compensable factor sections: COMPLEXITY, RESULTS, ACCOUNTABILITY
   - Each factor contains bullet points describing the work at that level

5. **SOC Codes Section** (labeled "Statistical Reporting"):
   - Lists SOC codes and titles associated with the career group
   - Some pages also note SOC codes on individual role headers

6. **Historical Titles Section** (labeled "History"):
   - Organized by current role name
   - Table with columns: CLASS CODE | CLASS TITLE | GRADE

---

## Notebook Structure

The Jupyter notebook should be organized as follows:

### Cell 1: Setup and Libraries
```python
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from sqlalchemy import create_engine
import time
```
Markdown: Explain what each library is for and why it was chosen.

### Cell 2: Define Source URLs
Load the career group URLs from a list or CSV.
Markdown: Explain the DHRM data structure (7 families, ~56 groups, HTML vs PDF sources).

### Cell 3: Scraping Function for HTML Pages
A function that takes a URL, fetches the page, and parses it using BeautifulSoup and regex into structured data matching the schema above.
Markdown: Explain the parsing strategy, the consistent template, and how regex extracts the compensable factors.

### Cell 4: Scraping Function for PDF Pages
A function that handles the 6 PDF career groups using pdfplumber or tabula.
Markdown: Explain why some pages are PDFs and how the parsing differs.

### Cell 5: Execute the Scrape
Loop through all URLs, call the appropriate function, collect results into DataFrames.
Add appropriate delays between requests (1-2 seconds) to be respectful to the DHRM server.
Markdown: Discuss ethical scraping practices (rate limiting, robots.txt compliance, data is public).

### Cell 6: Data Validation
Check for missing fields, validate codes match expected patterns, show summary statistics.
Markdown: Explain what data quality checks were performed.

### Cell 7: Load to Database
Connect to MySQL (local or Cloud SQL) via sqlalchemy and load the DataFrames.
Markdown: Show the connection string pattern (with credentials masked) and explain the load strategy.

### Cell 8: Verification Queries
Run SQL queries to verify the data loaded correctly. Show record counts, sample rows, and run the validation queries from the schema file.
Markdown: Explain each query and what it validates.

---

## Validated Example Output

Financial Services (#19030) has been fully scraped and validated. The expected output for this career group:
- 1 career_groups row
- 7 roles rows (Specialist I-III, Manager I-IV)
- 59 historical_titles rows
- 12 soc_codes rows (5 group-level + 7 role-level)

Use this as the test case to validate your parsing functions before running across all 56 groups.

---

## Important Notes

- Add 1-2 second delays between HTTP requests to avoid overloading the DHRM server
- Some HTML pages have slight formatting variations (extra whitespace, slightly different table structures). Build the parser to be tolerant of these.
- The 6 PDF pages may have different internal structures. Handle them as a separate parsing path.
- Store raw HTML/PDF responses locally before parsing, so you don't need to re-scrape if parsing logic changes.
- Every cell should have a markdown explanation that a professor could read and understand the purpose and approach. This notebook IS the deliverable, not a throwaway script.
- Never use em-dashes in any content produced for this project.
