"""
GRIFFIN -- Word Document Export Module
======================================
Generates professional .docx classification reports from GRIFFIN results.

This module is intentionally self-contained: it depends only on python-docx
and the Python standard library so it can be tested independently of the
Streamlit app.

Team 7 -- William & Mary BUAD 5722 / BUAD 5742, Spring 2026
"""

from io import BytesIO
from datetime import datetime

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

# ── GRIFFIN brand colours ──────────────────────────────────────
WM_GREEN = RGBColor(0x11, 0x57, 0x40)
WM_GOLD = RGBColor(0xC9, 0x97, 0x00)
DARK_GRAY = RGBColor(0x2D, 0x2D, 0x2D)
MED_GRAY = RGBColor(0x66, 0x66, 0x66)
LIGHT_GRAY = RGBColor(0xAA, 0xAA, 0xAA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# Hex strings for table shading (oxml needs plain hex, no '#')
WM_GREEN_HEX = "115740"
WM_GOLD_HEX = "C99700"
LIGHT_GREEN_HEX = "E8F2EE"
CREAM_HEX = "F7F4EE"


# ============================================================
#  Low-level formatting helpers
# ============================================================

def _set_cell_shading(cell, hex_color):
    """Apply background shading to a table cell."""
    shading = cell._element.get_or_add_tcPr()
    shd = shading.makeelement(qn("w:shd"), {
        qn("w:val"): "clear",
        qn("w:color"): "auto",
        qn("w:fill"): hex_color,
    })
    shading.append(shd)


def _set_paragraph_spacing(paragraph, before=0, after=0):
    """Set spacing before/after a paragraph in points."""
    pf = paragraph.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)


def _add_styled_heading(doc, text, level=1):
    """Add a heading with GRIFFIN green colour."""
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        run.font.color.rgb = WM_GREEN
    return heading


def _add_body_text(doc, text, bold=False, italic=False, color=None):
    """Add a body paragraph with optional formatting."""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.size = Pt(10.5)
    run.font.name = "Calibri"
    if bold:
        run.bold = True
    if italic:
        run.italic = True
    if color:
        run.font.color.rgb = color
    return para


def _add_key_value(doc, key, value):
    """Add a line like 'Career Group: 5 - Finance'."""
    para = doc.add_paragraph()
    k = para.add_run(f"{key}: ")
    k.font.size = Pt(10.5)
    k.font.name = "Calibri"
    k.bold = True
    k.font.color.rgb = WM_GREEN
    v = para.add_run(str(value))
    v.font.size = Pt(10.5)
    v.font.name = "Calibri"
    v.font.color.rgb = DARK_GRAY
    _set_paragraph_spacing(para, before=1, after=1)
    return para


def _add_table(doc, headers, rows):
    """Add a formatted table with GRIFFIN-branded header row.

    Parameters
    ----------
    headers : list[str]
    rows : list[list[str]]
    """
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    # Header row
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(header)
        run.bold = True
        run.font.size = Pt(10)
        run.font.name = "Calibri"
        run.font.color.rgb = WHITE
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_cell_shading(cell, WM_GREEN_HEX)

    # Data rows
    for r_idx, row_data in enumerate(rows):
        for c_idx, val in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(10)
            run.font.name = "Calibri"
            run.font.color.rgb = DARK_GRAY
            # Alternate row shading
            if r_idx % 2 == 0:
                _set_cell_shading(cell, CREAM_HEX)

    return table


def _format_salary(val):
    """Safely format a numeric value as a salary string."""
    try:
        return f"${float(val):,.0f}"
    except (TypeError, ValueError):
        return "N/A"


# ============================================================
#  Match-card data extraction helpers
# ============================================================

