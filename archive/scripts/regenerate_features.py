"""Regenerate workday_features.csv with fixed supervision regex."""
import pandas as pd
import numpy as np
import re
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Load data
training_df = pd.read_csv(os.path.join(DATA_DIR, "workday_training.csv"))
print(f"Loaded {len(training_df)} rows")

# Job family mapping
JOB_FAMILY_MAP = {
    "Staff - Administrative & Office Support": "Administrative Services",
    "Staff - Fiscal Administration": "Administrative Services",
    "Staff - Financial Analysis": "Administrative Services",
    "Staff - HR Business Partner": "Administrative Services",
    "Staff - Academic Program Administration": "Administrative Services",
    "Staff - Program Management": "Administrative Services",
    "Staff - Career Services": "Administrative Services",
    "Staff - Alumni Affairs": "Administrative Services",
    "Staff - Giving: Annual, Major Gifts, & Planned": "Administrative Services",
    "Staff - Stewardship & Donor Relations": "Administrative Services",
    "Staff - Admissions & Enrollment": "Administrative Services",
    "Staff - Student Services": "Administrative Services",
    "Staff - Compliance": "Administrative Services",
    "Staff - Community Relations": "Administrative Services",
    "Staff - Communications": "Educational and Media Services",
    "Staff - Public Relations": "Educational and Media Services",
    "Staff - Media & Creative Services": "Educational and Media Services",
    "Staff - Librarians": "Educational and Media Services",
    "Staff - Instructional Development & Design": "Educational and Media Services",
    "Staff - Software Programming & Applications": "Engineering and Technology",
    "Staff - User Support": "Engineering and Technology",
    "Staff - Medical": "Health and Human Services",
    "Staff - Athletic Training & Wellbeing": "Health and Human Services",
    "Staff - Scientist": "Natural Resources and Applied Science",
    "Staff - Lab & Research Support": "Natural Resources and Applied Science",
    "Staff - Security - Law Enforcement Officer": "Public Safety",
    "Staff - Security - Non Law Enforcement Officer": "Public Safety",
    "Staff - Building Services": "Trades and Operations",
    "Staff - Maintenance": "Trades and Operations",
    "Staff - Athletics Operations": "Trades and Operations",
}
training_df["occ_family"] = training_df["job_family"].map(JOB_FAMILY_MAP).fillna("Unknown")


# --- Feature extraction functions ---

def extract_budget_mentioned(text):
    return int(bool(re.search(r'\$[\d,]+|\bbudget\b', text, re.IGNORECASE)))

def extract_budget_amount_max(text):
    amounts = re.findall(r'\$([\d,]+)', text)
    return max(int(a.replace(',', '')) for a in amounts) if amounts else 0

def extract_supervises_staff(text):
    """FIXED: directional supervision detection — does this position GIVE supervision?"""
    gives_patterns = [
        r'supervises?\s+\w',
        r'(?:will|may|must)\s+supervise',
        r'oversee\s+\w',
        r'oversight\s+of',
        r'manage\s+(?:a\s+)?team',
        r'direct\s+reports?',
        r'lead\s+(?:a\s+)?team',
        r'responsible\s+for\s+(?:the\s+)?(?:supervision|oversight|management\s+of)',
        r'(?:functional|direct|immediate)\s+supervision\s+(?:of|over)',
        r'supervisory\s+(?:role|responsibilit|duties|authority)',
        r'manage\w*\s+(?:staff|employees?|personnel|workers)',
    ]
    return int(any(re.search(p, text, re.IGNORECASE) for p in gives_patterns))

def extract_receives_supervision(text):
    """NEW: does this position RECEIVE supervision?"""
    receives_patterns = [
        r'under\s+(?:the\s+)?(?:supervision|direction|guidance)',
        r'(?:reports?|reporting)\s+to',
        r'supervised\s+by',
        r'(?:immediate|direct)\s+supervisor\s+(?:is|will)',
    ]
    return int(any(re.search(p, text, re.IGNORECASE) for p in receives_patterns))

def extract_supervision_count(text):
    patterns = [
        r'(\d+)\s+(?:direct\s+reports?|staff\s+members?|employees?|subordinates?)',
        r'(?:team\s+of|supervises?|manages?|oversees?)\s+(\d+)',
        r'(\d+)\s+(?:FTE|full.time)',
    ]
    counts = []
    for p in patterns:
        counts.extend(int(m) for m in re.findall(p, text, re.IGNORECASE))
    return max(counts) if counts else 0

