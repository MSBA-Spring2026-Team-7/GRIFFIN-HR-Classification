"""Feature extraction for GRIFFIN ML classification pipeline.

Extracts 15 engineered features from raw position description text,
matching the features used in Notebook 4 training.
"""

import re


def count_keywords(text, keywords):
    """Count total occurrences of keyword list in text (case-insensitive)."""
    text_lower = text.lower()
    return sum(text_lower.count(kw.lower()) for kw in keywords)


def extract_features(text):
    """Extract the 15 ML features from raw position description text.

    Returns a dict matching the training data columns.
    """
    text_lower = text.lower()

    # 1. budget_mentioned (binary)
    budget_mentioned = int(bool(re.search(r'\$[\d,]+|\bbudget\b', text, re.IGNORECASE)))

    # 2. supervises_staff (binary) - 11 directional patterns
    supervise_patterns = [
        r'supervises?\s+\w', r'(?:will|may|must)\s+supervise',
        r'oversee\s+\w', r'oversight\s+of',
        r'manage\s+(?:a\s+)?team', r'direct\s+reports?',
        r'lead\s+(?:a\s+)?team',
        r'responsible\s+for\s+(?:the\s+)?(?:supervision|oversight|management\s+of)',
        r'(?:functional|direct|immediate)\s+supervision\s+(?:of|over)',
        r'supervisory\s+(?:role|responsibilit|duties|authority)',
        r'manage\w*\s+(?:staff|employees?|personnel|workers)'
    ]
    supervises_staff = int(any(re.search(p, text, re.IGNORECASE) for p in supervise_patterns))

    # 3. receives_supervision (binary)
    receives_patterns = [
        r'under\s+(?:the\s+)?(?:supervision|direction|guidance)',
        r'(?:reports?|reporting)\s+to',
        r'supervised\s+by',
        r'(?:immediate|direct)\s+supervisor\s+(?:is|will)'
    ]
    receives_supervision = int(any(re.search(p, text, re.IGNORECASE) for p in receives_patterns))

    # 4. supervision_count (integer)
    count_patterns = [
        r'(\d+)\s+(?:direct\s+reports?|staff\s+members?|employees?|subordinates?)',
        r'(?:team\s+of|supervises?|manages?|oversees?)\s+(\d+)',
        r'(\d+)\s+(?:FTE|full.time)'
    ]
    counts = []
    for p in count_patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            for g in m.groups():
                if g:
                    counts.append(int(g))
    supervision_count = max(counts) if counts else 0

    # 5. education_level (ordinal 0-5)
    edu_map = [
        (5, ['ph.d', 'phd', 'doctorate', 'doctoral', 'j.d.', 'jd', 'm.d.']),
        (4, ["master's", 'masters', 'master degree', 'm.s.', 'm.a.', 'mba', 'm.b.a.']),
        (3, ["bachelor's", 'bachelors', 'bachelor degree', 'b.s.', 'b.a.',
             'undergraduate degree', 'four-year degree', '4-year degree']),
        (2, ["associate's", 'associates', 'associate degree', 'two-year', '2-year']),
        (1, ['high school', 'ged', 'diploma'])
    ]
    education_level = 0
    for level, keywords in edu_map:
        if any(kw in text_lower for kw in keywords):
            education_level = max(education_level, level)

    # 6. years_experience (integer)
    exp_patterns = [
        r'(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience|relevant|professional|related)',
        r'(?:minimum|at\s+least|requires?)\s+(\d+)\s+years?'
    ]
    exp_counts = []
    for p in exp_patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            for g in m.groups():
                if g:
                    exp_counts.append(int(g))
    years_experience = max(exp_counts) if exp_counts else 0

    # 7. text_length
    text_length = len(text)

    # 8-13. Keyword counts
    leadership_kw = [
        "manage", "lead", "direct", "supervise", "oversee",
        "coordinate", "administer", "executive"
    ]
    technical_kw = [
        "software", "database", "network", "system", "programming",
        "technical", "engineer", "IT", "technology", "cyber", "server"
    ]
    research_kw = [
        "research", "laboratory", "experiment", "grant", "publication",
        "scientific", "study", "analysis", "data"
    ]
    healthcare_kw = [
        "patient", "clinical", "medical", "health", "nursing",
        "therapy", "counseling", "diagnosis", "treatment"
    ]
    facilities_kw = [
        "maintenance", "building", "HVAC", "plumbing", "electrical",
        "custodial", "grounds", "facility", "repair", "construction"
    ]
    finance_kw = [
        "budget", "fiscal", "accounting", "audit", "financial",
        "procurement", "payroll", "revenue", "expenditure", "tax"
    ]

    # 14. is_exempt (binary) - extract from text
    is_nonexempt = bool(re.search(r'non-?exempt', text, re.IGNORECASE))
    is_exempt_patterns = [r'\bexempt\b', r'FLSA\s+exempt']
    is_exempt_match = any(re.search(p, text, re.IGNORECASE) for p in is_exempt_patterns)
    is_exempt = 0 if is_nonexempt else (1 if is_exempt_match else 0)

    # 15. is_salaried (binary) - extract from text
    is_salaried = int(bool(re.search(r'\bsalar(?:y|ied)\b', text, re.IGNORECASE)))

    return {
        'budget_mentioned': budget_mentioned,
        'supervises_staff': supervises_staff,
        'receives_supervision': receives_supervision,
        'supervision_count': supervision_count,
        'education_level': education_level,
        'years_experience': years_experience,
        'text_length': text_length,
        'leadership_keywords': count_keywords(text, leadership_kw),
        'technical_keywords': count_keywords(text, technical_kw),
        'research_keywords': count_keywords(text, research_kw),
        'healthcare_keywords': count_keywords(text, healthcare_kw),
        'facilities_keywords': count_keywords(text, facilities_kw),
        'finance_keywords': count_keywords(text, finance_kw),
        'is_exempt': is_exempt,
        'is_salaried': is_salaried,
    }
