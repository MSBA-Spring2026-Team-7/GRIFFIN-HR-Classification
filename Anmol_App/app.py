import streamlit as st
import pandas as pd
import re
import os
import google.generativeai as genai

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
except ImportError:
    pass

# =============================
# 🔑 CONFIG
# =============================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# =============================
# 📂 LOAD DATA
# =============================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "reference")

@st.cache_data
def load_data():
    career_groups = pd.read_excel(os.path.join(DATA_DIR, "career_groups.xlsx"), engine="openpyxl")
    roles         = pd.read_excel(os.path.join(DATA_DIR, "roles.xlsx"), engine="openpyxl")
    pay_bands     = pd.read_excel(os.path.join(DATA_DIR, "dhrm_pay_bands.xlsx"), engine="openpyxl")
    return career_groups, roles, pay_bands

career_groups, roles, pay_bands = load_data()

# =============================
# 🧹 HELPERS
# =============================
def clean_role_name(name):
    """Fix spacing issues like 'ServicesManager' → 'Services Manager'"""
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', str(name)).strip()

def get_pay_info(band):
    for col in ["pay_band", "band", "Band", "PAY_BAND"]:
        if col in pay_bands.columns:
            match = pay_bands[pay_bands[col] == band]
            if len(match) > 0:
                return match.iloc[0]
    return None

# =============================
# 🧠 CLASSIFICATION LOGIC
# =============================
def classify_job(text, top_n=3):
    text_lower = text.lower()
    scored = []

    # Domain rules: (text_keywords, role_keywords, weight)
    # Higher weight = stronger signal. Rules can fire multiple times if multiple groups match.
    keyword_rules = [
        # HR / People — HIGHEST PRIORITY (most specific keywords)
        (["human resource", "hris", "employee relations", "classification of roles",
          "benchmarking salaries", "hr specialist", "hr analyst", "hr manager",
          "talent acquisition", "workforce", "onboarding", "personnel management"],
         ["human resource"], 12),
        (["hr", "recruit", "hiring", "onboard", "talent", "personnel", "benefits"],
         ["human resource", "hr", "personnel", "talent", "recruiter", "benefits"], 6),
        # Finance / Accounting
        (["finance", "financial", "accounting", "accountant", "audit", "auditing",
          "budget", "fiscal", "revenue", "tax", "cpa", "ledger", "payroll",
          "accounts payable", "accounts receivable", "general ledger"],
         ["finance", "financial", "account", "fiscal", "audit", "budget", "comptroller"], 10),
        # IT / Data / Tech
        (["data", "database", "sql", "analytics", "reporting", "business intelligence",
          "dashboard", "data analysis", "data management"],
         ["data", "analytics", "information", "database", "reporting"], 8),
        (["analyst", "analysis", "analyze"],
         ["analyst", "analysis"], 5),
        (["software", "developer", "programming", "code", "engineer", "devops", "cloud", "aws", "azure"],
         ["software", "developer", "engineer", "systems", "technology"], 8),
        (["cybersecurity", "security", "infosec", "network"],
         ["security", "cyber", "network", "information assurance"], 8),
        # Legal / Compliance
        (["legal", "attorney", "counsel", "paralegal", "contract", "litigation", "regulatory"],
         ["legal", "attorney", "counsel", "compliance", "contract", "paralegal"], 8),
        # Communications / Marketing
        (["communications", "marketing", "public relations", "media", "content", "writing", "editor"],
         ["communications", "marketing", "public affairs", "media", "editor"], 8),
        # Research / Science
        (["research", "scientist", "laboratory", "lab", "clinical", "biology", "chemistry"],
         ["research", "scientist", "laboratory", "science", "clinical"], 8),
        # Education
        (["teach", "professor", "instructor", "faculty", "curriculum", "academic", "education"],
         ["faculty", "instructor", "professor", "academic", "education"], 8),
        # Operations / Facilities
        (["repair", "maintenance", "equipment", "facility", "facilities", "mechanical", "hvac"],
         ["repair", "maintenance", "equipment", "facilities", "mechanical"], 8),
        # Management level
        (["manager", "management", "director", "supervisor", "lead", "oversee"],
         ["manager", "director", "supervisor", "administrator", "coordinator"], 3),
        # Admin / Office — LOWEST PRIORITY (very generic terms)
        (["administrative", "admin", "clerical", "receptionist", "secretary"],
         ["administrative", "office", "specialist", "assistant", "clerical"], 2),
    ]

    for _, row in roles.iterrows():
        score = 0
        role_name    = str(row.get("role_name", "")).lower()
        role_summary = str(row.get("role_summary", "")).lower()

        for text_kws, role_kws, weight in keyword_rules:
            text_hit = any(kw in text_lower for kw in text_kws)
            # Match against role_name ONLY for precision — summaries have too many generic mentions
            name_hit = any(kw in role_name for kw in role_kws)
            if text_hit and name_hit:
                score += weight

        # Word overlap bonus — exclude generic HR/job words that appear everywhere
        STOP_WORDS = {
            "specialist", "manager", "analyst", "officer", "director", "assistant",
            "associate", "senior", "junior", "level", "services", "service",
            "support", "program", "programs", "management", "operations", "staff",
            "administrative", "professional", "coordinator", "supervisor", "general"
        }
        text_words = {w for w in text_lower.split() if len(w) > 4 and w not in STOP_WORDS}
        role_words = {w for w in role_name.split() if len(w) > 4 and w not in STOP_WORDS}
        score += len(text_words & role_words) * 3

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]

