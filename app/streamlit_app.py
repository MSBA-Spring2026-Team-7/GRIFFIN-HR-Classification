"""
GRIFFIN – Streamlit HR Classification & Pay Tool
=================================================
William & Mary Mason School of Business
BUAD 5722 / BUAD 5742 — Spring 2026

Streamlit frontend that classifies position descriptions into DHRM
career groups/roles and displays pay band information. Uses Google
Gemini for AI-powered classification and explanation.

Team 7: Steven Alvarado, Anmol Motwani, JR Jones, Brynn Vetrano
"""

import os
import re
import json
import streamlit as st
import pandas as pd

from feature_extraction import extract_features
from ml_classifier import predict_occupational_family

# ── Load API key (Streamlit Cloud Secrets first, then .env for local dev) ──
# Cloud: reads from st.secrets["GEMINI_API_KEY"] configured in the
# Streamlit Cloud Secrets UI. Local: reads from .env via python-dotenv.
# Supports both GEMINI_API_KEY (canonical) and GOOGLE_API_KEY (legacy) names.
try:
    from dotenv import load_dotenv
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

import google.generativeai as genai


def _load_gemini_api_key():
    """Resolve the Gemini API key from Streamlit Secrets or environment.

    Priority order:
      1. st.secrets["GEMINI_API_KEY"]  (Streamlit Cloud deployment)
      2. st.secrets["GOOGLE_API_KEY"]  (legacy name)
      3. os.environ["GEMINI_API_KEY"]  (local .env, canonical)
      4. os.environ["GOOGLE_API_KEY"]  (local .env, legacy)
    Returns empty string if none found; callers decide how to handle.
    """
    # Try st.secrets (may raise FileNotFoundError if no secrets.toml locally)
    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        try:
            val = st.secrets.get(key_name)
            if val:
                return val
        except (FileNotFoundError, KeyError, AttributeError):
            pass
    # Fall back to environment variables
    for key_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(key_name, "")
        if val:
            return val
    return ""


GOOGLE_API_KEY = _load_gemini_api_key()
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ── Data paths ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "reference")


# ============================================================
#  DATA LOADING
# ============================================================
@st.cache_data
def load_reference_data():
    """Load GRIFFIN reference data from xlsx files."""
    career_groups = pd.read_excel(
        os.path.join(DATA_DIR, "career_groups.xlsx"), engine="openpyxl"
    )
    roles = pd.read_excel(
        os.path.join(DATA_DIR, "roles.xlsx"), engine="openpyxl"
    )
    pay_bands = pd.read_excel(
        os.path.join(DATA_DIR, "dhrm_pay_bands.xlsx"), engine="openpyxl"
    )
    crosswalk = pd.read_excel(
        os.path.join(DATA_DIR, "crosswalk.xlsx"), engine="openpyxl"
    )
    wm_grades = pd.read_excel(
        os.path.join(DATA_DIR, "wm_pay_grades.xlsx"), engine="openpyxl"
    )
    return career_groups, roles, pay_bands, crosswalk, wm_grades


career_groups_df, roles_df, pay_bands_df, crosswalk_df, wm_grades_df = load_reference_data()


@st.cache_resource
def ensure_h2o_loaded():
    """Lazy-load the H2O model on first user request.

    Streamlit Cloud's free tier gives us ~1 GB RAM. Booting the H2O JVM at
    app import would consume most of that budget before the user does
    anything. This function is only called when the user clicks the
    "Load ML reference model" button. If H2O is unavailable (JVM not
    installed, OOM, etc.), the ml_classifier module falls back to sklearn.
    """
    from ml_classifier import _get_h2o_model, _ensure_sklearn_model
    model = _get_h2o_model()          # Boot JVM + load H2O model (cached in ml_classifier)
    _ensure_sklearn_model()           # Pre-train sklearn fallback if needed
    return model is not None


@st.cache_resource
def ensure_sklearn_only():
    """Pre-warm only the sklearn fallback (cheap, no JVM)."""
    from ml_classifier import _ensure_sklearn_model
    _ensure_sklearn_model()
    return True


# Warm up sklearn fallback at boot (~50 MB). Do NOT boot H2O here — see
# ensure_h2o_loaded() above. H2O loads only when the user explicitly opts in
# via the "Load ML reference model" button in the sidebar.
ensure_sklearn_only()


# ============================================================
#  HELPERS
# ============================================================
def clean_role_name(name):
    """Fix spacing issues like 'ServicesManager' -> 'Services Manager'."""
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', str(name)).strip()


def get_pay_info(band):
    """Look up salary range for a given pay band number."""
    if band is None or pd.isna(band):
        return None
    match = pay_bands_df[pay_bands_df["pay_band"] == int(band)]
    if len(match) > 0:
        return match.iloc[0]
    return None