def _extract_match_cards(classification_result):
    """Extract a list of match-card dicts from the classification result.

    Supports both:
    - CURRENT format (flat Gemini dict with role enrichment)
    - FUTURE format (structured with classification_type, primary, secondary)

    Returns a list of dicts, each with keys:
        role_name, career_group, confidence, band, pay_min, pay_max,
        wm_grade, wm_min, wm_max, reasoning
    """
    cards = []
    if not classification_result:
        return cards

    # ── Future agent format (D-010) ──
    if "classification_type" in classification_result:
        ctype = classification_result.get("classification_type", "SINGLE")
        primary = classification_result.get("primary", {})
        cards.append(_normalize_card(primary, badge="Primary"))
        if ctype == "BLENDED":
            secondary = classification_result.get("secondary", {})
            cards.append(_normalize_card(secondary, badge="Secondary"))
        return cards

    # ── Current format (flat dict + enriched match_cards list) ──
    if "match_cards" in classification_result:
        for mc in classification_result["match_cards"]:
            cards.append(_normalize_card(mc))
        return cards

    # ── Minimal fallback: single flat Gemini result ──
    cards.append(_normalize_card(classification_result))
    return cards


def _normalize_card(d, badge=None):
    """Normalize a card dict to a consistent shape."""
    pay = d.get("pay")  # may be a pandas Series or dict
    pay_min = None
    pay_max = None
    if pay is not None:
        try:
            pay_min = pay.get("minimum_salary") if hasattr(pay, "get") else pay["minimum_salary"]
            pay_max = pay.get("maximum_salary") if hasattr(pay, "get") else pay["maximum_salary"]
        except (KeyError, TypeError):
            pass

    wm = d.get("wm")
    wm_grade = wm.get("wm_pay_grade", "N/A") if isinstance(wm, dict) else "N/A"
    wm_min = wm.get("wm_min") if isinstance(wm, dict) else None
    wm_max = wm.get("wm_max") if isinstance(wm, dict) else None

    return {
        "role_name": d.get("role_name", d.get("career_group_name", "Unknown")),
        "career_group": d.get("career_group",
                              d.get("career_group_label",
                                    f"{d.get('career_group_code', '?')} - {d.get('career_group_name', '?')}")),
        "confidence": d.get("confidence", 0),
        "band": d.get("band", d.get("pay_band", "N/A")),
        "pay_min": pay_min,
        "pay_max": pay_max,
        "wm_grade": wm_grade,
        "wm_min": wm_min,
        "wm_max": wm_max,
        "reasoning": d.get("reasoning", ""),
        "badge": badge or d.get("badge", ""),
        "duty_pct": d.get("duty_pct"),
    }


# ============================================================
#  Main report generator
# ============================================================

