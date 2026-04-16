"""
GRIFFIN Batch Ingestion Utility
===============================
CLI tool for HR staff to add new position descriptions to the GRIFFIN
training data from Word (.docx) and PDF documents.

Three-mode workflow:
  1. EXTRACT  -- pull text from documents into a review spreadsheet
  2. CLASSIFY -- run GRIFFIN classification + optional AI cleaning
  3. INGEST   -- append approved PDs to training CSV

Usage:
  python tools/batch_ingest.py --extract  --input-dir path/to/docs --output batch_review.xlsx
  python tools/batch_ingest.py --classify --input batch_review.xlsx --api-key AIzaSy...
  python tools/batch_ingest.py --classify --input batch_review.xlsx --api-key AIzaSy... --ai-clean
  python tools/batch_ingest.py --ingest   --input batch_review.xlsx
"""

import argparse
import json
import os
import sys
import time
import traceback

import pandas as pd

# ---------------------------------------------------------------------------
# Path bootstrap -- let tools/ import from app/ and project root
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
APP_DIR = os.path.join(PROJECT_ROOT, "app")

# Insert project root and app/ so we can import agent_classifier + siblings
for p in (PROJECT_ROOT, APP_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

TRAINING_CSV = os.path.join(
    PROJECT_ROOT, "data", "training", "workday_training.csv"
)

# ---------------------------------------------------------------------------
# Valid job_family labels (must match training data exactly)
# ---------------------------------------------------------------------------
VALID_JOB_FAMILIES = {
    "Staff - Academic Program Administration",
    "Staff - Administrative & Office Support",
    "Staff - Admissions & Enrollment",
    "Staff - Alumni Affairs",
    "Staff - Athletic Training & Wellbeing",
    "Staff - Athletics Operations",
    "Staff - Building Services",
    "Staff - Career Services",
    "Staff - Communications",
    "Staff - Community Relations",
    "Staff - Compliance",
    "Staff - Financial Analysis",
    "Staff - Fiscal Administration",
    "Staff - Giving: Annual, Major Gifts, & Planned",
    "Staff - HR Business Partner",
    "Staff - Instructional Development & Design",
    "Staff - Lab & Research Support",
    "Staff - Librarians",
    "Staff - Maintenance",
    "Staff - Media & Creative Services",
    "Staff - Medical",
    "Staff - Program Management",
    "Staff - Public Relations",
    "Staff - Scientist",
    "Staff - Security - Law Enforcement Officer",
    "Staff - Security - Non Law Enforcement Officer",
    "Staff - Software Programming & Applications",
    "Staff - Stewardship & Donor Relations",
    "Staff - Student Services",
    "Staff - User Support",
}

# ===========================================================================
# AI Cleaning prompt (Gemini)
# ===========================================================================
AI_CLEAN_PROMPT = """\
You are an HR data quality specialist. Review this position description text that has \
been extracted from a document. Perform these checks:

1. PII DETECTION: Flag any remaining personally identifiable information:
   - Employee names, supervisor names
   - Employee IDs, SSNs
   - Phone numbers, email addresses
   - Specific department budget amounts with dollar signs
   Report each as: "PII_FLAG: [type] found at: [quoted text]"

2. BOILERPLATE REMOVAL: Identify and mark standard boilerplate text that should \
be stripped before ML training:
   - EEO/AA compliance statements
   - Application instructions ("click here to apply", "upload your resume")
   - University mission statements
   - Standard benefits descriptions
   Return the cleaned text with boilerplate removed.

3. QUALITY CHECK: Is this actually a position description?
   - YES: contains duty areas, qualifications, responsibilities
   - NO: this appears to be a [cover letter / org chart / policy document / etc.]

Respond in JSON:
{
  "pii_flags": ["PII_FLAG: name found at: 'Reports to Jane Smith'", ...],
  "is_valid_pd": true/false,
  "invalid_reason": "only if is_valid_pd is false",
  "cleaned_text": "the PD with boilerplate removed",
  "boilerplate_removed": ["EEO statement (lines 45-52)", ...]
}
"""


# ===========================================================================
# MODE 1: EXTRACT
# ===========================================================================
def _extract_text_docx(filepath):
    """Extract text from a .docx file using python-docx."""
    from docx import Document

    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs]
    return "\n".join(paragraphs)