def extract_salary_from_text(text):
    """Extract posted salary from position description text.

    Looks for patterns like 'up to $55,000', 'Salary: $50,000 - $65,000',
    '$45,000 commensurate with experience', 'Compensation Grade: S07', etc.
    Returns the salary figure most likely to represent the hiring target,
    or None if no salary is found.
    """
    if not text:
        return None
    # Pattern 1: "up to $XX,XXX" — hiring ceiling
    m = re.search(r'up\s+to\s+\$\s*([\d,]+)', text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(',', ''))
    # Pattern 2: "Salary- $XX,XXX" or "Salary: $XX,XXX"
    m = re.search(r'salary[\s\-:]+\$\s*([\d,]+)', text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(',', ''))
    # Pattern 3: salary range "$XX,XXX - $YY,YYY" — use the max as ceiling
    m = re.search(r'\$\s*([\d,]+)\s*(?:-|to|–)\s*\$\s*([\d,]+)', text, re.IGNORECASE)
    if m:
        return float(m.group(2).replace(',', ''))
    # Pattern 4: standalone "$XX,XXX" near salary-related keywords
    m = re.search(r'(?:salary|compensation|pay|commensurate)[^$]{0,30}\$\s*([\d,]+)', text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(',', ''))
    return None


def get_wm_grade(band, posted_salary=None):
    """Find the W&M pay grade using midpoint-to-midpoint matching.

    Strategy (in priority order):
    1. If a posted salary was extracted from the PD, find the grade whose
       midpoint is the closest ceiling (midpoint >= salary, or nearest match).
    2. Otherwise, use the DHRM pay band midpoint as the reference salary.

    The W&M midpoint functions as the practical hiring ceiling — new hires
    typically come in between min and midpoint for a grade.
    """
    # Determine the reference salary to match against
    ref_salary = posted_salary
    salary_source = "posted salary" if posted_salary else "DHRM band midpoint"

    if ref_salary is None:
        pay = get_pay_info(band)
        if pay is None:
            return None
        ref_salary = (pay['minimum_salary'] + pay['maximum_salary']) / 2

    # Filter to salaried grades only
    salaried = wm_grades_df[wm_grades_df['grade_type'] == 'salaried'].copy()
    if salaried.empty:
        return None

    # Midpoint-as-ceiling: find grades where midpoint >= ref_salary
    ceiling_grades = salaried[salaried['annual_midpoint'] >= ref_salary]
    if not ceiling_grades.empty:
        # Pick the lowest midpoint that's still >= ref_salary (tightest ceiling)
        best = ceiling_grades.loc[ceiling_grades['annual_midpoint'].idxmin()]
    else:
        # ref_salary exceeds all midpoints — pick the highest grade
        best = salaried.loc[salaried['annual_midpoint'].idxmax()]

    return {
        'wm_pay_grade': best['pay_grade'],
        'wm_min': best['annual_min'],
        'wm_midpoint': best['annual_midpoint'],
        'wm_max': best['annual_max'],
        'salary_source': salary_source
    }


def build_career_group_summary():
    """Build a compact summary of all career groups for the LLM prompt."""
    lines = []
    for _, row in career_groups_df.iterrows():
        lines.append(
            f"- {row['career_group_code']}: {row['career_group_name']} "
            f"(Family: {row['occupational_family']}, "
            f"Pay Bands {int(row['pay_band_min'])}-{int(row['pay_band_max'])})"
        )
    return "\n".join(lines)


def build_roles_for_group(group_code):
    """Build a summary of roles within a specific career group."""
    group_roles = roles_df[roles_df["career_group_code"] == group_code]
    if group_roles.empty:
        return "No roles found for this group."
    lines = []
    for _, row in group_roles.iterrows():
        name = clean_role_name(row["role_name"])
        lines.append(f"- {row['role_code']}: {name} (Pay Band {int(row['pay_band'])})")
    return "\n".join(lines)


# ============================================================
#  GEMINI CLASSIFICATION
# ============================================================
CLASSIFICATION_SYSTEM_PROMPT = f"""You are GRIFFIN, an HR classification specialist for Virginia DHRM positions at William & Mary.

You have access to the complete list of 56 DHRM career groups:

{build_career_group_summary()}

TASK: Given a position description, classify it into the most appropriate DHRM career group and role.

RESPONSE FORMAT: You MUST respond with valid JSON only. No markdown, no explanation outside the JSON.
{{
  "career_group_code": <integer code>,
  "career_group_name": "<name>",
  "confidence": <integer 1-100>,
  "reasoning": "<2-3 sentence explanation of why this classification fits>",
  "alternative_code": <integer code of second-best match or null>,
  "alternative_name": "<name of second-best match or null>"
}}"""