def generate_classification_report(
    pd_text: str,
    classification_result: dict,
    ml_result: dict = None,
    mode: str = "Full Analysis",
    posted_salary: float = None,
) -> bytes:
    """Generate a .docx classification report and return as bytes.

    Parameters
    ----------
    pd_text : str
        The input position description text.
    classification_result : dict
        The classification output. Supports both the current Gemini format
        and the future D-010 agent format (duck-typed via dict.get).
    ml_result : dict | None
        ML prediction result with keys: method, prediction, probabilities.
    mode : str
        "Full Analysis" or "Fast Mode".
    posted_salary : float | None
        Extracted salary from the PD, if found.

    Returns
    -------
    bytes
        The .docx file contents, suitable for st.download_button(data=...).
    """
    doc = Document()

    # ── Default font ──
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(10.5)
    font.color.rgb = DARK_GRAY

    # Set narrow margins for a more professional look
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    now = datetime.now()
    timestamp = now.strftime("%B %d, %Y at %I:%M %p")

    # ── HEADER / TITLE BLOCK ──────────────────────────────────
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title_para.add_run("GRIFFIN")
    run_title.font.size = Pt(28)
    run_title.font.name = "Calibri"
    run_title.bold = True
    run_title.font.color.rgb = WM_GREEN
    _set_paragraph_spacing(title_para, before=0, after=2)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = subtitle.add_run("William & Mary  |  HR Position Classification & Pay Tool")
    run_sub.font.size = Pt(11)
    run_sub.font.name = "Calibri"
    run_sub.font.color.rgb = WM_GOLD
    _set_paragraph_spacing(subtitle, before=0, after=4)

    report_label = doc.add_paragraph()
    report_label.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_rl = report_label.add_run("Classification Report")
    run_rl.font.size = Pt(16)
    run_rl.font.name = "Calibri"
    run_rl.bold = True
    run_rl.font.color.rgb = DARK_GRAY
    _set_paragraph_spacing(report_label, before=0, after=2)

    ts_para = doc.add_paragraph()
    ts_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_ts = ts_para.add_run(f"Generated: {timestamp}")
    run_ts.font.size = Pt(9)
    run_ts.font.name = "Calibri"
    run_ts.font.color.rgb = MED_GRAY
    run_ts.italic = True
    _set_paragraph_spacing(ts_para, before=0, after=6)

    if posted_salary:
        sal_para = doc.add_paragraph()
        sal_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_sal = sal_para.add_run(f"Posted Salary Detected: {_format_salary(posted_salary)}")
        run_sal.font.size = Pt(9.5)
        run_sal.font.name = "Calibri"
        run_sal.font.color.rgb = WM_GOLD
        _set_paragraph_spacing(sal_para, before=0, after=4)

    # Divider line
    div = doc.add_paragraph()
    div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_div = div.add_run("_" * 60)
    run_div.font.color.rgb = WM_GOLD
    run_div.font.size = Pt(8)
    _set_paragraph_spacing(div, before=4, after=8)

    # ── SECTION 1: INPUT POSITION DESCRIPTION ─────────────────
    _add_styled_heading(doc, "1. Input Position Description", level=2)

    # Truncate very long PDs in the report to keep it readable,
    # but include the full text.
    pd_para = doc.add_paragraph()
    run_pd = pd_para.add_run(pd_text.strip())
    run_pd.font.size = Pt(9.5)
    run_pd.font.name = "Calibri"
    run_pd.font.color.rgb = DARK_GRAY
    run_pd.italic = True
    _set_paragraph_spacing(pd_para, before=2, after=6)

    # ── SECTION 2: CLASSIFICATION RESULTS ─────────────────────
    _add_styled_heading(doc, "2. Classification Results", level=2)

    mode_para = doc.add_paragraph()
    run_mode = mode_para.add_run(f"Mode: {mode}")
    run_mode.font.size = Pt(10)
    run_mode.font.name = "Calibri"
    run_mode.bold = True
    run_mode.font.color.rgb = MED_GRAY
    _set_paragraph_spacing(mode_para, before=0, after=4)

    if mode == "Fast Mode":
        _render_fast_mode_section(doc, ml_result)
    else:
        _render_full_analysis_section(doc, classification_result)

    # ── SECTION 3: ML PREDICTION (Full Analysis only) ─────────
    if mode == "Full Analysis" and ml_result:
        _add_styled_heading(doc, "3. ML Prediction", level=2)
        _render_ml_section(doc, ml_result)

    # ── SECTION 4: AI RATIONALE (Full Analysis only) ──────────
    if mode == "Full Analysis" and classification_result:
        explanation = classification_result.get("explanation", "")
        reasoning = classification_result.get("reasoning", "")
        rationale_text = explanation or reasoning
        if rationale_text:
            section_num = "4" if ml_result else "3"
            _add_styled_heading(doc, f"{section_num}. AI Rationale", level=2)
            rat_para = doc.add_paragraph()
            run_rat = rat_para.add_run(rationale_text)
            run_rat.font.size = Pt(10.5)
            run_rat.font.name = "Calibri"
            run_rat.font.color.rgb = DARK_GRAY
            _set_paragraph_spacing(rat_para, before=2, after=6)

    # ── SECTION 5: METHODOLOGY NOTE ───────────────────────────
    _render_methodology_section(doc, mode, ml_result)

    # ── FOOTER ────────────────────────────────────────────────
    footer_div = doc.add_paragraph()
    footer_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_fd = footer_div.add_run("_" * 60)
    run_fd.font.color.rgb = WM_GOLD
    run_fd.font.size = Pt(8)
    _set_paragraph_spacing(footer_div, before=12, after=4)

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_f1 = footer.add_run(f"Generated by GRIFFIN  |  William & Mary  |  {timestamp}")
    run_f1.font.size = Pt(8.5)
    run_f1.font.name = "Calibri"
    run_f1.font.color.rgb = MED_GRAY
    run_f1.italic = True
    _set_paragraph_spacing(footer, before=0, after=2)

    disc = doc.add_paragraph()
    disc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_disc = disc.add_run("This report is advisory. Final classification authority rests with HR professionals.")
    run_disc.font.size = Pt(8)
    run_disc.font.name = "Calibri"
    run_disc.font.color.rgb = LIGHT_GRAY
    run_disc.italic = True

    # ── Write to bytes ────────────────────────────────────────
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ============================================================
#  Section renderers
# ============================================================