def _extract_text_pdf(filepath):
    """Extract text from a .pdf file using pdfplumber."""
    import pdfplumber

    pages = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def run_extract(input_dir, output_path):
    """Mode 1: read .docx/.pdf from input_dir -> review spreadsheet."""
    if not os.path.isdir(input_dir):
        print(f"ERROR: Input directory not found: {input_dir}")
        sys.exit(1)

    # Gather document paths
    doc_files = []
    for fname in sorted(os.listdir(input_dir)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in (".docx", ".pdf"):
            doc_files.append(os.path.join(input_dir, fname))

    if not doc_files:
        print(f"No .docx or .pdf files found in: {input_dir}")
        sys.exit(1)

    print(f"Found {len(doc_files)} document(s) in {input_dir}")

    rows = []
    for fpath in doc_files:
        fname = os.path.basename(fpath)
        ext = os.path.splitext(fname)[1].lower()
        print(f"  Extracting: {fname} ...", end=" ")

        try:
            if ext == ".docx":
                text = _extract_text_docx(fpath)
            else:
                text = _extract_text_pdf(fpath)

            char_count = len(text)
            status = "PENDING_REVIEW"
            print(f"OK ({char_count:,} chars)")

        except Exception as exc:
            text = ""
            char_count = 0
            status = f"EXTRACT_FAILED: {exc}"
            print(f"FAILED ({exc})")

        rows.append({
            "filename": fname,
            "extracted_text": text,
            "char_count": char_count,
            "status": status,
        })

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"\nWrote {len(df)} rows to: {output_path}")
    print("Next step: review the spreadsheet, then run --classify.")


# ===========================================================================
# MODE 2: CLASSIFY
# ===========================================================================

# ── Module-level cache for CLI agents (replaces @st.cache_resource) ──
_cli_orchestrator = None
_cli_llm = None


def _init_cli_agents(api_key):
    """Initialize LLM and agents for CLI use (no Streamlit dependency).

    Mirrors agent_classifier._init_agents() but uses a plain module-level
    cache instead of @st.cache_resource.  Imports griffin_langchain_agents
    directly -- that module has NO Streamlit dependency.
    """
    global _cli_orchestrator, _cli_llm

    if _cli_orchestrator is not None:
        return _cli_orchestrator, _cli_llm

    import griffin_langchain_agents as gla
    from griffin_langchain_agents import (
        get_llm,
        create_agents,
        create_orchestrator,
        ensure_data_loaded,
    )

    # The orchestrator blend prompt is defined in agent_classifier.py but
    # it is a constant string with no Streamlit dependency.  Import just
    # the constant -- agent_classifier.py imports streamlit at module level,
    # so we inline the prompt here instead to stay 100% Streamlit-free.
    ORCHESTRATOR_BLEND_PROMPT = _get_blend_prompt()

    ensure_data_loaded()
    _cli_llm = get_llm(api_key=api_key, temperature=0)
    classifier_agent, pay_matcher_agent = create_agents(_cli_llm, verbose=False)
    _cli_orchestrator = create_orchestrator(
        _cli_llm, classifier_agent, pay_matcher_agent,
        system_prompt_override=ORCHESTRATOR_BLEND_PROMPT,
    )
    return _cli_orchestrator, _cli_llm


