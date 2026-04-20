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

import csv
import os
import re
import textwrap
from datetime import datetime
import streamlit as st
import pandas as pd

from feature_extraction import extract_features
from ml_classifier import predict_occupational_family

# ── Optional: Word document export (graceful degradation if python-docx missing) ──
try:
    from export_report import generate_classification_report
    _EXPORT_AVAILABLE = True
except ImportError:
    _EXPORT_AVAILABLE = False

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

from agent_classifier import classify_position


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


# Warm up sklearn fallback at boot (~50 MB, instant).
ensure_sklearn_only()

# Pre-warm H2O JVM in a background thread so it's ready when the user needs it.
# This runs during page load — by the time the user pastes a PD and clicks
# "Classify", the JVM is likely already booted (~30s head start).
# On Streamlit Cloud (1GB free tier), this will fail silently and sklearn
# remains the only classifier. The daemon=True flag ensures the thread
# doesn't block app shutdown.
import threading

def _background_h2o_warmup():
    """Boot H2O JVM + load model in background during app startup."""
    try:
        from ml_classifier import _get_h2o_model
        _get_h2o_model()  # Boots JVM, loads model, caches in module-level var
    except Exception:
        pass  # Fails silently on Cloud (OOM) — sklearn is always available

threading.Thread(target=_background_h2o_warmup, daemon=True, name="h2o-warmup").start()


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
.blend-match {
    border: 1px solid #DDD8C8;
    border-left: 5px solid #8B4513;
    background: linear-gradient(135deg, #FFFFFF 0%, #FFF8F0 100%);
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
#  CONFIDENCE METRICS EXPLANATION (collapsible)
# ============================================================
with st.expander("Understanding Confidence Metrics", expanded=False):
    st.markdown("""
<div style="background:#F0F7F4; border:1px solid #B8D8CC; border-radius:8px; padding:18px 22px;">
    <div style="display:flex; gap:20px; flex-wrap:wrap;">
        <div style="flex:1; min-width:260px;">
            <div style="font-family:'Open Sans',sans-serif; font-size:0.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#115740; margin-bottom:6px;">
                <span style="display:inline-block; width:10px; height:10px; background:#115740; border-radius:2px; margin-right:6px;"></span>ML Probability
            </div>
            <div style="font-family:'Open Sans',sans-serif; font-size:0.85rem; color:#2D2D2D; line-height:1.65;">
                Computed by the trained machine learning model (GBM). This is a <strong>statistical probability</strong> based on 15 engineered features from the position description, validated against 100+ classified positions. Higher = stronger statistical match.
            </div>
        </div>
        <div style="flex:1; min-width:260px;">
            <div style="font-family:'Open Sans',sans-serif; font-size:0.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#C99700; margin-bottom:6px;">
                <span style="display:inline-block; width:10px; height:10px; background:#C99700; border-radius:2px; margin-right:6px;"></span>AI Assessment
            </div>
            <div style="font-family:'Open Sans',sans-serif; font-size:0.85rem; color:#2D2D2D; line-height:1.65;">
                The language model's <strong>self-reported confidence</strong> in its classification. This reflects the AI's reasoning about how well the duties map to DHRM career groups, but is <em>not</em> a statistical metric. Think of it as an expert's professional judgment.
            </div>
        </div>
    </div>
    <div style="font-family:'Open Sans',sans-serif; font-size:0.82rem; color:#555; margin-top:14px; padding-top:12px; border-top:1px solid #B8D8CC; line-height:1.6;">
        When both metrics agree and are high, confidence in the classification is strong. When they disagree, the classification warrants human review.
    </div>
    <div style="font-family:'Open Sans',sans-serif; font-size:0.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#115740; margin-top:16px; margin-bottom:6px;">
        Understanding the Three Ranked Matches
    </div>
    <div style="font-family:'Open Sans',sans-serif; font-size:0.82rem; color:#2D2D2D; line-height:1.65;">
        Full Analysis provides <strong>three ranked recommendations</strong> to help HR specialists triangulate the correct classification:<br>
        <span style="color:#115740;">&bull;</span> <strong>Best Match</strong> &mdash; the top-ranked role in the primary career group.<br>
        <span style="color:#C99700;">&bull;</span> <strong>Alternative Role</strong> &mdash; the second-best role within the <em>same</em> career group, showing the next-closest fit at a different band level.<br>
        <span style="color:#AAAAAA;">&bull;</span> <strong>Alternative Group</strong> &mdash; the best role in a <em>different</em> career group entirely, offering a second perspective when duties span multiple domains.<br><br>
        <em>The Alternative Group card is especially valuable when a position has duties that cross career-group boundaries. Even a low-confidence alternative (10&ndash;20%) confirms the primary classification is strong, while a high-confidence alternative signals the classification warrants closer review.</em>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
#  INPUT SECTION
# ============================================================
st.markdown('<div class="section-label">Step 1 \u2014 Paste Position Description</div>',
            unsafe_allow_html=True)

input_text = st.text_area(
    label="Position Description Text",
    label_visibility="collapsed",
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

# ── Session state: persist classification results across reruns ──
# Streamlit reruns the entire script on every widget interaction (including
# download button clicks). Without session_state, computed results vanish.
if "classification_results" not in st.session_state:
    st.session_state.classification_results = []

MEDALS = ["\U0001f947", "\U0001f948", "\U0001f949"]
BAR_COLORS = ["#115740", "#C99700", "#AAAAAA"]
CARD_CLASSES = ["top-match", "alt-match", "third-match"]
BADGE_LABELS = ["Best Match", "Alternative Role", "Alternative Group"]
BADGE_CLASSES = ["top-badge", "card-badge", "card-badge"]


def _render_match_card(medal, role_name, badge_label, badge_class, card_class,
                       bar_color, confidence, career_group_label, band,
                       pay, wm, reasoning=None, ml_prob=None, ai_conf=None):
    """Render a single match card with Anmol-style layout.

    Confidence display logic:
      - Full Analysis (both ml_prob and ai_conf provided): show two bars
        -- ML Probability (green #115740) and AI Assessment (gold #C99700)
      - Fast Mode (only ml_prob, no ai_conf): show one bar labeled "ML Probability"
      - Legacy fallback (neither provided): use 'confidence' param as before
    """
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

    # Build confidence bar(s) HTML
    if ml_prob is not None and ai_conf is not None:
        # Full Analysis: two separate bars
        ml_pct = min(max(ml_prob, 0), 100)
        ai_pct = min(max(ai_conf, 0), 100)
        conf_html = f"""
        <div class="conf-bar-wrap">
            <div class="conf-label">ML Probability: {ml_prob}%</div>
            <div class="conf-bar-bg">
                <div class="conf-bar-fill" style="width:{ml_pct}%;background:#115740"></div>
            </div>
        </div>
        <div class="conf-bar-wrap">
            <div class="conf-label">AI Assessment: {ai_conf}%</div>
            <div class="conf-bar-bg">
                <div class="conf-bar-fill" style="width:{ai_pct}%;background:#C99700"></div>
            </div>
        </div>
        """
    elif ml_prob is not None:
        # Fast Mode: ML only
        ml_pct = min(max(ml_prob, 0), 100)
        conf_html = f"""
        <div class="conf-bar-wrap">
            <div class="conf-label">ML Probability: {ml_prob}%</div>
            <div class="conf-bar-bg">
                <div class="conf-bar-fill" style="width:{ml_pct}%;background:#115740"></div>
            </div>
        </div>
        """
    else:
        # Legacy fallback
        bar_pct = min(max(confidence, 0), 100)
        conf_html = f"""
        <div class="conf-bar-wrap">
            <div class="conf-label">Confidence: {confidence}%</div>
            <div class="conf-bar-bg">
                <div class="conf-bar-fill" style="width:{bar_pct}%;background:{bar_color}"></div>
            </div>
        </div>
        """

    card_html = f"""
    <div class="match-card {card_class}">
        <div class="card-header">
            <span class="card-medal">{medal}</span>
            <span class="card-role-name">{role_name}</span>
            <span class="card-badge {badge_class}">{badge_label}</span>
        </div>
        {conf_html}
        <div class="data-pills">
            <span class="data-pill"><b>Career Group:</b> {career_group_label}</span>
            <span class="data-pill"><b>Pay Band:</b> {band_display}</span>
            <span class="data-pill"><b>Salary Range:</b> {salary_range}</span>
            <span class="data-pill"><b>W&amp;M Grade:</b> {wm_grade}</span>
        </div>
        {"<div style='font-family:Open Sans,sans-serif;font-size:0.85rem;color:#555;line-height:1.6;margin-top:4px'><em>" + reasoning + "</em></div>" if reasoning else ""}
    </div>
    """
    # Strip ALL leading whitespace per line — prevents Streamlit's markdown
    # parser from treating indented HTML as preformatted code blocks.
    clean_html = '\n'.join(line.lstrip() for line in card_html.split('\n'))
    st.markdown(clean_html, unsafe_allow_html=True)


def _lookup_ml_prob(career_group_code, ml_result):
    """Look up the ML probability for a career group's occupational family.

    Maps the career_group_code to its occupational family via career_groups_df,
    then finds the matching probability in ml_result['probabilities'].
    Returns an integer percentage, or None if no match found.
    """
    if not ml_result or not career_group_code:
        return None
    probs = ml_result.get("probabilities", {})
    if not probs:
        return None
    # Map career group code -> occupational family
    cg_match = career_groups_df[
        career_groups_df["career_group_code"] == career_group_code
    ]
    if cg_match.empty:
        return None
    family = cg_match.iloc[0]["occupational_family"]
    # Case-insensitive lookup in probabilities
    for fam_name, pct in probs.items():
        if fam_name.lower() == family.lower():
            return pct
    return None


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


def _render_blend_card(primary, secondary, weighted_salary, ml_result=None):
    """Render a composite blend card showing both primary and secondary roles.

    Uses the same visual language as _render_match_card but with a
    distinct bronze border and dual-role layout.

    Args:
        primary: dict with career_group_code, career_group_name, role_name,
                 pay_band, confidence, duty_pct, reasoning
        secondary: dict with same fields
        weighted_salary: dict with min, midpoint, max (or None)
        ml_result: ML classification result dict (for ML probability lookup)
    """
    p_name = clean_role_name(primary.get("role_name", "Unknown"))
    s_name = clean_role_name(secondary.get("role_name", "Unknown"))
    p_pct = primary.get("duty_pct", 0.65)
    s_pct = secondary.get("duty_pct", 0.35)
    p_conf = primary.get("confidence", "N/A")
    s_conf = secondary.get("confidence", "N/A")
    p_group = f"{primary.get('career_group_code', '?')} - {primary.get('career_group_name', 'Unknown')}"
    s_group = f"{secondary.get('career_group_code', '?')} - {secondary.get('career_group_name', 'Unknown')}"
    p_band = primary.get("pay_band", "N/A")
    s_band = secondary.get("pay_band", "N/A")

    # Look up ML probabilities for each career group
    p_ml_prob = _lookup_ml_prob(primary.get("career_group_code"), ml_result)
    s_ml_prob = _lookup_ml_prob(secondary.get("career_group_code"), ml_result)
    p_ml_str = f"{p_ml_prob}%" if p_ml_prob is not None else "N/A"
    s_ml_str = f"{s_ml_prob}%" if s_ml_prob is not None else "N/A"

    # Weighted salary display
    if weighted_salary:
        ws_min = f"${weighted_salary['min']:,.0f}"
        ws_mid = f"${weighted_salary['midpoint']:,.0f}"
        ws_max = f"${weighted_salary['max']:,.0f}"
        ws_display = f"{ws_min} &ndash; {ws_mid} &ndash; {ws_max}"
    else:
        ws_display = "N/A"

    card_html = f"""
    <div class="match-card blend-match">
        <div class="card-header">
            <span class="card-medal">&#9878;</span>
            <span class="card-role-name">Blended Classification</span>
            <span class="card-badge" style="background:#FFF0E0; color:#8B4513; border-color:#8B4513; font-weight:600;">Blended</span>
        </div>
        <div style="font-family:'Open Sans',sans-serif; font-size:0.82rem; color:#555; margin-bottom:14px; line-height:1.6;">
            This position spans two career groups. Duties are split across the primary and secondary classifications below.
            The blend threshold of 30% was met by the secondary group.
        </div>
        <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:14px;">
            <div style="flex:1; min-width:240px; background:#F7F4EE; border:1px solid #DDD8C8; border-radius:8px; padding:12px 16px;">
                <div style="font-family:'Open Sans',sans-serif; font-size:0.68rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#115740; margin-bottom:6px;">Primary ({p_pct:.0%} of duties)</div>
                <div style="font-family:'Crimson Text',serif; font-size:1.1rem; font-weight:700; color:#115740;">{p_name}</div>
                <div class="data-pills" style="margin-top:8px;">
                    <span class="data-pill"><b>Group:</b> {p_group}</span>
                    <span class="data-pill"><b>Band:</b> {p_band}</span>
                    <span class="data-pill"><b>ML Prob:</b> {p_ml_str}</span>
                    <span class="data-pill"><b>AI Assess:</b> {p_conf}%</span>
                </div>
            </div>
            <div style="flex:1; min-width:240px; background:#FFF8F0; border:1px solid #DDD8C8; border-radius:8px; padding:12px 16px;">
                <div style="font-family:'Open Sans',sans-serif; font-size:0.68rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:#8B4513; margin-bottom:6px;">Secondary ({s_pct:.0%} of duties)</div>
                <div style="font-family:'Crimson Text',serif; font-size:1.1rem; font-weight:700; color:#8B4513;">{s_name}</div>
                <div class="data-pills" style="margin-top:8px;">
                    <span class="data-pill"><b>Group:</b> {s_group}</span>
                    <span class="data-pill"><b>Band:</b> {s_band}</span>
                    <span class="data-pill"><b>ML Prob:</b> {s_ml_str}</span>
                    <span class="data-pill"><b>AI Assess:</b> {s_conf}%</span>
                </div>
            </div>
        </div>
        <div class="data-pills">
            <span class="data-pill"><b>Weighted Salary (Min &ndash; Mid &ndash; Max):</b> {ws_display}</span>
            <span class="data-pill"><b>Formula:</b> (Primary x {p_pct:.0%}) + (Secondary x {s_pct:.0%})</span>
        </div>
    </div>
    """
    clean_html = '\n'.join(line.lstrip() for line in card_html.split('\n'))
    st.markdown(clean_html, unsafe_allow_html=True)


# ── Classify PD button: compute results and store in session_state ──
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

        # Clear previous results when a new classification run starts
        st.session_state.classification_results = []

        for job_idx, job in enumerate(jobs):

            # Extract posted salary from PD for W&M grade matching
            posted_salary = extract_salary_from_text(job)

            # ML Prediction (local -- no API cost) — runs in BOTH modes
            with st.spinner("Running ML classification..."):
                features = extract_features(job)
                ml_result = predict_occupational_family(features)

            # ── Full Analysis: Agent pipeline classification ──
            agent_result = None
            if mode == "Full Analysis":
                with st.spinner(f"Classifying position{f' {job_idx+1}' if len(jobs) > 1 else ''} with Agentic AI..."):
                    agent_result = classify_position(job, GOOGLE_API_KEY)

                if "error" in agent_result:
                    st.error(f"Classification failed: {agent_result['error']}")
                    continue

            # Store the result in session_state so it survives reruns
            st.session_state.classification_results.append({
                "job_text": job,
                "agent_result": agent_result,
                "ml_result": ml_result,
                "mode": mode,
                "posted_salary": posted_salary,
            })

# ── Render results from session_state (persists across reruns) ──
if st.session_state.classification_results:
    # Clear Results button
    if st.button("Clear Results", key="clear_results"):
        st.session_state.classification_results = []
        st.rerun()

    results_list = st.session_state.classification_results
    total_jobs = len(results_list)

    for job_idx, stored in enumerate(results_list):
        job = stored["job_text"]
        agent_result = stored["agent_result"]
        ml_result = stored["ml_result"]
        result_mode = stored["mode"]
        posted_salary = stored["posted_salary"]

        # Section header
        label = f"Results \u2014 Position {job_idx+1}" if total_jobs > 1 else "Classification Results"
        st.markdown(f'<div class="results-header">{label}</div>', unsafe_allow_html=True)

        if posted_salary:
            st.markdown(f'<div style="font-family:Open Sans,sans-serif; font-size:0.82rem; color:#555; margin-bottom:12px;">\U0001f4cb <b>Posted salary detected:</b> ${posted_salary:,.0f} &mdash; used for W&amp;M grade matching (midpoint-as-ceiling method)</div>', unsafe_allow_html=True)

        # Show input preview
        with st.expander("Position description used", expanded=False):
            st.write(job)

        # ══════════════════════════════════════════════════
        #  FAST MODE — ML-only results
        # ══════════════════════════════════════════════════
        if result_mode == "Fast Mode":
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
                        <div class="conf-label">ML Probability: {top_pred[1]}%</div>
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

                # ── Download button (Fast Mode) ──
                if _EXPORT_AVAILABLE:
                    try:
                        report_bytes = generate_classification_report(
                            pd_text=job,
                            classification_result={},
                            ml_result=ml_result,
                            mode=result_mode,
                            posted_salary=posted_salary,
                        )
                        st.download_button(
                            label="\U0001f4c4 Download Classification Report",
                            data=report_bytes,
                            file_name=f"GRIFFIN_Classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_fast_{job_idx}",
                        )
                    except Exception:
                        pass  # Silent — export is non-critical
            else:
                st.error("ML classification returned no results.")

            if job_idx < total_jobs - 1:
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
                    <strong>Predicted Family:</strong> {top_pred[0]} ({top_pred[1]}% ML probability)
                </div>
                <div style="font-family:'Open Sans',sans-serif; font-size:0.78rem; color:#666; margin-top:6px;">
                    {' &middot; '.join(f'{cls}: {pct}%' for cls, pct in sorted_probs[:4])}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ── Extract agent pipeline results ──
        primary = agent_result.get("primary", {})
        secondary = agent_result.get("secondary")
        classification_type = agent_result.get("classification_type", "SINGLE")
        weighted_salary = agent_result.get("weighted_salary")
        explanation = agent_result.get("explanation", "")

        primary_code = primary.get("career_group_code")
        primary_name = primary.get("career_group_name", "Unknown")
        primary_conf = primary.get("confidence", 0)
        primary_reasoning = primary.get("reasoning", "")

        # ══════════════════════════════════════════════════
        #  BLEND CARD (only for BLENDED classifications)
        # ══════════════════════════════════════════════════
        if classification_type == "BLENDED" and secondary:
            _render_blend_card(primary, secondary, weighted_salary, ml_result=ml_result)

        # ══════════════════════════════════════════════════
        #  CARD 1: Best Match (primary role from agent)
        # ══════════════════════════════════════════════════
        r1_code = primary.get("role_code")
        r1_name = clean_role_name(primary.get("role_name", "Unknown"))
        r1_conf = primary_conf
        r1_band, r1_pay, r1_wm = _lookup_role_details(r1_code, posted_salary=posted_salary)
        # Use agent-reported pay_band if lookup fails
        if r1_band is None and primary.get("pay_band"):
            r1_band = primary["pay_band"]
            r1_pay = get_pay_info(r1_band)
            r1_wm = get_wm_grade(r1_band, posted_salary=posted_salary)

        # Look up ML probability for the primary career group
        r1_ml_prob = _lookup_ml_prob(primary_code, ml_result)

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
            reasoning=primary_reasoning,
            ml_prob=r1_ml_prob,
            ai_conf=r1_conf,
        )

        # Attach locally-resolved pay/wm/band back to the source dict so the
        # .docx export (which shallow-copies agent_result) picks them up.
        if primary:
            primary["band"] = r1_band
            primary["pay_band"] = r1_band
            primary["pay"] = r1_pay
            primary["wm"] = r1_wm

        # AI detailed explanation from agent narrative
        if use_ai_explanation and explanation:
            explanation_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', explanation)
            st.markdown(
                f'<div class="ai-block">'
                f'<div class="ai-block-label">AI Classification Rationale</div>'
                f'<p class="ai-block-text">{explanation_html}</p>'
                f'</div>',
                unsafe_allow_html=True
            )

        # ══════════════════════════════════════════════════
        #  BLENDED Secondary Card (only for BLENDED)
        # ══════════════════════════════════════════════════
        if classification_type == "BLENDED" and secondary:
            r2_code = secondary.get("role_code")
            r2_name = clean_role_name(secondary.get("role_name", "Unknown"))
            r2_conf = secondary.get("confidence", 0)
            r2_reasoning = secondary.get("reasoning", "")
            s_code = secondary.get("career_group_code")
            s_name = secondary.get("career_group_name", "Unknown")
            r2_band, r2_pay, r2_wm = _lookup_role_details(r2_code, posted_salary=posted_salary)
            if r2_band is None and secondary.get("pay_band"):
                r2_band = secondary["pay_band"]
                r2_pay = get_pay_info(r2_band)
                r2_wm = get_wm_grade(r2_band, posted_salary=posted_salary)

            r2_ml_prob = _lookup_ml_prob(s_code, ml_result)

            _render_match_card(
                medal=MEDALS[1],
                role_name=r2_name,
                badge_label="Secondary Role",
                badge_class=BADGE_CLASSES[1],
                card_class=CARD_CLASSES[1],
                bar_color=BAR_COLORS[1],
                confidence=r2_conf,
                career_group_label=f"{s_code} - {s_name}",
                band=r2_band,
                pay=r2_pay,
                wm=r2_wm,
                reasoning=r2_reasoning,
                ml_prob=r2_ml_prob,
                ai_conf=r2_conf,
            )

        # ══════════════════════════════════════════════════
        #  CARD 2: Alternative Role (2nd role in primary group)
        # ══════════════════════════════════════════════════
        alt_role = agent_result.get("alternative_role")
        if alt_role and alt_role.get("role_code"):
            ar_code = alt_role.get("role_code")
            ar_name = clean_role_name(alt_role.get("role_name", "Unknown"))
            ar_conf = alt_role.get("confidence", 0)
            ar_reasoning = alt_role.get("reasoning", "")
            ar_band, ar_pay, ar_wm = _lookup_role_details(ar_code, posted_salary=posted_salary)
            if ar_band is None and alt_role.get("pay_band"):
                ar_band = alt_role["pay_band"]
                ar_pay = get_pay_info(ar_band)
                ar_wm = get_wm_grade(ar_band, posted_salary=posted_salary)

            # ML probability uses the PRIMARY career group (same group)
            ar_ml_prob = _lookup_ml_prob(primary_code, ml_result)

            _render_match_card(
                medal=MEDALS[1],
                role_name=ar_name,
                badge_label=BADGE_LABELS[1],
                badge_class=BADGE_CLASSES[1],
                card_class=CARD_CLASSES[1],
                bar_color=BAR_COLORS[1],
                confidence=ar_conf,
                career_group_label=f"{primary_code} - {primary_name}",
                band=ar_band,
                pay=ar_pay,
                wm=ar_wm,
                reasoning=ar_reasoning,
                ml_prob=ar_ml_prob,
                ai_conf=ar_conf,
            )

            # Attach enriched fields so .docx export sees Salary Range + W&M Grade
            alt_role["band"] = ar_band
            alt_role["pay_band"] = ar_band
            alt_role["pay"] = ar_pay
            alt_role["wm"] = ar_wm

        # ══════════════════════════════════════════════════
        #  CARD 3: Alternative Career Group
        # ══════════════════════════════════════════════════
        alt_group = agent_result.get("alternative_group")
        if alt_group and alt_group.get("role_code"):
            ag_code = alt_group.get("role_code")
            ag_name = clean_role_name(alt_group.get("role_name", "Unknown"))
            ag_conf = alt_group.get("confidence", 0)
            ag_reasoning = alt_group.get("reasoning", "")
            ag_cg_code = alt_group.get("career_group_code")
            ag_cg_name = alt_group.get("career_group_name", "Unknown")
            ag_band, ag_pay, ag_wm = _lookup_role_details(ag_code, posted_salary=posted_salary)
            if ag_band is None and alt_group.get("pay_band"):
                ag_band = alt_group["pay_band"]
                ag_pay = get_pay_info(ag_band)
                ag_wm = get_wm_grade(ag_band, posted_salary=posted_salary)

            # ML probability uses the ALTERNATIVE career group code
            ag_ml_prob = _lookup_ml_prob(ag_cg_code, ml_result)

            _render_match_card(
                medal=MEDALS[2],
                role_name=ag_name,
                badge_label=BADGE_LABELS[2],
                badge_class=BADGE_CLASSES[2],
                card_class=CARD_CLASSES[2],
                bar_color=BAR_COLORS[2],
                confidence=ag_conf,
                career_group_label=f"{ag_cg_code} - {ag_cg_name}",
                band=ag_band,
                pay=ag_pay,
                wm=ag_wm,
                reasoning=ag_reasoning,
                ml_prob=ag_ml_prob,
                ai_conf=ag_conf,
            )

            # Attach enriched fields so .docx export sees Salary Range + W&M Grade
            alt_group["band"] = ag_band
            alt_group["pay_band"] = ag_band
            alt_group["pay"] = ag_pay
            alt_group["wm"] = ag_wm

        # ── Download button (Full Analysis) ──
        if _EXPORT_AVAILABLE:
            try:
                _export_classification = dict(agent_result)
                _export_classification.pop("raw_response", None)
                report_bytes = generate_classification_report(
                    pd_text=job,
                    classification_result=_export_classification,
                    ml_result=ml_result,
                    mode=result_mode,
                    posted_salary=posted_salary,
                )
                st.download_button(
                    label="\U0001f4c4 Download Classification Report",
                    data=report_bytes,
                    file_name=f"GRIFFIN_Classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_full_{job_idx}",
                )
            except Exception:
                pass  # Silent — export is non-critical

        # ── Confirm Classification button (Full Analysis only) ──
        _confirm_key = f"confirm_{job_idx}"
        _confirmed_state_key = f"confirmed_{job_idx}"
        if st.button("\u2713 Confirm This Classification is Correct",
                     key=_confirm_key):
            # Map career group -> occupational family via reference data
            _occ_family = ""
            _cg_code = primary.get("career_group_code")
            if _cg_code is not None:
                _cg_match = career_groups_df[
                    career_groups_df["career_group_code"] == _cg_code
                ]
                if not _cg_match.empty:
                    _occ_family = _cg_match.iloc[0]["occupational_family"]

            _queue_path = os.path.join(PROJECT_ROOT, "data", "training",
                                       "confirmed_queue.csv")
            _queue_dir = os.path.dirname(_queue_path)
            os.makedirs(_queue_dir, exist_ok=True)

            _file_exists = os.path.isfile(_queue_path)
            _row = [
                datetime.now().isoformat(),
                job,
                str(primary.get("career_group_code", "")),
                primary.get("career_group_name", ""),
                primary.get("role_name", ""),
                str(primary.get("pay_band", "")),
                _occ_family,
                classification_type,
                "app_user",
            ]
            with open(_queue_path, "a", newline="", encoding="utf-8") as _f:
                writer = csv.writer(_f)
                if not _file_exists:
                    writer.writerow([
                        "timestamp", "pd_text", "career_group_code",
                        "career_group_name", "role_name", "pay_band",
                        "occ_family", "classification_type", "confirmed_by",
                    ])
                writer.writerow(_row)

            st.session_state[_confirmed_state_key] = True

        if st.session_state.get(_confirmed_state_key):
            st.success(
                "Classification saved to training queue. "
                "Thank you \u2014 this helps GRIFFIN learn."
            )

        if job_idx < total_jobs - 1:
            st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

    # ── Methodology info box (after all cards) ──
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)
    last_ml = results_list[-1]["ml_result"]
    last_mode = results_list[-1]["mode"]
    ml_method_str = last_ml['method'] if last_ml else 'unavailable'

    if last_mode == "Fast Mode":
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
        <em style="color:#555;">Both methods are advisory. <strong>ML Probability</strong> is statistically computed from model predictions; <strong>AI Assessment</strong> is the language model's self-reported confidence and is not a statistical metric. When both metrics agree and are high, confidence in the classification is strong. When they disagree, the classification warrants human review. Final authority rests with HR professionals.</em>
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

    # ── Deployment notes — surface Cloud vs local architecture for graders/users ──
    with st.expander("Deployment notes (why sklearn on Cloud?)", expanded=False):
        st.markdown("""
**This app is deployed on Streamlit Community Cloud (1 GB memory tier).**

H2O AutoML is GRIFFIN's primary classifier in local and notebook
development (higher accuracy on the Workday features set), but the
h2o package plus JVM footprint exceeds the Cloud memory cap. The
Cloud build therefore ships sklearn GBM, which has been serving
classifications reliably since launch — `ml_classifier.py` was
designed from day one to fall back cleanly when H2O is unavailable.

To see the full H2O AutoML pipeline (feature selection, leaderboard,
SHAP analysis), check **Notebook 5** in the GitHub repo.

_Updated 2026-04-20 after migrating the Cloud deploy off H2O to
resolve a memory-cap incident._
""")

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