def _render_fast_mode_section(doc, ml_result):
    """Render the Fast Mode results section (ML-only)."""
    if not ml_result:
        _add_body_text(doc, "No ML prediction available.", italic=True, color=MED_GRAY)
        return

    sorted_probs = sorted(
        ml_result.get("probabilities", {}).items(),
        key=lambda x: x[1], reverse=True,
    )
    if not sorted_probs:
        _add_body_text(doc, "ML prediction returned no probabilities.", italic=True, color=MED_GRAY)
        return

    top_family, top_conf = sorted_probs[0]

    _add_key_value(doc, "Predicted Occupational Family", top_family)
    _add_key_value(doc, "ML Confidence", f"{top_conf}%")
    _add_key_value(doc, "Method", ml_result.get("method", "Unknown"))

    doc.add_paragraph()  # spacer

    # Probabilities table
    _add_body_text(doc, "Occupational Family Probabilities:", bold=True, color=WM_GREEN)

    headers = ["Occupational Family", "Confidence"]
    rows = [[fam, f"{pct}%"] for fam, pct in sorted_probs]
    _add_table(doc, headers, rows)

    doc.add_paragraph()  # spacer after table


def _render_full_analysis_section(doc, classification_result):
    """Render the Full Analysis results section."""
    if not classification_result:
        _add_body_text(doc, "No classification data available.", italic=True, color=MED_GRAY)
        return

    # ── Check for BLENDED (future D-010 agent format) ──
    ctype = classification_result.get("classification_type", "SINGLE")

    # ── Try structured match_cards first, then fall back to flat dict ──
    cards = _extract_match_cards(classification_result)

    if cards:
        for idx, card in enumerate(cards):
            rank_labels = ["Best Match", "Alternative Role", "Alternative Group"]
            label = card.get("badge") or (rank_labels[idx] if idx < len(rank_labels) else f"Match {idx + 1}")
            _add_body_text(doc, f"--- {label} ---", bold=True, color=WM_GREEN)
            _add_key_value(doc, "Role", card["role_name"])
            _add_key_value(doc, "Career Group", card["career_group"])
            _add_key_value(doc, "Confidence", f"{card['confidence']}%")
            _add_key_value(doc, "Pay Band", str(card["band"]))

            if card["pay_min"] is not None and card["pay_max"] is not None:
                _add_key_value(doc, "Salary Range",
                               f"{_format_salary(card['pay_min'])} - {_format_salary(card['pay_max'])}")

            if card["wm_grade"] and card["wm_grade"] != "N/A":
                wm_str = card["wm_grade"]
                if card["wm_min"] is not None and card["wm_max"] is not None:
                    wm_str += f" ({_format_salary(card['wm_min'])} - {_format_salary(card['wm_max'])})"
                _add_key_value(doc, "W&M Grade", wm_str)

            if card.get("duty_pct") is not None:
                _add_key_value(doc, "Duty Percentage", f"{card['duty_pct']}%")

            if card.get("reasoning"):
                reason_para = doc.add_paragraph()
                r_label = reason_para.add_run("Reasoning: ")
                r_label.font.size = Pt(10)
                r_label.font.name = "Calibri"
                r_label.bold = True
                r_label.font.color.rgb = WM_GREEN
                r_text = reason_para.add_run(card["reasoning"])
                r_text.font.size = Pt(10)
                r_text.font.name = "Calibri"
                r_text.italic = True
                r_text.font.color.rgb = MED_GRAY
                _set_paragraph_spacing(reason_para, before=1, after=4)

            doc.add_paragraph()  # spacer between cards

    # ── BLENDED weighted salary table (future format) ──
    if ctype == "BLENDED":
        weighted = classification_result.get("weighted_salary", {})
        if weighted:
            _add_body_text(doc, "Weighted Salary (Blended)", bold=True, color=WM_GREEN)
            headers = ["Component", "Value"]
            rows = []
            for k, v in weighted.items():
                display_key = k.replace("_", " ").title()
                display_val = _format_salary(v) if isinstance(v, (int, float)) else str(v)
                rows.append([display_key, display_val])
            _add_table(doc, headers, rows)
            doc.add_paragraph()

    # ── Alternative Matches (for HR triangulation) ──
    _render_alternative_sections(doc, classification_result)

    # ── Pay band summary table for all cards ──
    all_cards_for_summary = list(cards)
    alt_role_data = classification_result.get("alternative_role")
    alt_group_data = classification_result.get("alternative_group")
    if alt_role_data:
        all_cards_for_summary.append(_normalize_card(alt_role_data, badge="Alt Role"))
    if alt_group_data:
        all_cards_for_summary.append(_normalize_card(alt_group_data, badge="Alt Group"))

    pay_rows = []
    for card in all_cards_for_summary:
        if card["pay_min"] is not None and card["pay_max"] is not None:
            pay_rows.append([
                card["role_name"],
                str(card["band"]),
                _format_salary(card["pay_min"]),
                _format_salary(card["pay_max"]),
                card["wm_grade"] if card["wm_grade"] != "N/A" else "-",
            ])
    if len(pay_rows) > 1:
        _add_body_text(doc, "Pay Band Summary", bold=True, color=WM_GREEN)
        _add_table(doc, ["Role", "Band", "Salary Min", "Salary Max", "W&M Grade"], pay_rows)
        doc.add_paragraph()