def extract_education_level(text):
    tl = text.lower()
    if any(w in tl for w in ['ph.d', 'phd', 'doctorate', 'doctoral', 'j.d.', 'jd', 'm.d.', 'md']):
        return 5
    if any(w in tl for w in ["master's", "masters", "master degree", "m.s.", "m.a.", "mba", "m.b.a."]):
        return 4
    if any(w in tl for w in ["bachelor's", "bachelors", "bachelor degree", "b.s.", "b.a.", "undergraduate degree"]):
        return 3
    if any(w in tl for w in ["associate's", "associates", "associate degree"]):
        return 2
    if any(w in tl for w in ["high school", "ged", "diploma"]):
        return 1
    return 0

def extract_years_experience(text):
    patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|relevant|professional|related)',
        r'(?:minimum|at\s+least|requires?)\s+(\d+)\s+years?',
    ]
    years = []
    for p in patterns:
        years.extend(int(m) for m in re.findall(p, text, re.IGNORECASE))
    return max(years) if years else 0

def count_keywords(text, keywords):
    tl = text.lower()
    return sum(tl.count(kw.lower()) for kw in keywords)

LEADERSHIP_KW = ["manage", "lead", "direct", "supervise", "oversee", "coordinate", "administer", "executive"]
TECHNICAL_KW = ["software", "database", "network", "system", "programming", "technical", "engineer", "IT", "technology", "cyber", "server"]
RESEARCH_KW = ["research", "laboratory", "experiment", "grant", "publication", "scientific", "study", "analysis", "data"]
HEALTHCARE_KW = ["patient", "clinical", "medical", "health", "nursing", "therapy", "counseling", "diagnosis", "treatment"]
FACILITIES_KW = ["maintenance", "building", "HVAC", "plumbing", "electrical", "custodial", "grounds", "facility", "repair", "construction"]
FINANCE_KW = ["budget", "fiscal", "accounting", "audit", "financial", "procurement", "payroll", "revenue", "expenditure", "tax"]


# --- Apply features ---

df = training_df.copy()
df["budget_mentioned"] = df["censored_text"].apply(extract_budget_mentioned)
df["budget_amount_max"] = df["censored_text"].apply(extract_budget_amount_max)
df["supervises_staff"] = df["censored_text"].apply(extract_supervises_staff)
df["receives_supervision"] = df["censored_text"].apply(extract_receives_supervision)
df["supervision_count"] = df["censored_text"].apply(extract_supervision_count)
df["education_level"] = df["censored_text"].apply(extract_education_level)
df["years_experience"] = df["censored_text"].apply(extract_years_experience)
df["text_length"] = df["censored_text"].str.len()
df["leadership_keywords"] = df["censored_text"].apply(lambda t: count_keywords(t, LEADERSHIP_KW))
df["technical_keywords"] = df["censored_text"].apply(lambda t: count_keywords(t, TECHNICAL_KW))
df["research_keywords"] = df["censored_text"].apply(lambda t: count_keywords(t, RESEARCH_KW))
df["healthcare_keywords"] = df["censored_text"].apply(lambda t: count_keywords(t, HEALTHCARE_KW))
df["facilities_keywords"] = df["censored_text"].apply(lambda t: count_keywords(t, FACILITIES_KW))
df["finance_keywords"] = df["censored_text"].apply(lambda t: count_keywords(t, FINANCE_KW))
df["is_exempt"] = (df["exempt_status"] == "Exempt").astype(int)
df["is_salaried"] = (df["pay_type"] == "Salary").astype(int)

feature_cols = [
    "budget_mentioned", "budget_amount_max", "supervises_staff", "receives_supervision",
    "supervision_count", "education_level", "years_experience", "text_length",
    "leadership_keywords", "technical_keywords", "research_keywords",
    "healthcare_keywords", "facilities_keywords", "finance_keywords",
    "is_exempt", "is_salaried"
]
export_cols = feature_cols + ["compensation_grade", "job_family", "occ_family"]

output_path = os.path.join(DATA_DIR, "workday_features.csv")
df[export_cols].to_csv(output_path, index=False)
print(f"\nExported {len(df)} rows x {len(export_cols)} columns to {output_path}")
print(f"\nFeature summary (16 features):")
for col in feature_cols:
    nz = df[col].astype(bool).sum()
    print(f"  {col}: min={df[col].min()}, max={df[col].max()}, mean={df[col].mean():.2f}, nonzero={nz}")