def _get_blend_prompt():
    """Return the orchestrator blend-detection prompt (CLI-safe copy).

    This is the same prompt as agent_classifier.ORCHESTRATOR_BLEND_PROMPT
    but inlined here so that batch_ingest.py never imports the
    agent_classifier module (which imports streamlit at module level).
    """
    return """\
You are an HR Classification Orchestrator for Virginia state positions at William & Mary.
You coordinate two specialist agents:
1. The Classifier agent -- determines the DHRM career group and role.
2. The Pay Matcher agent -- determines the pay band and salary range.

WORKFLOW:
1. Call the classifier to get the career group and role classification.
   The classifier MUST analyze each duty area, estimate the percentage of
   time, and map each to a career group.
2. After classification, determine blend status:
   - Calculate total percentage assigned to each career group.
   - If a secondary career group accounts for >= 30% of duties, the
     classification is BLENDED with primary and secondary roles.
   - If no secondary group reaches 30%, the classification is SINGLE.
3. Call the pay matcher for the primary role (and secondary if blended).
4. Return your final answer as a JSON block inside triple backticks with
   the label "json". Use EXACTLY this schema:

```json
{
  "classification_type": "SINGLE or BLENDED",
  "primary": {
    "career_group_code": <int>,
    "career_group_name": "<string>",
    "role_code": <int>,
    "role_name": "<string>",
    "pay_band": <int>,
    "confidence": <int 1-100>,
    "duty_pct": <float 0.0-1.0>,
    "reasoning": "<string>"
  },
  "secondary": null or {
    "career_group_code": <int>,
    "career_group_name": "<string>",
    "role_code": <int>,
    "role_name": "<string>",
    "pay_band": <int>,
    "confidence": <int 1-100>,
    "duty_pct": <float 0.0-1.0>,
    "reasoning": "<string>"
  },
  "alternative_role": null or {
    "role_code": <int>,
    "role_name": "<string>",
    "pay_band": <int>,
    "confidence": <int 1-100>,
    "reasoning": "<why this is the second-best match within the same career group>"
  },
  "alternative_group": {
    "career_group_code": <int>,
    "career_group_name": "<string -- MUST be a DIFFERENT career group than primary>",
    "role_code": <int>,
    "role_name": "<string>",
    "pay_band": <int>,
    "confidence": <int 1-100>,
    "reasoning": "<why this different career group could also apply>"
  },
  "explanation": "<professional narrative paragraph explaining the classification>"
}
```

RULES:
- For SINGLE: primary.duty_pct = 1.0, secondary = null
- For BLENDED: primary.duty_pct + secondary.duty_pct must = 1.0 (normalized)
- confidence is your honest assessment (1-100). Do NOT fabricate or copy.
- Use the ACTUAL career_group_code and role_code integers from the GRIFFIN data.
- Always include the JSON block -- the Streamlit app parses it programmatically.

ALTERNATIVE MATCHES (for HR triangulation):
- alternative_role: the second-best matching role WITHIN the same primary career group.
  Use the search_roles tool to identify it. This gives HR a runner-up option within
  the same occupational family. Set to null only if there is genuinely no other
  reasonable role in that career group.
- alternative_group: You MUST always provide an alternative_group -- even if the position
  clearly belongs to one career group, identify the SECOND most likely career group and
  its best matching role. HR specialists use all three matches for triangulation. If
  confidence in the alternative group is very low (e.g., 10-20%), that is acceptable and
  informative -- it tells the HR specialist that the primary classification is strong.
  A null alternative_group is only acceptable if the position description is too vague
  to classify at all. In all other cases, provide the best role from a DIFFERENT career
  group than the primary.
- Both fields use their own independent confidence scores (1-100).
"""


def _parse_json_from_response(text):
    """Extract and parse JSON block from orchestrator response (CLI copy).

    Same logic as agent_classifier._parse_json_from_response -- duplicated
    here to avoid importing agent_classifier (which imports streamlit).
    """
    import re

    # Strategy 1: ```json ... ```
    m = re.search(r'```json\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 2: ``` ... ```
    m = re.search(r'```\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: outermost { ... }
    brace_start = text.find('{')
    if brace_start != -1:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start:i + 1])
                    except json.JSONDecodeError:
                        break

    return None


def _classify_for_cli(pd_text, api_key):
    """Classify one PD via the LangChain agent pipeline (no Streamlit).

    This is the CLI replacement for agent_classifier.classify_position().
    It initialises agents with plain Python caching, runs the orchestrator,
    and parses the JSON response into the same flat dict the spreadsheet
    expects.
    """
    import uuid
    import griffin_langchain_agents as gla
    from griffin_langchain_agents import HumanMessage

    orchestrator, llm = _init_cli_agents(api_key)

    prompt = HumanMessage(content=(
        "Classify the following position description into DHRM career "
        "groups and roles. Analyze duty areas and determine if this is "
        "a SINGLE or BLENDED classification (30% secondary threshold). "
        "Include pay band information.\n\n"
        f"Position Description:\n{pd_text}"
    ))

    config = {"configurable": {"thread_id": f"cli-batch-{uuid.uuid4().hex[:8]}"}}
    response = orchestrator.invoke({"messages": [prompt]}, config)
    raw_text = gla._content_to_str(response["messages"][-1].content)

    parsed = _parse_json_from_response(raw_text)
    if parsed is None:
        return None  # caller handles the failure

    primary = parsed.get("primary", {})
    return {
        "ai_career_group": primary.get("career_group_name", ""),
        "ai_role": primary.get("role_name", ""),
        "ai_confidence": primary.get("confidence", 0),
    }


