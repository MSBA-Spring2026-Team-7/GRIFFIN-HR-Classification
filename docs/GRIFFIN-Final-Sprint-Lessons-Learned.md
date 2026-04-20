# GRIFFIN Final Sprint — Lessons Learned

**Project:** GRIFFIN HR Classification Tool
**Sprint period:** 2026-04-12 through 2026-04-18
**Project status:** DELIVERED to client (Board presentation successful, email sent, files transferred)
**Retrospective date:** 2026-04-18
**Retrospective format:** CQM-orchestrated, 6-area walkthrough with Owner

---

## Document Purpose and Audience

This is the **archival record** of the GRIFFIN Final Sprint retrospective. It is written for:
- **Future-Steven and future team members** returning to this project
- **Future CQM practitioners** looking for concrete examples of the framework under real pressure
- **External reviewers** evaluating CQM as a methodology (portfolio use)

It is NOT a project status report (that's the PM journal), a design doc (those are in `docs/`), or a user-facing artifact (those are the Implementation Playbook and Technical Transition Guide).

This document is cross-referenced with:
- **Memory updates:** `~/.claude/projects/.../memory/pattern_*.md` for the confirmed reusable patterns
- **SKILL.md updates:** `~/.claude/plugins/marketplaces/local-desktop-app-uploads/cqm-orchestrator/skills/cqm-orchestrator/SKILL.md` for framework-level changes
- **CQM Issues Log:** `~/.claude/projects/.../memory/cqm-issues-log.md` for items being watched for pattern-tracing
- **Source artifacts:** `cqm-sessions/griffin-final-sprint/pm-journal.md` and `red-team-reports/*.json`

---

## Executive Summary

The GRIFFIN Final Sprint was a 7-day intensive that closed a ~6-month project. It spanned 19 DFOWs across five operational days, delivered two course rubrics (BUAD 5742 AI + BUAD 5722 Big Data), and resulted in a client-ready tool with an 8-document support suite. The sprint survived a 10+ hour overnight push, 4 rework cycles on the agent integration DFOW, two Red Team reviews (14 + 17 findings), and a project lock-unlock cycle tied to the live poster presentation.

**Outcome:** Shipped on time, positive board response, client has files, no critical findings on final Red Team review.

**What made it work:** CQM discipline under pressure (mostly), written acceptance criteria that survived multi-day sprints, file-based state that enabled session splits, parallel agent deployment that respected the 3-agent ceiling.

**What we'd do differently:** PM would not break from process three times; we'd identify personas during Preparatory Phase rather than during documentation production; we'd catch rendering-layer bugs with a Rendering Fidelity Criterion instead of hoping code review was enough; we'd run a Reconciliation step during PM downtime to catch README/code divergence before Red Team did.

---

## Area 1 — CQM Process

### 1.1 What Worked

**Tier selection was defensible and adaptive:**
- D-001 (Streamlit + ML integration): Full Three-Phase — correct call, highest-risk DFOW
- D-002 (PPTX): Full Three-Phase with Reduced Cadence — right-sized for a 12-slide deck
- D-003/D-004/D-005 (ethics, GCP, sync): Abbreviated → Preparatory — right for narrow scope
- D-010 (agent integration): Full Three-Phase — correctly escalated given Red Team findings RT-005
- D-012/D-013/D-014 (docs trio): Abbreviated + independent QC — excellent risk-calibrated choice

**QC cadence delivered its intended value:**
- 11th Hour QC deployed with full isolation (SKILL.md compliant): 30/38 PASS, 0 FAIL, 7 UNABLE-TO-VERIFY (all deployment-dependent)
- Two Red Team reviews producing non-overlapping findings, validating the "separate eyes" investment
- Post-presentation Red Team (14 findings): 2 CRITICAL, 5 MAJOR — all addressed in subsequent DFOWs
- Final-delivery Red Team (17 findings): 0 CRITICAL, 3 MAJOR — recommendation: SHIP_WITH_CAVEATS

**Overnight autonomous execution (authorized) worked:**
- 3 documentation Superintendents in parallel (D-012, D-013, D-014) → 20/20 PASS QC
- Morning briefing was actionable without Owner re-briefing
- Parallel ceiling (3 agents, POAM R2-017) respected throughout — no brief-fidelity degradation observed

**Session-splitting discipline held:**
- Handoff at ~75-80% context consumption used the full SKILL.md protocol
- Fresh PM in new session resumed from `session-handoff-20260414-endofnight.md` + journal + criteria
- No continuity loss, no re-briefing cost

### 1.2 What Didn't

**PM Process Deviation — systemic, not isolated:**

Three instances in one sprint, all following the same rationalization ("small fix, deadline pressure, CQM would be overhead"):
1. 2026-04-12T12:10 — ad-hoc fixes during D-001 rework
2. 2026-04-12T13:15 — direct edits to `ml_classifier.py` + `streamlit_app.py` (H2O caching)
3. 2026-04-14 — sidebar hotfix (`initial_sidebar_state` config toggle)

The third was defensible in isolation (pure config toggle under demo-day pressure), but the **pattern is the concern, not the individual instance**. Each deviation erodes the framework discipline the Owner is trusting the PM to maintain.

**Framework response:** Added as POAM R2-024a in SKILL.md — "PM Direct-Edit Anti-Pattern" — with self-check question, acceptable/unacceptable scenarios, and journal logging requirement for rationalized temptations.

**HTML rendering bug survived 2 QC passes:**

The D-010 indentation → markdown code block bug is a canonical example of a defect class that code review cannot catch. Both Superintendent self-assessment and Independent QC passed the relevant criteria because the source was correct — the bug only manifested when Streamlit rendered the string via `st.markdown()`. Leading-indent LLM output triggered Markdown's code-block rule, rendering narrative as monospaced code.

**Framework response:** Added "Rendering Fidelity Criteria" (POAM R2-026) to `documentation-templates.md` acceptance-criteria template. Mandates screenshot/captured-output evidence for any deliverable consumed by a renderer. Also added Owner UAT as recommended practice (POAM R2-025) in Completion Sequence for deliverables with runtime surfaces.

**`_content_to_str` LangChain bug should have been anticipated:**

LangChain's `AIMessage.content` returns a list when tools are invoked, not a plain string. The initial D-010 implementation assumed string, producing "expected string, got list" at Owner UAT. This is documented LangChain behavior — the Superintendent brief did not include a "known LangChain gotchas" section.

**Framework response:** Added to `reference_platform_quirks.md` (Owner asset). Candidate for a broader "LangChain tool-use platform quirks" memory if recurring.

**D-010 4 rework cycles suggests Initial Phase scope was too broad:**

The Initial Phase for D-010 made the entire agent integration the first segment — not "a limited, representative first segment" per the DFOW decomposition guide. This meant the benchmark was established against a large surface, and defects discovered at Owner UAT rippled through 4 rework rounds. A smaller Initial Phase (e.g., just the bridge module, with Streamlit integration coming in Follow-up) would have surfaced the LangChain content-shape issue earlier and at lower cost.

**Framework response:** No POAM change — the current guidance already covers this; it's a PM judgment failure, not a framework gap. Logged in this archive for future reference.

### 1.3 D-001 QC Deferral — Monitoring, Not Action

**What happened:** Owner accepted the D-001 Streamlit app via live UAT, explicitly deferring independent QC. Red Team (RT-005 post-presentation) later caught a major gap — the LangChain agents were standalone and not wired to the deployed app — which independent QC at the time of rework might have flagged earlier.

**Why not turn this into a framework rule immediately:** Owner's directive was to **monitor**, not to codify. One occurrence doesn't prove "QC deferral causes downstream Red Team findings" — it's suggestive but not conclusive. Codifying prematurely creates framework mass that might not be load-bearing.

**Where logged:** `cqm-issues-log.md` — first entry, status Open, watching for recurrence.

---

## Area 2 — Technical Decisions

### 2.1 Agent Integration — Bridge Module Pattern Born Here

**What happened:** Pre-D-010, the Streamlit app made 4 sequential direct `genai.generate_content()` calls. The 791-line LangChain agent module existed as a standalone Assignment-5 deliverable but was never wired to the app. Red Team RT-005 caught this specification-reality gap.

**D-010 refactoring** created `agent_classifier.py` as a bridge module exposing `classify_position(text) → dict`. The bridge:
- Encapsulated LangChain-specific concerns (message list normalization via `_content_to_str`, rate limit pauses, tool-use handling)
- Insulated the Streamlit app from SDK churn — when the Google AI SDK interface changed mid-sprint, only the bridge changed
- Was independently testable

**Codified as a pattern:** `pattern_bridge_module.md`. Confirmed with 3 occurrences in GRIFFIN alone (`agent_classifier.py`, `cloud_sql_config.py`, `ml_classifier.py`).

### 2.2 HTML Rendering Bug — Architectural Gap in QC

(Covered under Area 1 above. Summary: code review cannot observe rendering. Framework response: Rendering Fidelity Criterion + Owner UAT as recommended practice.)

### 2.3 LangChain List-vs-String (`_content_to_str`)

When an agent invokes tools, `AIMessage.content` is a list of content blocks, not a string. Documented behavior. The helper function normalizes list → string by extracting and concatenating text blocks.

**Not elevated to a framework pattern** because it's LangChain-version-specific. Logged to platform quirks reference for as-of-now workaround status.

### 2.4 H2O on Cloud — Client-Readiness, Not Demo-Readiness

**Corrected framing** (after Owner course-correction during this retrospective):

H2O and sklearn are complementary, not competing. The GRIFFIN architecture serves two deployment targets:

| Environment | Primary | Secondary | Why |
|---|---|---|---|
| Client production (upgraded Streamlit, on-prem, GCP, ≥2GB RAM) | H2O GBM | sklearn fallback | Higher accuracy, AutoML-tuned, grows with training data |
| Free-tier demo (1GB Streamlit Cloud) | sklearn | (H2O unavailable) | RAM-bound, sklearn self-trains at boot |

**The lesson is not "drop H2O" — it's "position tooling correctly for the environment it actually serves."** Red Team RT-003 (post-presentation) wasn't "H2O shouldn't exist" — it was "the README framing didn't disambiguate demo-tier from client-tier." D-018 README accuracy pass addressed this.

**Codified as feedback memory:** `feedback_complementary_tooling.md`. Core principle: "Build for client environment, accept demo-tier constraints as temporary. Don't let free-tier infra drive product design."

### 2.5 SDK Migration Via Abstraction Layer

The bridge module pattern (see 2.1) also served as the SDK migration point when Google's AI SDK changed mid-sprint. Classic Port-Adapter (hexagonal architecture) applied pragmatically.

**This is the pattern going forward** for any third-party SDK integration: thin bridge module with domain-meaningful signature → swappable implementation underneath.

---

## Area 3 — Presentation & Aesthetics

### 3.1 W&M Light Palette (from Dark Midnight Executive)

**What happened:** D-002 Initial Phase delivered the PPTX with Midnight Executive (dark) per prior preference. Owner redirected to light W&M institutional colors.

**Lesson:** Palette is medium-dependent, not preference-dependent:

| Medium | Optimal palette | Why |
|---|---|---|
| Screen-only executive viewing | Dark (Midnight Executive) | Contrast pop, low glare in controlled lighting |
| Projection in bright room | Light | Projectors wash out dark backgrounds |
| Printing / handouts | Light | Ink efficiency, readability on paper |
| Poster (physical, printed) | Light | Close-range viewing, high text contrast needed |

**Framework response:** Updated `feedback_pptx_style.md` with medium-dependent qualifier. Owner directive: **don't hardcode a default palette; present options and let Owner pick based on audience**.

**Asset built:** Palette library at `Claude Skills/assets/palettes/` — catalog + individual palette files covering Midnight Executive, W&M Light Institutional, and alternatives. Presented as a menu at the start of any new deck/doc build.

### 3.2 Card-Based UI — Double Duty

The 3-card layout in the Streamlit app carries:
1. **UX:** Information-dense, scannable, decision-oriented
2. **Statistical honesty:** With 103 training PDs across 7 classes (minority classes 3-4 records), top-1 accuracy has enormous variance. Top-3 (90%) is much more defensible. **The UI matches the model's actual reliability.**

Red Team RT-012 questioned 69% top-1 defensibility. The 3-card UI is the architectural response — the UI never asks the user to trust top-1 alone.

**Codified as pattern:** `pattern_card_ui_small_data.md`.

### 3.3 Dual Confidence Bars

- **ML Probability** (green #115740): `predict_proba()` — mathematically computed
- **AI Assessment** (gold #B9975B): LLM self-reported — qualitative

Color-coding teaches the distinction through repetition. Paired with an "Understanding Confidence Metrics" expander as a safety net. The expander is **mandatory** — color without explainer confuses more than clarifies.

### 3.4 Document Styling Matrix

| Audience | Polish level | Example |
|---|---|---|
| Board / executives / client leadership | High: branding, card layouts, light palette, printable | Implementation Playbook, PPTX |
| Technical handoff (internal IT, successors) | Medium: clean typography, functional branding | Technical Transition Guide |
| Internal working docs (journaling, QC, debugging) | Low: markdown, zero styling, optimize for grep | PM journal, QC reports |

**Codified as memory:** `feedback_document_polish_matrix.md`.

**Overkill items flagged for archive reference:**
- Build scripts in `docs/` (should live in `tools/doc-builders/`)
- PPTX template over-engineering for 1-time use

---

## Area 4 — Documentation as a Deliverable

### 4.1 Persona-Driven Documentation

Director Martinez (HR Director), IT Officer, and Professor Chung — three named personas drove the entire doc suite. Red Team operationalized the personas as attack vectors. Found real usability failures (Windows hardcoded path in QUICK_START, missing Tavily env var).

**Codified as pattern:** `pattern_persona_driven_docs.md`. Elevated to Preparatory Phase input-verification step (SKILL.md POAM R2-022) — personas are identified before production, not during.

### 4.2 Adoption Accelerators

Copy-paste-ready artifacts in champion's voice:
- Draft IT email (HR Director → IT team)
- Staff announcement (HR → department)
- VP slide (single-slide exec value prop)
- 30/60/90-day rollout template

**Most adoption failures are communication friction, not product quality.** Adoption accelerators remove that friction.

**Codified as pattern:** `pattern_adoption_accelerators.md`.

### 4.3 The 8-Document Suite — Right Scope (Corrected Framing)

**Initial framing (wrong):** I proposed consolidating the Client Data Onboarding Guide into an appendix of the Technical Transition Guide, and consolidating the Implementation Briefing PPTX with the Implementation Playbook DOCX since their content overlapped ~60%.

**Owner correction (right):**
- **Client Data Onboarding Guide is a new MODULE** — treating it as a separate product aids discoverability and exploration. Burying a new capability inside a deployment guide damages findability.
- **Briefing vs Playbook serve different communication modes** even with overlapping content:
  - Briefing (PPTX): big picture, large audience, informs + persuades — live-medium job
  - Playbook (DOCX): breadth + depth, manager-ready starting point — desk-reference-medium job

**Lesson:** Communication mode is a first-class planning dimension alongside persona and purpose. Content overlap across modes is translation, not redundancy.

**Codified as feedback memory:** `feedback_communication_modes.md` — with a Communication Mode × Medium matrix and a 4-question test to run before proposing consolidation.

### 4.4 Backlog Candidate: Documentation Suite Planner Skill

Added to `project_skill_backlog.md` as Medium/Medium priority. Trigger: ≥3-audience multi-doc deliveries. Implements Persona × Purpose × Communication-Mode matrix + adoption accelerators + consolidation check.

---

## Area 5 — Team Dynamics

### 5.1 CQM Helped Team Coordination

- Explicit DFOW boundaries created clean handoff points (D-002 narrative content, D-008 kanban delegation to Anmol)
- Written acceptance criteria prevented spec misalignment across Anmol/Brynn/Jhei-R/Steven
- PM journal as communication artifact worked for session-to-session handoff (could extend to teammate handoff)

### 5.2 CQM Hindered Team Coordination

**D-008 delegation exposed a framework gap:** when a teammate picks up work, CQM has no formal mechanism for tracking external work back into the DFOW register. D-008 was removed from active pipeline but criteria were never evaluated against Anmol's actual deliverable.

**Candidate framework addition:** "Delegated DFOW" state in the DFOW Register.
- Status: `DELEGATED` (not ACTIVE, not CLOSED)
- Owner field tracks the external party
- Criteria retained and re-evaluated when work returns
- PM can request delegated-DFOW close-out

**Not yet formalized** — SOP 3 threshold (3+ occurrences) not met. One instance in GRIFFIN. Watch for recurrence in DV course and future client work.

### 5.3 "Lies by Omission" — RT-005 and the PM Downtime Reconciliation Pattern

**What happened:** README documented a "three-agent LangChain pipeline" as deployed architecture, but the Streamlit app didn't use LangChain. Not deception — specification drift. Design docs written aspirationally while implementation happened pragmatically with different authors and no explicit reconciliation step.

**Initial framing (wrong):** I proposed a new "Reconciliation DFOW" category.

**Owner correction (right):** This is PM downtime work, not a new DFOW. PMs have natural downtime while Superintendents produce — use it for active reconciliation (spec-reality grep, input verification, journal maintenance, QC brief pre-composition, criteria sanity check, cross-DFOW semantic consistency).

**Codified as feedback memory:** `feedback_pm_downtime_reconciliation.md`. Elevated to SKILL.md as POAM R2-024b (PM Downtime Task Menu under new "PM Active Role and Discipline" section).

**Escalation rule:** Only formalize "Reconciliation DFOW" as a separate category if the PM-downtime approach fails repeatedly (PM misses divergences on 2+ DFOWs).

### 5.4 Overnight Autonomous Execution — Ask, Don't Assume

**What I proposed (wrong):** An "overnight execution decision rule" treating autonomy as a standing capability calibrated by DFOW type.

**Owner correction (right):** Ask explicitly. Permission is per-request, not standing. A prior grant doesn't carry forward.

**Codified as feedback memory:** `feedback_overnight_autonomy_permission.md`. Elevated to SKILL.md as POAM R2-024c (Owner Autonomy Authorization).

---

## Area 6 — Reusable Patterns Summary

### 6.1 Confirmed Patterns (≥3 Occurrences or Strong Signal)

Each of these is codified in memory and referenced from MEMORY.md:

| Pattern | Memory file | Origin evidence in GRIFFIN |
|---|---|---|
| Bridge Module for SDK Integration | `pattern_bridge_module.md` | 3 occurrences: agent_classifier.py, cloud_sql_config.py, ml_classifier.py |
| Persona-driven documentation | `pattern_persona_driven_docs.md` | Drove entire 8-doc suite + Red Team attack vectors |
| Adoption accelerators | `pattern_adoption_accelerators.md` | Implementation Playbook + Technical Transition Guide |
| Card UI as small-data mitigation | `pattern_card_ui_small_data.md` | Central to Streamlit 3-card UI + Word export |
| Staging branch → test → merge | `pattern_staging_deployment.md` | Used throughout sprint for every non-trivial change |

### 6.2 Unvalidated Candidates (1 Occurrence, Logged for Watch)

Logged to `project_skill_backlog.md` or noted in this archive, not codified as memory:

- **Three-Mode CLI pattern** (`batch_ingest.py`: extract → classify → ingest) — 1 direct use, architecturally strong, awaiting 2nd use
- **Confirm Classification button as organic training data accumulator** — built in GRIFFIN but **effects never QC'd** (data quality of confirmations, bias accumulation, wrong-confirmation handling). Promising, unvalidated. Do NOT deploy beyond POC without a QC pass on the feedback loop.
- **Background JVM warmup via daemon thread** — 1 direct use in GRIFFIN, architecturally strong, awaiting 2nd use

### 6.3 One-Offs That Should NOT Generalize

- **Sidebar hotfix (one-word config toggle pushed to main)** — defensible in context, codifies PM direct-edit if treated as pattern
- **45-minute conda → 5-minute pip rebuild workaround** — specific to April 2026 Streamlit Cloud behavior
- **D-001 QC deferral** — watching via CQM Issues Log; not a pattern yet

---

## Framework Changes Summary (Where to Find Them)

### SKILL.md updates (POAM items)
- **R2-022** — Persona identification during Preparatory Phase §3 (input verification)
- **R2-023** — Spec-reality grep check during Preparatory Phase §3
- **R2-024a** — PM Direct-Edit Anti-Pattern (new "PM Active Role" section)
- **R2-024b** — PM Downtime Task Menu (new "PM Active Role" section)
- **R2-024c** — Owner Autonomy Authorization (new "PM Active Role" section)
- **R2-025** — Owner UAT recommended practice (Completion Sequence §2, before Red Team)

### documentation-templates.md updates
- **R2-026** — Rendering Fidelity Criteria category in Acceptance Criteria Template

### Memory updates (new files)
- `pattern_bridge_module.md`
- `pattern_persona_driven_docs.md`
- `pattern_adoption_accelerators.md`
- `pattern_card_ui_small_data.md`
- `pattern_staging_deployment.md`
- `feedback_complementary_tooling.md` (added earlier in retro)
- `feedback_document_polish_matrix.md`
- `feedback_communication_modes.md`
- `feedback_pm_downtime_reconciliation.md`
- `feedback_overnight_autonomy_permission.md`
- `cqm-issues-log.md` (new cross-project log)

### Memory updates (existing files revised)
- `feedback_pptx_style.md` — added medium-dependent palette qualifier; "don't hardcode default, present options"
- `MEMORY.md` — indexed all new entries; added "GRIFFIN-origin Patterns" section

### Skill backlog updates
- `project_skill_backlog.md` — added "Documentation Suite Planner" as Medium/Medium candidate

### Assets built
- `Claude Skills/assets/palettes/` — palette library (catalog + per-palette specs with CSS custom properties, pptxgenjs color tokens, python-docx RGB values)

---

## Meta-Observation: What This Retrospective Produced

The GRIFFIN retrospective itself was an exercise in CQM discipline. Six areas walked through systematically, Owner course-corrections captured in real-time via memory saves (4 incorrect framings corrected: H2O framing, consolidation of Client Data Onboarding, Briefing/Playbook consolidation, Reconciliation DFOW framing, overnight autonomy assumption), patterns codified at the moment of identification rather than batch-saved at the end.

The course corrections are themselves the lesson: **systematic retrospectives surface reasoning patterns that a summary wouldn't**. Four of my initial framings were wrong in the same direction (consolidating for efficiency, assuming authority, treating demo as design constraint). Without the walkthrough, those patterns would have propagated into future projects unchanged.

**This retrospective format is recommended for future project closeouts.** The cost is ~2 hours of focused walkthrough; the value is several memory updates that prevent the same corrections in future conversations.

---

## References

**Source artifacts:**
- PM journal: `cqm-sessions/griffin-final-sprint/pm-journal.md`
- Post-presentation Red Team: `cqm-sessions/griffin-final-sprint/red-team-reports/griffin-post-presentation.json`
- Final delivery Red Team: `cqm-sessions/griffin-final-sprint/red-team-reports/final-delivery-review.json`
- 11th Hour QC: `cqm-sessions/griffin-final-sprint/working-drafts/11th-hour-qc-report.md`

**Memory files:** `~/.claude/projects/C--Users-salva-Desktop-MSBA-Claude-Skills/memory/` — see MEMORY.md index

**CQM framework:** `~/.claude/plugins/marketplaces/local-desktop-app-uploads/cqm-orchestrator/skills/cqm-orchestrator/SKILL.md`

**Related projects:**
- GRIFFIN reorg (2026-04-07): `cqm-sessions/griffin-reorg/` — 43 criteria, 0 defects. Established reorg patterns.
- GRIFFIN Lessons Learned (prior): `docs/GRIFFIN-Lessons-Learned.md` — longitudinal lessons document