def classify_with_gemini(text):
    """Use Gemini to classify a position description into DHRM career groups."""
    try:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=CLASSIFICATION_SYSTEM_PROMPT
        )
        response = model.generate_content(
            f"Classify this position description:\n\n{text}",
            generation_config=genai.GenerationConfig(temperature=0.1)
        )

        # Parse JSON from response
        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        return result
    except Exception as e:
        return {"error": str(e)}


def find_best_role(group_code, text):
    """Use Gemini to pick the best role within a career group."""
    roles_list = build_roles_for_group(group_code)
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""Given this position description and the roles available in career group {group_code},
pick the single best matching role.

Position Description:
{text}

Available Roles:
{roles_list}

Respond with JSON only:
{{"role_code": <integer>, "role_name": "<name>", "reasoning": "<1 sentence>"}}"""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.1)
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def find_top_roles(group_code, text, n=2):
    """Use Gemini to pick the top N roles within a career group."""
    roles_list = build_roles_for_group(group_code)
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""Given this position description and the roles available in career group {group_code},
pick the top {n} best matching roles, ranked from best to worst match.

Position Description:
{text}

Available Roles:
{roles_list}

Respond with a JSON array only (no markdown, no explanation):
[{{"role_code": <integer>, "role_name": "<name>", "confidence": <integer 1-100>, "reasoning": "<1 sentence>"}}, ...]

Return exactly {n} roles. If fewer than {n} roles exist, return all available roles."""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.1)
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        return result if isinstance(result, list) else [result]
    except Exception as e:
        return [{"error": str(e)}]


def generate_explanation(text, role_name, career_group_name, reasoning):
    """Generate a detailed AI explanation for the classification."""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""You are an HR classification expert at William & Mary.

A position description has been classified as:
- Career Group: {career_group_name}
- Role: {role_name}
- Initial reasoning: {reasoning}

Position Description:
{text}

Write 3-4 sentences explaining why this position matches that classification.
Be specific, professional, and HR-focused. Reference actual duties from the description
and how they map to the DHRM classification criteria (Complexity, Results, Accountability)."""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI explanation unavailable: {e}"


# ============================================================
#  STREAMLIT PAGE CONFIG & THEME
# ============================================================
st.set_page_config(
    page_title="GRIFFIN - W&M HR Classification Tool",
    page_icon="\U0001f3db\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Open+Sans:wght@300;400;500;600&display=swap');

* { box-sizing: border-box; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; max-width: 1100px; }

/* Banner */
.griffin-banner {
    background: #115740;
    border-bottom: 4px solid #C99700;
    padding: 32px 48px 24px;
    margin-bottom: 32px;
}
.griffin-banner-inner {
    display: flex;
    align-items: center;
    gap: 20px;
}
.griffin-logo { font-size: 2.8rem; line-height: 1; }
.griffin-title {
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: #F5F0E8;
    margin: 0;
    letter-spacing: 1px;
}
.griffin-subtitle {
    font-family: 'Open Sans', sans-serif;
    font-size: 0.82rem;
    font-weight: 300;
    color: #C99700;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin: 4px 0 0 0;
}

/* Section labels */
.section-label {
    font-family: 'Open Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #115740;
    margin-bottom: 8px;
    padding-left: 2px;
}

/* Results header */
.results-header {
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #115740;
    border-bottom: 2px solid #C99700;
    padding-bottom: 8px;
    margin: 28px 0 20px 0;
}

/* Gold divider */
.gold-divider {
    border: none;
    border-top: 1.5px solid #C99700;
    margin: 28px 0;
    opacity: 0.5;
}

/* Match cards */
.match-card {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 22px 26px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #DDD8C8;
    transition: box-shadow 0.2s ease;
}
.match-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.10); }
.top-match {
    border: 1px solid #DDD8C8;
    border-left: 5px solid #115740;
}
.alt-match {
    border: 1px solid #DDD8C8;
    border-left: 5px solid #C99700;
    opacity: 0.95;
}
.third-match {
    border: 1px solid #DDD8C8;
    border-left: 5px solid #AAAAAA;
    opacity: 0.90;
}

/* Card header row */
.card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}
.card-medal { font-size: 1.5rem; line-height: 1; }
.card-role-name {
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: #115740;
    flex: 1;
}
.card-badge {
    font-family: 'Open Sans', sans-serif;
    font-size: 0.75rem;
    color: #666;
    background: #F0EBE0;
    border: 1px solid #DDD8C8;
    padding: 4px 12px;
    border-radius: 20px;
    white-space: nowrap;
}
.top-badge {
    background: #E8F2EE;
    color: #115740;
    border-color: #115740;
    font-weight: 600;
}

/* Confidence bar (custom) */
.conf-bar-wrap { margin-bottom: 14px; }
.conf-label {
    font-family: 'Open Sans', sans-serif;
    font-size: 0.72rem;
    color: #888;
    margin-bottom: 4px;
}
.conf-bar-bg {
    background: #EDE8DA;
    border-radius: 4px;
    height: 5px;
    overflow: hidden;
}
.conf-bar-fill {
    height: 5px;
    border-radius: 4px;
}

/* Data pills row */
.data-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
}
.data-pill {
    font-family: 'Open Sans', sans-serif;
    font-size: 0.82rem;
    background: #F7F4EE;
    border: 1px solid #DDD8C8;
    border-radius: 6px;
    padding: 5px 12px;
    color: #333;
}
.data-pill b { color: #115740; }

/* AI Explanation block */
.ai-block {
    background: #F0F7F4;
    border: 1px solid #B8D8CC;
    border-radius: 6px;
    padding: 14px 16px;
    margin-top: 12px;
}
.ai-block-label {
    font-family: 'Open Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #115740;
    margin-bottom: 6px;
}
.ai-block-text {
    font-family: 'Open Sans', sans-serif;
    font-size: 0.88rem;
    color: #2D2D2D;
    line-height: 1.7;
    margin: 0;
}

/* Footer */
.griffin-footer {
    text-align: center;
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 1.0rem;
    font-weight: 700;
    color: #115740;
    margin-top: 48px;
    padding: 20px 0 32px;
    border-top: 2px solid #C99700;
    letter-spacing: 0.5px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
#  BANNER
# ============================================================
st.markdown("""
<div class="griffin-banner">
    <div class="griffin-banner-inner">
        <div class="griffin-logo">\U0001f3db\ufe0f</div>
        <div>
            <div class="griffin-title">GRIFFIN</div>
            <div class="griffin-subtitle">William &amp; Mary &nbsp;&middot;&nbsp; HR Position Classification &amp; Pay Tool</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