# =============================
# 🤖 GEMINI EXPLANATION
# =============================
def generate_explanation(text, role_name):
    try:
        model  = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""You are an HR classification expert at a university.

A position description has been matched to the role: {role_name}

Position Description:
{text}

Write 3-4 sentences explaining why this position matches that role.
Be specific, professional, and HR-focused. Reference actual duties from the description."""
        return model.generate_content(prompt).text
    except Exception as e:
        return f"AI explanation unavailable: {e}"

# =============================
# 🎨 PAGE CONFIG & THEME
# =============================
st.set_page_config(
    page_title="GRIFFIN – W&M HR Classification Tool",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400&family=Open+Sans:wght@300;400;500;600&display=swap');

/* ── Reset & Base ── */
.stApp { background-color: #F7F4EE; }
* { box-sizing: border-box; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; max-width: 1100px; }

/* ── Banner ── */
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
.griffin-logo {
    font-size: 2.8rem;
    line-height: 1;
}
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

/* ── Section labels ── */
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

/* ── Input card ── */
.input-card {
    background: #ffffff;
    border: 1px solid #DDD8C8;
    border-radius: 10px;
    padding: 24px 28px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* ── Text area ── */
.stTextArea textarea {
    border: 1.5px solid #C99700 !important;
    border-radius: 6px !important;
    background: #FDFBF7 !important;
    font-family: 'Open Sans', sans-serif !important;
    font-size: 0.93rem !important;
    color: #1a1a1a !important;
    line-height: 1.6 !important;
}
.stTextArea textarea:focus {
    border-color: #115740 !important;
    box-shadow: 0 0 0 3px rgba(17,87,64,0.12) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #115740 !important;
    color: #F5F0E8 !important;
    border: 2px solid #C99700 !important;
    border-radius: 6px !important;
    padding: 10px 32px !important;
    font-family: 'Open Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background: #0d4230 !important;
    border-color: #e6b800 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(17,87,64,0.25) !important;
}

/* ── Toggle ── */
.stToggle { margin-bottom: 4px; }

/* ── Results section header ── */
.results-header {
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #115740;
    border-bottom: 2px solid #C99700;
    padding-bottom: 8px;
    margin: 28px 0 20px 0;
}

/* ── Match cards ── */
.match-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 22px 26px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #E8E2D0;
    transition: box-shadow 0.2s ease;
}
.match-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.10); }
.top-match {
    border-left: 5px solid #115740;
    border-top: none; border-right: none; border-bottom: none;
    border: 1px solid #E8E2D0;
    border-left: 5px solid #115740;
}
.alt-match {
    border-left: 5px solid #C99700;
    border: 1px solid #E8E2D0;
    border-left: 5px solid #C99700;
    opacity: 0.95;
}

/* ── Card header row ── */
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
    color: #0d3d29;
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

/* ── Confidence bar ── */
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

/* ── Data pills row ── */
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

/* ── AI Explanation block ── */
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
    color: #2a2a2a;
    line-height: 1.7;
    margin: 0;
}

/* ── Divider ── */
.gold-divider {
    border: none;
    border-top: 1.5px solid #C99700;
    margin: 28px 0;
    opacity: 0.5;
}

/* ── Footer ── */
.griffin-footer {
    text-align: center;
    font-family: 'Open Sans', sans-serif;
    font-size: 0.75rem;
    color: #aaa;
    margin-top: 48px;
    padding: 20px 0 32px;
    border-top: 1px solid #DDD8C8;
    letter-spacing: 0.5px;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    font-family: 'Open Sans', sans-serif !important;
    font-size: 0.82rem !important;
    color: #888 !important;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 🏛️ BANNER
# =============================
st.markdown("""
<div class="griffin-banner">
    <div class="griffin-banner-inner">
        <div class="griffin-logo">🏛️</div>
        <div>
            <div class="griffin-title">GRIFFIN</div>
            <div class="griffin-subtitle">William &amp; Mary &nbsp;·&nbsp; HR Position Classification &amp; Pay Tool</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================
# 📋 INPUT SECTION
# =============================
st.markdown('<div class="section-label">Step 1 — Paste Position Description (PD)</div>', unsafe_allow_html=True)

