# GRIFFIN Tools

## batch_ingest.py -- Batch Ingestion Utility

Adds new position descriptions (PDs) to the GRIFFIN training data from Word and PDF documents. Designed for HR staff who work in spreadsheets.

### Prerequisites

All dependencies are already in the GRIFFIN conda environment:

- python-docx
- pdfplumber
- openpyxl
- pandas
- google-generativeai (only needed for --classify)

### Three-Step Workflow

**Step 1: Extract** -- Pull text from documents into a review spreadsheet.

```bash
python tools/batch_ingest.py --extract --input-dir "path/to/pd_folder" --output "batch_review.xlsx"
```

This reads every `.docx` and `.pdf` in the folder, extracts the text, and writes a spreadsheet with columns: `filename`, `extracted_text`, `char_count`, `status`. Corrupted or password-protected files are marked EXTRACT_FAILED and skipped.

**Step 2: Classify** -- Run GRIFFIN's classification pipeline on each PD.

```bash
# Classification only
python tools/batch_ingest.py --classify --input "batch_review.xlsx" --api-key "YOUR_GEMINI_KEY"

# Classification + AI cleaning (PII detection, boilerplate removal)
python tools/batch_ingest.py --classify --input "batch_review.xlsx" --api-key "YOUR_GEMINI_KEY" --ai-clean
```

New columns are added: `ml_prediction`, `ml_confidence`, `ai_career_group`, `ai_role`, `ai_confidence`, `occ_family_suggested`, `correct_label`, `notes`.

The `correct_label` column is pre-filled with the model's suggestion. The HR reviewer confirms or changes it.

With `--ai-clean`, additional columns appear: `pii_flags`, `cleaned_text`, `boilerplate_removed`. PII flags are advisory -- the HR reviewer makes the final call.

**Step 3: Ingest** -- Append approved PDs to training data.

```bash
python tools/batch_ingest.py --ingest --input "batch_review.xlsx"
```

Before running this step, the HR reviewer must:
1. Set `status` to `APPROVED` for rows that should be added
2. Confirm or correct the `correct_label` column (must be a valid job_family value)

The script validates labels, appends to `data/training/workday_training.csv`, and prints a reminder to retrain.

### Rate Limiting

A paid Gemini API tier is recommended for production use. The default `--delay 2` adds a 2-second pause between API calls as a safety margin. With a paid account, use `--delay 0` for full speed.

### Valid job_family Labels

The `correct_label` column must match one of the 30 job families in the training data exactly. The script will reject any unrecognized labels and print the valid list.

---

## cloud_sql_setup.py -- GCP Cloud SQL Setup

User-friendly wrapper for deploying and verifying the GRIFFIN database schema on GCP Cloud SQL. Designed for IT staff following the Technical Transition Guide.

### What It Does

1. Checks if Cloud SQL credentials are configured in `.env`
2. Connects to Cloud SQL (or falls back to local SQLite)
3. Deploys the schema from `data/schema/wm_hr_classification_schema.sql`
4. Verifies all 9 expected tables exist and reports results

### Usage

```bash
# Auto-detect: uses Cloud SQL if .env has credentials, otherwise local SQLite
python tools/cloud_sql_setup.py

# Force local SQLite for testing (no GCP credentials needed)
python tools/cloud_sql_setup.py --local-only
```

### Cloud SQL Configuration

Create a `.env` file in the project root with:

```
CLOUD_SQL_HOST=<your-cloud-sql-public-ip>
CLOUD_SQL_PASSWORD=<your-database-password>
CLOUD_SQL_PORT=3306          # optional, default 3306
CLOUD_SQL_DB=griffin_db      # optional, default griffin_db
CLOUD_SQL_USER=root          # optional, default root
```

### Prerequisites

```bash
pip install sqlalchemy pymysql python-dotenv
```
