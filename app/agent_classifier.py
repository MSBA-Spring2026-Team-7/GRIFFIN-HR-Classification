"""
GRIFFIN Agent Classifier — Bridge Module
========================================
Bridges the LangChain agent pipeline (griffin_langchain_agents.py) and
the Streamlit UI (streamlit_app.py).

Exposes `classify_position(pd_text, api_key) -> dict` which:
1. Initializes the LLM and agents (cached across Streamlit reruns).
2. Runs the orchestrator with blend-detection instructions.
3. Parses the orchestrator's natural-language response into a
   structured dict for the UI to render.
4. Detects SINGLE vs BLENDED classification (30% threshold).
5. Computes weighted salary for blended classifications.
"""

import json
import re
import os
import uuid

import streamlit as st
import pandas as pd

import griffin_langchain_agents as gla
from griffin_langchain_agents import (
    get_llm,
    create_agents,
    create_orchestrator,
    ensure_data_loaded,
    HumanMessage,
)

# ── Named constant for blend threshold (S-4 criterion) ──
BLEND_THRESHOLD = 0.30

# ── Paths for crosswalk lookup (weighted salary computation) ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "reference")


# ── Enhanced orchestrator prompt with blend-detection instructions ──
# This augments the base orchestrator with explicit instructions to
# analyze duty percentages and determine SINGLE vs BLENDED classification,
# then return a parseable JSON block.
ORCHESTRATOR_BLEND_PROMPT = """\
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


@st.cache_resource
def _init_agents(api_key):
    """Initialize LLM and agents once, cached across Streamlit reruns.

    Args:
        api_key: The Gemini API key.

    Returns:
        (orchestrator, llm) tuple.
    """
    ensure_data_loaded()
    llm = get_llm(api_key=api_key, temperature=0)
    classifier_agent, pay_matcher_agent = create_agents(llm, verbose=False)
    orchestrator = create_orchestrator(
        llm, classifier_agent, pay_matcher_agent,
        system_prompt_override=ORCHESTRATOR_BLEND_PROMPT,
    )
    return orchestrator, llm


def _parse_json_from_response(text):
    """Extract and parse the JSON block from the orchestrator response.

    The orchestrator is instructed to return a JSON block inside triple
    backticks. This function tries several extraction strategies:
    1. ```json ... ``` fenced block
    2. ``` ... ``` generic fenced block
    3. First { ... } at the top level
    """
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

    # Strategy 3: Find the outermost { ... }
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

    # Strategy 4: Natural language extraction (last resort)
    return _extract_from_natural_language(text)


def _extract_from_natural_language(text):
    """Last-resort extraction of classification fields from prose.

    When the orchestrator returns useful classification data embedded in
    natural language rather than a clean JSON block, this function uses
    regex patterns to pull out career group, role, pay band, and
    confidence values.

    Returns a structured dict matching the expected schema, or None if
    no meaningful data can be extracted.
    """
    result = {
        "classification_type": "SINGLE",
        "primary": {},
        "secondary": None,
        "alternative_role": None,
        "alternative_group": None,
        "explanation": "",
    }

    # Look for career group code (5-digit number near "career group" text)
    cg_match = re.search(
        r'career\s+group[:\s]*(\d{5})\s*[-\u2013]\s*([^,\n]+)',
        text, re.IGNORECASE,
    )
    if cg_match:
        result["primary"]["career_group_code"] = int(cg_match.group(1))
        result["primary"]["career_group_name"] = cg_match.group(2).strip()

    # Look for role (role code + name, or just a role title)
    role_match = re.search(
        r'role[:\s]*(\d+)\s*[-\u2013]\s*([^,\n]+)', text, re.IGNORECASE,
    )
    if not role_match:
        role_match = re.search(
            r'((?:Specialist|Manager|Administrator|Analyst|Officer|Director'
            r'|Coordinator)\s+(?:I{1,3}|IV|V|VI)?\b[^,\n]*)',
            text, re.IGNORECASE,
        )
    if role_match:
        if role_match.lastindex and role_match.lastindex >= 2:
            result["primary"]["role_code"] = int(role_match.group(1))
            result["primary"]["role_name"] = role_match.group(2).strip()
        else:
            result["primary"]["role_name"] = role_match.group(1).strip()

    # Look for pay band
    band_match = re.search(r'pay\s*band[:\s]*(\d)', text, re.IGNORECASE)
    if band_match:
        result["primary"]["pay_band"] = int(band_match.group(1))

    # Look for confidence
    conf_match = re.search(r'confidence[:\s]*(\d+)', text, re.IGNORECASE)
    if conf_match:
        result["primary"]["confidence"] = int(conf_match.group(1))

    # Check for blended classification indicators
    if re.search(
        r'blended|blend|dual|secondary\s+(?:career|classification)',
        text, re.IGNORECASE,
    ):
        result["classification_type"] = "BLENDED"

    # Use the full text as explanation (truncated for safety)
    result["explanation"] = text[:500]
    result["primary"]["duty_pct"] = 1.0
    result["primary"]["reasoning"] = text[:300]

    # Only return if we found at least a career group or role name
    if result["primary"].get("career_group_code") or result["primary"].get("role_name"):
        return result
    return None


def _load_crosswalk():
    """Load the crosswalk for weighted salary computation."""
    return pd.read_excel(
        os.path.join(DATA_DIR, "crosswalk.xlsx"), engine="openpyxl"
    )


def _compute_weighted_salary(primary_band, secondary_band,
                             primary_pct, secondary_pct):
    """Compute weighted salary from two pay bands and their duty percentages.

    Uses the DHRM-to-W&M crosswalk to get salary figures per band, then
    applies the weighted formula from pay_matcher_skill.md:
        Weighted Mid = (Primary Mid x Primary%) + (Secondary Mid x Secondary%)

    Args:
        primary_band: DHRM pay band number for primary role.
        secondary_band: DHRM pay band number for secondary role.
        primary_pct: Duty percentage for primary (0.0 - 1.0).
        secondary_pct: Duty percentage for secondary (0.0 - 1.0).

    Returns:
        dict with weighted min, midpoint, max or None if lookup fails.
    """
    xwalk = _load_crosswalk()

    p_row = xwalk[xwalk["dhrm_pay_band"] == int(primary_band)]
    s_row = xwalk[xwalk["dhrm_pay_band"] == int(secondary_band)]

    if p_row.empty or s_row.empty:
        return None

    p = p_row.iloc[0]
    s = s_row.iloc[0]

    # Normalize percentages to sum to 1.0
    total = primary_pct + secondary_pct
    if total > 0:
        p_pct = primary_pct / total
        s_pct = secondary_pct / total
    else:
        p_pct, s_pct = 0.5, 0.5

    return {
        "min": round(p["wm_min"] * p_pct + s["wm_min"] * s_pct, 2),
        "midpoint": round(p["wm_midpoint"] * p_pct + s["wm_midpoint"] * s_pct, 2),
        "max": round(p["wm_max"] * p_pct + s["wm_max"] * s_pct, 2),
    }


def classify_position(pd_text, api_key):
    """Classify a position description using the GRIFFIN agent pipeline.

    This is the single entry point called by streamlit_app.py for Full
    Analysis mode. It replaces the 4 direct genai.GenerativeModel() calls.

    Args:
        pd_text: The position description text to classify.
        api_key: The Gemini API key.

    Returns:
        A structured dict with the classification result:
        {
            "classification_type": "SINGLE" | "BLENDED",
            "primary": { career_group_code, career_group_name, role_code,
                         role_name, pay_band, confidence, duty_pct, reasoning },
            "secondary": None | { same fields as primary },
            "weighted_salary": None | { min, midpoint, max },
            "explanation": str,
            "blend_threshold": float,
            "raw_response": str  # full orchestrator text for debugging
        }
        On error:
        { "error": str }
    """
    try:
        orchestrator, llm = _init_agents(api_key)

        prompt = HumanMessage(content=(
            "Classify the following position description into DHRM career "
            "groups and roles. Analyze duty areas and determine if this is "
            "a SINGLE or BLENDED classification (30% secondary threshold). "
            "Include pay band information.\n\n"
            f"Position Description:\n{pd_text}"
        ))

        # Use a unique thread_id per invocation so conversations don't bleed
        config = {"configurable": {"thread_id": f"streamlit-{uuid.uuid4().hex[:8]}"}}
        response = orchestrator.invoke({"messages": [prompt]}, config)
        raw_text = gla._content_to_str(response["messages"][-1].content)

        # Parse the JSON from the orchestrator's response
        parsed = _parse_json_from_response(raw_text)
        if parsed is None:
            return {
                "error": (
                    "Could not parse structured classification from agent "
                    "response. The agent may have returned an unexpected format."
                ),
                "raw_response": raw_text,
            }

        # Build the result dict
        classification_type = parsed.get("classification_type", "SINGLE").upper()
        primary = parsed.get("primary", {})
        secondary = parsed.get("secondary")

        # Ensure duty_pct defaults
        if classification_type == "SINGLE":
            primary["duty_pct"] = 1.0
            secondary = None

        # Compute weighted salary for blended classifications
        weighted_salary = None
        if classification_type == "BLENDED" and secondary:
            p_band = primary.get("pay_band")
            s_band = secondary.get("pay_band")
            p_pct = primary.get("duty_pct", 0.65)
            s_pct = secondary.get("duty_pct", 0.35)
            if p_band and s_band:
                weighted_salary = _compute_weighted_salary(
                    p_band, s_band, p_pct, s_pct
                )

        return {
            "classification_type": classification_type,
            "primary": primary,
            "secondary": secondary,
            "alternative_role": parsed.get("alternative_role"),
            "alternative_group": parsed.get("alternative_group"),
            "weighted_salary": weighted_salary,
            "explanation": parsed.get("explanation", ""),
            "blend_threshold": BLEND_THRESHOLD,
            "raw_response": raw_text,
        }

    except Exception as e:
        return {"error": f"Agent pipeline error: {e}"}