input_text = st.text_area(
    label="",
    height=200,
    placeholder=(
        "Paste a position description (PD) here...\n\n"
        "Example: Finance manager responsible for budget planning, financial reporting,\n"
        "general ledger management, accounts payable oversight, and internal audit compliance.\n\n"
        "Tip: Use  ---  on its own line to classify multiple PDs at once."
    )
)

col_btn, col_toggle, col_note = st.columns([1.2, 1.5, 3])
with col_btn:
    run = st.button("⚡  Classify PD")
with col_toggle:
    use_ai = st.toggle("🤖 AI Explanation", value=True)
with col_note:
    st.caption("Separate multiple PDs with `---` on its own line.")

# Debug expander (collapsed by default, clean)
with st.expander("🔧 Developer: List available Gemini models"):
    if st.button("List models"):
        try:
            available = [
                m.name for m in genai.list_models()
                if "generateContent" in m.supported_generation_methods
            ]
            st.success(f"{len(available)} models available:")
            for m in available:
                st.code(m)
        except Exception as e:
            st.error(f"Error: {e}")

# =============================
# 🚀 CLASSIFICATION & RESULTS
# =============================
MEDALS     = ["🥇", "🥈", "🥉"]
BAR_COLORS = ["#115740", "#C99700", "#AAAAAA"]

if run:
    if not input_text.strip():
        st.warning("Please paste a job description before classifying.")
    else:
        jobs = [j.strip() for j in input_text.split("---") if j.strip()]

        for job_idx, job in enumerate(jobs):

            with st.spinner(f"Analyzing position{f' {job_idx+1}' if len(jobs)>1 else ''}..."):
                top_matches = classify_job(job, top_n=3)

            if not top_matches:
                st.error("No matching roles found. Try adding more specific duties or keywords.")
                continue

            top_score = top_matches[0][0]

            # Section header
            label = f"Results — Position {job_idx+1}" if len(jobs) > 1 else "Classification Results"
            st.markdown(f'<div class="results-header">📊 {label}</div>', unsafe_allow_html=True)

            # Show a preview of the input
            with st.expander("📄 Position description used", expanded=False):
                st.write(job)

            # ── Render each match card using native Streamlit ──
            for rank, (score, role) in enumerate(top_matches):

                medal      = MEDALS[rank]
                confidence = int((score / max(top_score, 1)) * 100)
                border     = "#115740" if rank == 0 else "#C99700" if rank == 1 else "#AAAAAA"

                role_name    = clean_role_name(role.get("role_name", "Unknown Role"))
                career_group = str(role.get("career_group_code", "N/A"))
                band         = role.get("pay_band", None)
                pay          = get_pay_info(band)
                salary_min   = f"${pay.get('minimum_salary'):,.0f}" if pay is not None else "N/A"
                salary_max   = f"${pay.get('maximum_salary'):,.0f}" if pay is not None else "N/A"
                band_display = str(band) if band else "N/A"
                badge        = "⭐ Best Match" if rank == 0 else f"Alternative #{rank+1}"

                # Header row
                col_medal, col_name = st.columns([0.06, 0.94])
                with col_medal:
                    st.markdown(f"<p style='font-size:2rem;margin:0'>{medal}</p>", unsafe_allow_html=True)
                with col_name:
                    st.markdown(
                        f"<p style='font-family:Georgia,serif;font-size:1.15rem;font-weight:700;"
                        f"color:#0d3d29;margin:0 0 4px 0'>{role_name} "
                        f"<span style='font-size:0.72rem;background:#E8F2EE;color:#115740;"
                        f"border:1px solid #115740;padding:2px 10px;border-radius:20px;"
                        f"font-weight:600;vertical-align:middle'>{badge}</span></p>",
                        unsafe_allow_html=True
                    )

                # Confidence bar
                st.progress(confidence / 100, text=f"Match strength: {confidence}%  ({score} pts)")

                # Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("📁 Career Group", career_group)
                c2.metric("📊 Pay Band", band_display)
                c3.metric("💵 Salary Range", f"{salary_min} – {salary_max}")

                # AI explanation for top match only
                if use_ai and rank == 0:
                    with st.spinner("Generating AI explanation..."):
                        explanation = generate_explanation(job, role_name)
                    st.info(f"🧠 **AI Classification Rationale**\n\n{explanation}")

                st.markdown(f"<hr style='border:none;border-top:2px solid {border};margin:16px 0 20px 0;opacity:0.4'>", unsafe_allow_html=True)

            if job_idx < len(jobs) - 1:
                st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)

# =============================
# 🏛️ FOOTER
# =============================
st.markdown("""
<div class="griffin-footer">
    GRIFFIN &nbsp;·&nbsp; William &amp; Mary Mason School of Business
    &nbsp;·&nbsp; HR Position Classification &amp; Pay Tool
    &nbsp;·&nbsp; For internal HR use only
</div>
""", unsafe_allow_html=True)