def _classify_single(pd_text, api_key):
    """Run GRIFFIN classification on one PD text (CLI-safe).

    Combines:
      - ML prediction via extract_features + predict_occupational_family
        (no Streamlit dependency).
      - AI agent classification via _classify_for_cli (no Streamlit
        dependency).

    Returns a flat dict of columns to merge into the spreadsheet.
    """
    from feature_extraction import extract_features
    from ml_classifier import predict_occupational_family

    # ── ML prediction (always runs, zero API cost) ──
    features = extract_features(pd_text)
    ml_result = predict_occupational_family(features)

    ml_prediction = ""
    ml_confidence = 0
    occ_family = ""
    if ml_result:
        sorted_probs = sorted(
            ml_result["probabilities"].items(), key=lambda x: x[1], reverse=True,
        )
        ml_prediction = sorted_probs[0][0] if sorted_probs else ""
        ml_confidence = sorted_probs[0][1] if sorted_probs else 0
        occ_family = ml_prediction  # occupational family = top ML prediction

    # ── AI agent classification ──
    ai_result = _classify_for_cli(pd_text, api_key)

    ai_career_group = ""
    ai_role = ""
    ai_confidence = 0
    if ai_result:
        ai_career_group = ai_result.get("ai_career_group", "")
        ai_role = ai_result.get("ai_role", "")
        ai_confidence = ai_result.get("ai_confidence", 0)

    return {
        "ml_prediction": ml_prediction,
        "ml_confidence": ml_confidence,
        "ai_career_group": ai_career_group,
        "ai_role": ai_role,
        "ai_confidence": ai_confidence,
        "occ_family_suggested": occ_family,
    }