def _render_alternative_card(doc, card, heading):
    """Render a single alternative match card with professional formatting.

    Parameters
    ----------
    doc : Document
        The python-docx Document being built.
    card : dict
        Normalized card dict from _normalize_card().
    heading : str
        Section heading, e.g. "Alternative Match -- Same Career Group".
    """
    _add_body_text(doc, f"--- {heading} ---", bold=True, color=WM_GREEN)
    _add_key_value(doc, "Role", card["role_name"])
    _add_key_value(doc, "Career Group", card["career_group"])
    _add_key_value(doc, "AI Confidence", f"{card['confidence']}%")
    _add_key_value(doc, "Pay Band", str(card["band"]))

    if card["pay_min"] is not None and card["pay_max"] is not None:
        _add_key_value(doc, "Salary Range",
                       f"{_format_salary(card['pay_min'])} - {_format_salary(card['pay_max'])}")

    if card["wm_grade"] and card["wm_grade"] != "N/A":
        wm_str = card["wm_grade"]
        if card["wm_min"] is not None and card["wm_max"] is not None:
            wm_str += f" ({_format_salary(card['wm_min'])} - {_format_salary(card['wm_max'])})"
        _add_key_value(doc, "W&M Grade", wm_str)

    if card.get("reasoning"):
        reason_para = doc.add_paragraph()
        r_label = reason_para.add_run("Reasoning: ")
        r_label.font.size = Pt(10)
        r_label.font.name = "Calibri"
        r_label.bold = True
        r_label.font.color.rgb = WM_GREEN
        r_text = reason_para.add_run(card["reasoning"])
        r_text.font.size = Pt(10)
        r_text.font.name = "Calibri"
        r_text.italic = True
        r_text.font.color.rgb = MED_GRAY
        _set_paragraph_spacing(reason_para, before=1, after=4)

    doc.add_paragraph()  # spacer