#  INPUT SECTION
# ============================================================
st.markdown('<div class="section-label">Step 1 \u2014 Paste Position Description</div>',
            unsafe_allow_html=True)

input_text = st.text_area(
    label="",
    height=200,
    placeholder=(
        "Paste a position description here...\n\n"
        "Example: Finance manager responsible for budget planning, financial reporting,\n"
        "general ledger management, accounts payable oversight, and internal audit compliance.\n\n"
        "Tip: Use  ---  on its own line to classify multiple PDs at once."
    )
)

# Classification mode
mode = st.radio(
    "Classification Mode",
    options=["Full Analysis", "Fast Mode"],
    horizontal=True,
    help="Full Analysis uses both ML and Gemini AI (slower, more detailed). Fast Mode uses ML only (instant, no API cost)."
)

if mode == "Full Analysis":
    st.caption("ML prediction + Gemini AI classification with 3 ranked role matches and detailed rationale. Uses API tokens.")
else:
    st.caption("ML prediction only — instant results, zero API cost. Shows occupational family with confidence scores.")

col_btn, col_toggle, col_note = st.columns([1.2, 1.5, 3])
with col_btn:
    run = st.button("Classify PD")
with col_toggle:
    use_ai_explanation = st.toggle("AI Explanation", value=True,
                                   disabled=(mode == "Fast Mode"))
with col_note:
    st.caption("Separate multiple PDs with `---` on its own line.")

# ============================================================
#  CLASSIFICATION RESULTS
# ============================================================
MEDALS = ["\U0001f947", "\U0001f948", "\U0001f949"]
BAR_COLORS = ["#115740", "#C99700", "#AAAAAA"]
CARD_CLASSES = ["top-match", "alt-match", "third-match"]
BADGE_LABELS = ["Best Match", "Alternative Role", "Alternative Group"]
BADGE_CLASSES = ["top-badge", "card-badge", "card-badge"]