def _ai_clean_single(pd_text, api_key):
    """Send PD text through Gemini for PII/boilerplate cleaning.

    Returns a dict with cleaning columns.
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = AI_CLEAN_PROMPT + "\n\nPosition Description Text:\n" + pd_text

    try:
        response = model.generate_content(prompt)
        raw = response.text

        # Strip markdown fences if present
        cleaned_raw = raw.strip()
        if cleaned_raw.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = cleaned_raw.index("\n")
            cleaned_raw = cleaned_raw[first_newline + 1:]
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]
        cleaned_raw = cleaned_raw.strip()

        parsed = json.loads(cleaned_raw)

        pii_flags = "; ".join(parsed.get("pii_flags", []))
        cleaned_text = parsed.get("cleaned_text", pd_text)
        boilerplate = "; ".join(parsed.get("boilerplate_removed", []))
        is_valid = parsed.get("is_valid_pd", True)

        # Update status if it is not a valid PD
        status_note = ""
        if not is_valid:
            reason = parsed.get("invalid_reason", "not a position description")
            status_note = f"NOT_A_PD: {reason}"

        return {
            "pii_flags": pii_flags,
            "cleaned_text": cleaned_text,
            "boilerplate_removed": boilerplate,
            "ai_clean_status": status_note if status_note else "CLEANED",
        }

    except Exception as exc:
        return {
            "pii_flags": f"AI_CLEAN_ERROR: {exc}",
            "cleaned_text": pd_text,
            "boilerplate_removed": "",
            "ai_clean_status": f"CLEAN_FAILED: {exc}",
        }


def run_classify(input_path, api_key, ai_clean=False, delay=2):
    """Mode 2: classify extracted PDs and optionally AI-clean them."""
    if not os.path.isfile(input_path):
        print(f"ERROR: Spreadsheet not found: {input_path}")
        sys.exit(1)

    df = pd.read_excel(input_path, engine="openpyxl")

    required_cols = {"filename", "extracted_text", "char_count", "status"}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        print(f"ERROR: Spreadsheet missing columns: {missing}")
        sys.exit(1)

    total = len(df)
    print(f"Classifying {total} position descriptions...")
    if ai_clean:
        print("  AI cleaning enabled (--ai-clean)")
    if delay > 0:
        print(f"  Rate-limit delay: {delay}s between API calls")

    # Prepare new columns
    classify_cols = [
        "ml_prediction", "ml_confidence",
        "ai_career_group", "ai_role", "ai_confidence",
        "occ_family_suggested", "correct_label", "notes",
    ]
    clean_cols = ["pii_flags", "cleaned_text", "boilerplate_removed", "ai_clean_status"]

    for col in classify_cols:
        if col not in df.columns:
            df[col] = ""
    if ai_clean:
        for col in clean_cols:
            if col not in df.columns:
                df[col] = ""

    for idx, row in df.iterrows():
        fname = row["filename"]
        text = str(row["extracted_text"]).strip()
        current_status = str(row.get("status", "")).strip()

        # Skip already-failed extractions
        if current_status.startswith("EXTRACT_FAILED"):
            print(f"  [{idx+1}/{total}] SKIP (extraction failed): {fname}")
            continue

        # Skip empty text
        if not text or text == "nan":
            print(f"  [{idx+1}/{total}] SKIP (no text): {fname}")
            df.at[idx, "status"] = "CLASSIFY_FAILED: no extracted text"
            continue

        print(f"  [{idx+1}/{total}] Classifying: {fname} ...", end=" ", flush=True)

        # ---- Classification ----
        max_retries = 2
        classify_result = None
        for attempt in range(max_retries):
            try:
                classify_result = _classify_single(text, api_key)
                break
            except Exception as exc:
                if attempt < max_retries - 1:
                    print(f"retry ({exc})...", end=" ", flush=True)
                    time.sleep(delay)
                else:
                    print(f"FAILED ({exc})")
                    df.at[idx, "status"] = f"CLASSIFY_FAILED: {exc}"

        if classify_result:
            for col, val in classify_result.items():
                df.at[idx, col] = val

            # Pre-fill correct_label with the suggestion
            df.at[idx, "correct_label"] = classify_result.get(
                "occ_family_suggested", ""
            )
            df.at[idx, "status"] = "CLASSIFIED"
            conf = classify_result.get("ai_confidence", 0)
            print(f"OK (confidence: {conf}%)")

        # ---- AI Cleaning (optional) ----
        if ai_clean and classify_result:
            if delay > 0:
                time.sleep(delay)

            print(f"           AI cleaning: {fname} ...", end=" ", flush=True)
            try:
                clean_result = _ai_clean_single(text, api_key)
                for col, val in clean_result.items():
                    df.at[idx, col] = val

                pii_count = len([
                    f for f in str(clean_result.get("pii_flags", "")).split(";")
                    if f.strip() and "ERROR" not in f
                ])
                print(f"OK ({pii_count} PII flag(s))")
            except Exception as exc:
                print(f"FAILED ({exc})")

        # Rate-limit pause between documents
        if delay > 0 and idx < total - 1:
            time.sleep(delay)

    # Save updated spreadsheet
    df.to_excel(input_path, index=False, engine="openpyxl")
    print(f"\nUpdated spreadsheet: {input_path}")
    print("Next step: review predictions, set correct_label, mark status=APPROVED,")
    print("           then run --ingest.")


# ===========================================================================
# MODE 3: INGEST
# ===========================================================================
def run_ingest(input_path):
    """Mode 3: append approved PDs to training CSV."""
    if not os.path.isfile(input_path):
        print(f"ERROR: Spreadsheet not found: {input_path}")
        sys.exit(1)

    df = pd.read_excel(input_path, engine="openpyxl")

    # Filter to APPROVED rows
    if "status" not in df.columns:
        print("ERROR: Spreadsheet has no 'status' column.")
        sys.exit(1)

    approved = df[df["status"].astype(str).str.upper() == "APPROVED"].copy()

    if approved.empty:
        print("No rows with status=APPROVED found. Nothing to ingest.")
        print("Mark rows as APPROVED in the 'status' column first.")
        sys.exit(0)

    # Validate correct_label
    if "correct_label" not in approved.columns:
        print("ERROR: Spreadsheet has no 'correct_label' column.")
        sys.exit(1)

    invalid_labels = []
    for idx, row in approved.iterrows():
        label = str(row["correct_label"]).strip()
        if label not in VALID_JOB_FAMILIES:
            invalid_labels.append((row.get("filename", f"row {idx}"), label))

    if invalid_labels:
        print("ERROR: The following rows have invalid correct_label values:")
        for fname, label in invalid_labels:
            print(f"  {fname}: '{label}'")
        print()
        print("Valid labels are:")
        for lbl in sorted(VALID_JOB_FAMILIES):
            print(f"  {lbl}")
        sys.exit(1)

    # Load existing training data
    if not os.path.isfile(TRAINING_CSV):
        print(f"ERROR: Training CSV not found: {TRAINING_CSV}")
        sys.exit(1)

    training_df = pd.read_csv(TRAINING_CSV)
    original_count = len(training_df)

    # Build new rows matching the training CSV schema:
    #   censored_text, compensation_grade, job_profile_code,
    #   job_family, exempt_status, pay_type
    new_rows = []
    for _, row in approved.iterrows():
        # Use cleaned_text if available and non-empty, else extracted_text
        text = str(row.get("cleaned_text", "")).strip()
        if not text or text == "nan":
            text = str(row["extracted_text"]).strip()

        new_rows.append({
            "censored_text": text,
            "compensation_grade": "",        # HR fills later or left blank
            "job_profile_code": "",           # HR fills later or left blank
            "job_family": str(row["correct_label"]).strip(),
            "exempt_status": "",              # HR fills later or left blank
            "pay_type": "",                   # HR fills later or left blank
        })

    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([training_df, new_df], ignore_index=True)
    combined.to_csv(TRAINING_CSV, index=False)

    added = len(new_rows)
    new_total = len(combined)
    print(f"Added {added} new PD(s) to training data.")
    print(f"  Previous count: {original_count}")
    print(f"  New total:      {new_total}")
    print(f"  File: {TRAINING_CSV}")
    print()
    print("Run Notebook 4 then Notebook 5 to retrain the model with the new data.")


# ===========================================================================
# CLI entry point
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="GRIFFIN Batch Ingestion Utility -- add new PDs to training data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Workflow:
  Step 1: Extract text from documents
    python tools/batch_ingest.py --extract --input-dir "path/to/pd_folder" --output "batch_review.xlsx"

  Step 2: Classify (and optionally AI-clean)
    python tools/batch_ingest.py --classify --input "batch_review.xlsx" --api-key "AIzaSy..."
    python tools/batch_ingest.py --classify --input "batch_review.xlsx" --api-key "AIzaSy..." --ai-clean

  Step 3: Ingest approved PDs into training data
    python tools/batch_ingest.py --ingest --input "batch_review.xlsx"
""",
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--extract",
        action="store_true",
        help="Mode 1: extract text from .docx/.pdf files into a review spreadsheet",
    )
    mode_group.add_argument(
        "--classify",
        action="store_true",
        help="Mode 2: classify extracted PDs using GRIFFIN pipeline",
    )
    mode_group.add_argument(
        "--ingest",
        action="store_true",
        help="Mode 3: append approved PDs to training CSV",
    )

    # Shared arguments
    parser.add_argument(
        "--input-dir",
        type=str,
        help="(extract) Folder containing .docx/.pdf files",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="(classify/ingest) Path to the review spreadsheet (.xlsx)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="batch_review.xlsx",
        help="(extract) Output spreadsheet path (default: batch_review.xlsx)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="(classify) Gemini API key for classification and AI cleaning",
    )
    parser.add_argument(
        "--ai-clean",
        action="store_true",
        help="(classify) Also run AI-powered PII detection and boilerplate removal",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds between API calls (default: 2). Set 0 for enterprise keys.",
    )

    args = parser.parse_args()

    # ------- Route to the correct mode -------
    if args.extract:
        if not args.input_dir:
            parser.error("--extract requires --input-dir")
        run_extract(args.input_dir, args.output)

    elif args.classify:
        if not args.input:
            parser.error("--classify requires --input")
        if not args.api_key:
            parser.error("--classify requires --api-key")
        run_classify(args.input, args.api_key, ai_clean=args.ai_clean, delay=args.delay)

    elif args.ingest:
        if not args.input:
            parser.error("--ingest requires --input")
        run_ingest(args.input)


if __name__ == "__main__":
    main()