def _render_alternative_sections(doc, classification_result):
    """Render Alternative Role and Alternative Career Group sections.

    Gracefully skips each section if the corresponding data is null/absent.
    This ensures the export includes all three HR triangulation matches
    when available, and simply omits sections when they are not.

    Parameters
    ----------
    doc : Document
        The python-docx Document being built.
    classification_result : dict
        The full classification result dict containing alternative_role
        and alternative_group keys.
    """
    alt_role = classification_result.get("alternative_role")
    alt_group = classification_result.get("alternative_group")

    if not alt_role and not alt_group:
        return

    if alt_role:
        # The alternative role is in the SAME career group as the primary.
        # Inject the primary's career group info so _normalize_card doesn't
        # produce "? - ?" (the orchestrator omits these fields for alt_role).
        primary = classification_result.get("primary", {})
        enriched_alt_role = dict(alt_role)
        if "career_group_code" not in enriched_alt_role:
            enriched_alt_role["career_group_code"] = primary.get("career_group_code")
        if "career_group_name" not in enriched_alt_role:
            enriched_alt_role["career_group_name"] = primary.get("career_group_name")
        card = _normalize_card(enriched_alt_role, badge="Alternative Role")
        _render_alternative_card(
            doc, card, "Alternative Match \u2014 Same Career Group")

    if alt_group:
        card = _normalize_card(alt_group, badge="Alternative Group")
        _render_alternative_card(
            doc, card, "Alternative Match \u2014 Different Career Group")


def _render_ml_section(doc, ml_result):
    """Render the ML prediction subsection (shown in Full Analysis as counterbalance)."""
    sorted_probs = sorted(
        ml_result.get("probabilities", {}).items(),
        key=lambda x: x[1], reverse=True,
    )
    if sorted_probs:
        top_family, top_conf = sorted_probs[0]
        _add_key_value(doc, "Predicted Family", top_family)
        _add_key_value(doc, "ML Confidence", f"{top_conf}%")
    _add_key_value(doc, "Method", ml_result.get("method", "Unknown"))

    # Show top 4 probabilities in compact form
    if len(sorted_probs) > 1:
        doc.add_paragraph()  # spacer
        headers = ["Family", "Confidence"]
        rows = [[fam, f"{pct}%"] for fam, pct in sorted_probs[:6]]
        _add_table(doc, headers, rows)
        doc.add_paragraph()


def _render_methodology_section(doc, mode, ml_result):
    """Render the methodology and disclaimer section."""
    section_num = "5" if mode == "Full Analysis" else "3"
    _add_styled_heading(doc, f"{section_num}. Methodology", level=2)

    ml_method = ml_result.get("method", "Unknown") if ml_result else "unavailable"

    if mode == "Fast Mode":
        _add_body_text(
            doc,
            f"This classification was performed in Fast Mode using ML only ({ml_method}). "
            f"The ML model was trained on 100 William & Mary position descriptions with "
            f"15 engineered features and predicts occupational family. No API calls were "
            f"made. For detailed role-level classification with AI rationale, use Full Analysis mode.",
        )
    else:
        _add_body_text(
            doc,
            f"This classification used GRIFFIN's dual-method approach:",
            bold=True,
        )
        _add_body_text(
            doc,
            f"ML ({ml_method}): Trained on 100 W&M position descriptions with 15 engineered "
            f"features. Predicts occupational family. Runs locally with zero API cost.",
        )
        _add_body_text(
            doc,
            f"Agentic AI (Gemini 2.5 Flash): Classifies against the full DHRM taxonomy "
            f"(56 career groups, 294 roles) using LLM reasoning. Provides explainable rationale.",
        )
        _add_body_text(
            doc,
            "When ML and AI agree, confidence is high. When they disagree, the "
            "classification warrants human review.",
            italic=True, color=MED_GRAY,
        )

    doc.add_paragraph()  # spacer
    _add_body_text(
        doc,
        "ADVISORY DISCLAIMER: This classification is generated by automated models and "
        "is intended as a decision-support tool. Final classification authority rests "
        "with HR professionals. This report should not be used as the sole basis for "
        "personnel actions.",
        italic=True, color=MED_GRAY,
    )