def _render_match_card(medal, role_name, badge_label, badge_class, card_class,
                       bar_color, confidence, career_group_label, band,
                       pay, wm, reasoning=None):
    """Render a single match card with Anmol-style layout."""
    # Build pay strings
    salary_min = f"${pay['minimum_salary']:,.0f}" if pay is not None else "N/A"
    salary_max = f"${pay['maximum_salary']:,.0f}" if pay is not None else "N/A"
    salary_range = f"{salary_min} \u2013 {salary_max}"
    band_display = str(band) if band else "N/A"
    if wm is not None:
        wm_source = wm.get('salary_source', 'DHRM band midpoint')
        wm_grade = f"{wm['wm_pay_grade']} (${wm['wm_min']:,.0f} &ndash; ${wm['wm_max']:,.0f}) &mdash; <em>matched via {wm_source}</em>"
    else:
        wm_grade = "N/A"

    # Confidence bar width
    bar_pct = min(max(confidence, 0), 100)

    card_html = f"""
    <div class="match-card {card_class}">
        <div class="card-header">
            <span class="card-medal">{medal}</span>
            <span class="card-role-name">{role_name}</span>
            <span class="card-badge {badge_class}">{badge_label}</span>
        </div>
        <div class="conf-bar-wrap">
            <div class="conf-label">AI Confidence: {confidence}%</div>
            <div class="conf-bar-bg">
                <div class="conf-bar-fill" style="width:{bar_pct}%;background:{bar_color}"></div>
            </div>
        </div>
        <div class="data-pills">
            <span class="data-pill"><b>Career Group:</b> {career_group_label}</span>
            <span class="data-pill"><b>Pay Band:</b> {band_display}</span>
            <span class="data-pill"><b>Salary Range:</b> {salary_range}</span>
            <span class="data-pill"><b>W&amp;M Grade:</b> {wm_grade}</span>
        </div>
        {"<div style='font-family:Open Sans,sans-serif;font-size:0.85rem;color:#555;line-height:1.6;margin-top:4px'><em>" + reasoning + "</em></div>" if reasoning else ""}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def _lookup_role_details(role_code, posted_salary=None):
    """Look up pay band, pay info, and W&M grade for a role code."""
    band, pay, wm = None, None, None
    if role_code:
        role_row = roles_df[roles_df["role_code"] == role_code]
        if not role_row.empty:
            band = int(role_row.iloc[0]["pay_band"])
    pay = get_pay_info(band)
    wm = get_wm_grade(band, posted_salary=posted_salary)
    return band, pay, wm


if run:
    if not input_text.strip():
        st.warning("Please paste a job description before classifying.")
    else:
        # API key check — only required for Full Analysis mode
        if not GOOGLE_API_KEY and mode == "Full Analysis":
            st.error(
                "Gemini API key not found. Set `GEMINI_API_KEY` in Streamlit "
                "Cloud Secrets (cloud deploy) or in a `.env` file at the "
                "project root (local dev). Switch to Fast Mode to run "
                "ML-only classification without an API key."
            )
            st.stop()

        jobs = [j.strip() for j in input_text.split("---") if j.strip()]

        for job_idx, job in enumerate(jobs):

            # Extract posted salary from PD for W&M grade matching
            posted_salary = extract_salary_from_text(job)

            # ML Prediction (local -- no API cost) — runs in BOTH modes
            with st.spinner("Running ML classification..."):
                features = extract_features(job)
                ml_result = predict_occupational_family(features)

            # ── Full Analysis: Gemini classification ──
            classification = None
            if mode == "Full Analysis":
                with st.spinner(f"Classifying position{f' {job_idx+1}' if len(jobs) > 1 else ''} with Gemini AI..."):
                    classification = classify_with_gemini(job)

                if "error" in classification:
                    st.error(f"Classification failed: {classification['error']}")
                    continue

            # Section header
            label = f"Results \u2014 Position {job_idx+1}" if len(jobs) > 1 else "Classification Results"
            st.markdown(f'<div class="results-header">{label}</div>', unsafe_allow_html=True)

            if posted_salary:
                st.markdown(f'<div style="font-family:Open Sans,sans-serif; font-size:0.82rem; color:#555; margin-bottom:12px;">\U0001f4cb <b>Posted salary detected:</b> ${posted_salary:,.0f} &mdash; used for W&amp;M grade matching (midpoint-as-ceiling method)</div>', unsafe_allow_html=True)

            # Show input preview
            with st.expander("Position description used", expanded=False):
                st.write(job)

            # ══════════════════════════════════════════════════
            #  FAST MODE — ML-only results
            # ══════════════════════════════════════════════════
            if mode == "Fast Mode":
                if ml_result:
                    sorted_probs = sorted(ml_result['probabilities'].items(),
                                          key=lambda x: x[1], reverse=True)
                    top_pred = sorted_probs[0]

                    # Enhanced ML-only primary card
                    st.markdown(f"""
                    <div class="match-card top-match">
                        <div class="card-header">
                            <span class="card-medal">\U0001f3c5</span>
                            <span class="card-role-name">{top_pred[0]}</span>
                            <span class="card-badge top-badge">ML Prediction</span>
                        </div>
                        <div class="conf-bar-wrap">
                            <div class="conf-label">ML Confidence: {top_pred[1]}%</div>
                            <div class="conf-bar-bg">
                                <div class="conf-bar-fill" style="width:{top_pred[1]}%;background:#C99700"></div>
                            </div>
                        </div>
                        <div class="data-pills">
                            <span class="data-pill"><b>Method:</b> {ml_result['method']}</span>
                            <span class="data-pill"><b>Occupational Family:</b> {top_pred[0]}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # W&M grade lookup from ML prediction
                    # Map top occupational family back to career group to find a pay band
                    ml_family = top_pred[0]
                    ml_cg_match = career_groups_df[
                        career_groups_df['occupational_family'].str.lower() == ml_family.lower()
                    ]
                    if not ml_cg_match.empty:
                        ml_band_min = int(ml_cg_match.iloc[0]['pay_band_min'])
                        ml_band_max = int(ml_cg_match.iloc[0]['pay_band_max'])
                        ml_band_mid = (ml_band_min + ml_band_max) // 2
                        ml_pay = get_pay_info(ml_band_mid)
                        ml_wm = get_wm_grade(ml_band_mid, posted_salary=posted_salary)

                        if ml_pay is not None or ml_wm is not None:
                            pay_str = f"${ml_pay['minimum_salary']:,.0f} \u2013 ${ml_pay['maximum_salary']:,.0f}" if ml_pay is not None else "N/A"
                            wm_str = f"{ml_wm['wm_pay_grade']} (${ml_wm['wm_min']:,.0f} \u2013 ${ml_wm['wm_max']:,.0f})" if ml_wm is not None else "N/A"
                            st.markdown(f"""
                            <div style="background:#FFFFFF; border:1px solid #DDD8C8; border-left:4px solid #115740; border-radius:8px; padding:14px 18px; margin-bottom:16px;">
                                <div style="font-family:'Open Sans',sans-serif; font-size:0.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#115740; margin-bottom:8px;">Estimated Pay (from ML Family Match)</div>
                                <div class="data-pills">
                                    <span class="data-pill"><b>Career Group:</b> {ml_cg_match.iloc[0]['career_group_code']} - {ml_cg_match.iloc[0]['career_group_name']}</span>
                                    <span class="data-pill"><b>Pay Band Range:</b> {ml_band_min}\u2013{ml_band_max}</span>
                                    <span class="data-pill"><b>DHRM Salary (Band {ml_band_mid}):</b> {pay_str}</span>
                                    <span class="data-pill"><b>W&amp;M Grade:</b> {wm_str}</span>
                                </div>
                                <div style="font-family:'Open Sans',sans-serif; font-size:0.75rem; color:#888; margin-top:6px;">
                                    <em>Estimated from midpoint of family pay band range. Use Full Analysis for role-specific pay data.</em>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                    # Show all probabilities as a mini table
                    st.markdown("**All Occupational Family Probabilities:**")
                    for cls, pct in sorted_probs:
                        bar_width = max(pct, 1)
                        st.markdown(f"""
                        <div style="display:flex; align-items:center; gap:8px; margin:4px 0; font-family:'Open Sans',sans-serif; font-size:0.82rem;">
                            <span style="width:280px; color:#2D2D2D;">{cls}</span>
                            <div style="flex:1; background:#EDE8DA; border-radius:3px; height:12px; overflow:hidden;">
                                <div style="width:{bar_width}%; background:{'#115740' if pct > 10 else '#C99700'}; height:12px; border-radius:3px;"></div>
                            </div>
                            <span style="width:50px; text-align:right; color:#555; font-weight:600;">{pct}%</span>
                        </div>
                        """, unsafe_allow_html=True)

                    # Note about upgrading to Full Analysis
                    st.info("For specific role matching, pay band details, and AI-powered rationale, switch to **Full Analysis** mode.")
                else:
                    st.error("ML classification returned no results.")

                if job_idx < len(jobs) - 1:
                    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
                continue  # Skip Gemini logic entirely in Fast Mode

            # ══════════════════════════════════════════════════
            #  FULL ANALYSIS — ML panel (compact, as before)
            # ══════════════════════════════════════════════════
            if ml_result:
                sorted_probs = sorted(ml_result['probabilities'].items(),
                                      key=lambda x: x[1], reverse=True)
                top_pred = sorted_probs[0]
                method_label = ml_result['method']

                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #DDD8C8; border-left:4px solid #C99700; border-radius:8px; padding:14px 18px; margin-bottom:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-family:'Open Sans',sans-serif; font-size:0.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#C99700;">ML Classification ({method_label})</span>
                        <span style="font-family:'Open Sans',sans-serif; font-size:0.68rem; color:#888;">Local prediction &mdash; no API cost</span>
                    </div>
                    <div style="font-family:'Open Sans',sans-serif; font-size:0.92rem; color:#2D2D2D;">
                        <strong>Predicted Family:</strong> {top_pred[0]} ({top_pred[1]}% confidence)
                    </div>
                    <div style="font-family:'Open Sans',sans-serif; font-size:0.78rem; color:#666; margin-top:6px;">
                        {' &middot; '.join(f'{cls}: {pct}%' for cls, pct in sorted_probs[:4])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ── Gather Gemini classification data ──
            primary_code = classification.get("career_group_code")
            primary_name = classification.get("career_group_name", "Unknown")
            confidence = classification.get("confidence", 0)
            reasoning = classification.get("reasoning", "")
            alt_code = classification.get("alternative_code")
            alt_name = classification.get("alternative_name")

            # ── Step 2: Find top 2 roles in primary career group ──
            with st.spinner("Matching to specific roles..."):
                primary_roles = find_top_roles(primary_code, job, n=2)

            # ── Step 3: Find best role in alternative career group (if exists) ──
            alt_role_result = None
            if alt_code and alt_name:
                with st.spinner("Checking alternative career group..."):
                    alt_role_result = find_best_role(alt_code, job)
                    if "error" in alt_role_result:
                        alt_role_result = None

            # ══════════════════════════════════════════════════
            #  CARD 1: Best Match (top role in primary group)
            # ══════════════════════════════════════════════════
            if primary_roles and "error" not in primary_roles[0]:
                r1 = primary_roles[0]
                r1_name = clean_role_name(r1.get("role_name", "Unknown"))
                r1_code = r1.get("role_code")
                r1_conf = r1.get("confidence", confidence)
                r1_reasoning = r1.get("reasoning", reasoning)
                r1_band, r1_pay, r1_wm = _lookup_role_details(r1_code, posted_salary=posted_salary)

                _render_match_card(
                    medal=MEDALS[0],
                    role_name=r1_name,
                    badge_label=BADGE_LABELS[0],
                    badge_class=BADGE_CLASSES[0],
                    card_class=CARD_CLASSES[0],
                    bar_color=BAR_COLORS[0],
                    confidence=r1_conf,
                    career_group_label=f"{primary_code} - {primary_name}",
                    band=r1_band,
                    pay=r1_pay,
                    wm=r1_wm,
                    reasoning=r1_reasoning,
                )

                # AI detailed explanation for top match only
                if use_ai_explanation:
                    with st.spinner("Generating detailed AI explanation..."):
                        explanation = generate_explanation(
                            job, r1_name, primary_name, reasoning
                        )
                    # Convert markdown **bold** to HTML <strong> for raw HTML rendering
                    explanation_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', explanation)
                    st.markdown(
                        f'<div class="ai-block">'
                        f'<div class="ai-block-label">AI Classification Rationale</div>'
                        f'<p class="ai-block-text">{explanation_html}</p>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.error("Could not determine a matching role in the primary career group.")

            # ══════════════════════════════════════════════════
            #  CARD 2: Alternative Role (2nd role in primary group)
            # ══════════════════════════════════════════════════
            if len(primary_roles) >= 2 and "error" not in primary_roles[1]:
                r2 = primary_roles[1]
                r2_name = clean_role_name(r2.get("role_name", "Unknown"))
                r2_code = r2.get("role_code")
                r2_conf = r2.get("confidence", confidence - 10 if confidence > 10 else confidence)
                r2_reasoning = r2.get("reasoning", "")
                r2_band, r2_pay, r2_wm = _lookup_role_details(r2_code, posted_salary=posted_salary)

                _render_match_card(
                    medal=MEDALS[1],
                    role_name=r2_name,
                    badge_label=BADGE_LABELS[1],
                    badge_class=BADGE_CLASSES[1],
                    card_class=CARD_CLASSES[1],
                    bar_color=BAR_COLORS[1],
                    confidence=r2_conf,
                    career_group_label=f"{primary_code} - {primary_name}",
                    band=r2_band,
                    pay=r2_pay,
                    wm=r2_wm,
                    reasoning=r2_reasoning,
                )

            # ══════════════════════════════════════════════════
            #  CARD 3: Alternative Group (best role in alt group)
            # ══════════════════════════════════════════════════
            if alt_role_result and alt_code and alt_name:
                r3_name = clean_role_name(alt_role_result.get("role_name", "Unknown"))
                r3_code = alt_role_result.get("role_code")
                # Alt group confidence is lower than primary
                r3_conf = max(confidence - 20, 10)
                r3_reasoning = alt_role_result.get("reasoning", "")
                r3_band, r3_pay, r3_wm = _lookup_role_details(r3_code, posted_salary=posted_salary)

                _render_match_card(
                    medal=MEDALS[2],
                    role_name=r3_name,
                    badge_label=BADGE_LABELS[2],
                    badge_class=BADGE_CLASSES[2],
                    card_class=CARD_CLASSES[2],
                    bar_color=BAR_COLORS[2],
                    confidence=r3_conf,
                    career_group_label=f"{alt_code} - {alt_name}",
                    band=r3_band,
                    pay=r3_pay,
                    wm=r3_wm,
                    reasoning=r3_reasoning,
                )

            if job_idx < len(jobs) - 1:
                st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

        # ── Methodology info box (after all cards) ──
        st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
        ml_method_str = ml_result['method'] if ml_result else 'unavailable'

        if mode == "Fast Mode":
            st.markdown(f"""
<div style="background:#F0F7F4; border:1px solid #B8D8CC; border-radius:8px; padding:16px 20px; margin:20px 0;">
    <div style="font-family:'Open Sans',sans-serif; font-size:0.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#115740; margin-bottom:8px;">Fast Mode &mdash; ML Classification</div>
    <div style="font-family:'Open Sans',sans-serif; font-size:0.85rem; color:#2D2D2D; line-height:1.7;">
        <strong style="color:#C99700;">ML ({ml_method_str}):</strong> Trained on 100 W&amp;M position descriptions with 15 engineered features. Predicts occupational family. Runs locally &mdash; zero API cost.<br><br>
        <em style="color:#555;">Fast Mode: ML classification only. For detailed role-level classification with AI rationale, switch to Full Analysis mode. Final authority rests with HR professionals.</em>
    </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div style="background:#F0F7F4; border:1px solid #B8D8CC; border-radius:8px; padding:16px 20px; margin:20px 0;">
    <div style="font-family:'Open Sans',sans-serif; font-size:0.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#115740; margin-bottom:8px;">Dual-Method Classification</div>
    <div style="font-family:'Open Sans',sans-serif; font-size:0.85rem; color:#2D2D2D; line-height:1.7;">
        <strong style="color:#C99700;">ML ({ml_method_str}):</strong> Trained on 100 W&amp;M position descriptions with 15 engineered features. Predicts occupational family. Runs locally &mdash; zero API cost.<br>
        <strong style="color:#115740;">Agentic AI (Gemini 2.5 Flash):</strong> Classifies against the full DHRM taxonomy (56 career groups, 294 roles) using LLM reasoning. Provides explainable rationale.<br><br>
        <em style="color:#555;">Both methods are advisory. When ML and AI agree, confidence is high. When they disagree, the classification warrants human review. Final authority rests with HR professionals.</em>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
#  SIDEBAR — DATA EXPLORER + ML MODEL CONTROL
# ============================================================
with st.sidebar:
    # ── ML Reference Model (H2O AutoML) — lazy load ──
    st.markdown("### ML Reference Model")
    if st.session_state.get("h2o_loaded"):
        st.success("H2O reference model loaded.")
    else:
        st.caption(
            "The sklearn classifier runs by default. Click below to also "
            "load the H2O AutoML reference model used in training "
            "(~30s first load, adds ~400 MB RAM)."
        )
        if st.button("Load ML reference model", key="load_ml_reference_model"):
            with st.spinner("Starting H2O cluster and loading GBM model..."):
                try:
                    ok = ensure_h2o_loaded()
                    if ok:
                        st.session_state["h2o_loaded"] = True
                        st.success("H2O reference model loaded. Re-run classification to use it.")
                    else:
                        st.warning(
                            "H2O unavailable in this environment. The app will "
                            "continue to use the sklearn fallback classifier."
                        )
                except Exception as e:
                    st.error(f"H2O load failed: {e}. Using sklearn fallback.")

    st.markdown("---")
    st.markdown("### GRIFFIN Data Explorer")
    st.caption(f"{len(career_groups_df)} career groups | {len(roles_df)} roles | {len(pay_bands_df)} pay bands")

    selected_group = st.selectbox(
        "Browse Career Group",
        options=career_groups_df["career_group_name"].tolist(),
        index=None,
        placeholder="Select a career group..."
    )

    if selected_group:
        group_row = career_groups_df[career_groups_df["career_group_name"] == selected_group].iloc[0]
        st.markdown(f"**Code:** {group_row['career_group_code']}")
        st.markdown(f"**Family:** {group_row['occupational_family']}")
        st.markdown(f"**Pay Bands:** {int(group_row['pay_band_min'])} - {int(group_row['pay_band_max'])}")

        group_roles = roles_df[roles_df["career_group_code"] == group_row["career_group_code"]]
        if not group_roles.empty:
            st.markdown("**Roles:**")
            for _, r in group_roles.iterrows():
                st.markdown(f"- {clean_role_name(r['role_name'])} (Band {int(r['pay_band'])})")

# ============================================================
#  FOOTER
# ============================================================
st.markdown("""
<div class="griffin-footer">
    GRIFFIN &nbsp;&middot;&nbsp; William &amp; Mary Mason School of Business
    &nbsp;&middot;&nbsp; HR Position Classification &amp; Pay Tool
    &nbsp;&middot;&nbsp; BUAD 5722 / BUAD 5742 &nbsp;&middot;&nbsp; Team 7
    <br><span style="font-size:0.65rem; color:#999;">Salary data: CareerOneStop, U.S. Department of Labor/ETA (careeronestop.org)</span>
</div>
""", unsafe_allow_html=True)
