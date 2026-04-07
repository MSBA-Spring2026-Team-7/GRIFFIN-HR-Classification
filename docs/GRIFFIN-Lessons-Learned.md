# GRIFFIN Project Reorganization -- Lessons Learned

**Date:** 2026-04-07
**CQM Session:** griffin-reorg
**Tier:** Full Three-Phase, Reduced Cadence (POAM R2-015)
**Outcome:** 43/43 acceptance criteria PASS, 0 deficiencies, 0 rework cycles

---

## Part 1: Project Story

### The Mission

GRIFFIN (Government Role Identification and Financial Framework Integration Network) is an AI-powered HR classification system built for William & Mary's Human Resources department. It scrapes Virginia's DHRM career group data, trains an H2O AutoML classifier on Workday position descriptions, and deploys a LangChain multi-agent system that can classify a new position into one of seven career group families and recommend an appropriate pay grade. The project spans two graduate courses (BUAD 5742 AI, BUAD 5722 Big Data) and a four-person team.

### The Problem

GRIFFIN grew organically across 22 tasks and 4 workstreams. Notebooks lived alongside their output folders. Reference Excel files sat in `data/hr_handoff/`. Training CSVs floated at the `data/` root. Scrape caches nested inside `notebooks/`. Duplicate notebooks (SAlvarado_ prefixed, _portable suffixed) cluttered the workspace. A conversation history folder, proof-of-concept CSVs, and an old `assignment5/` directory with live API keys all coexisted at the project root. There was no single document explaining how the pieces connected.

The result: a project that worked, but that no teammate could navigate without tribal knowledge, and no professor could evaluate without a guided tour.

### The Operation

The reorganization was executed as a CQM-orchestrated task with three Definable Features of Work (DFOWs):

| DFOW | Description | Criteria | Agent Type |
|------|-------------|----------|------------|
| D-001 | Folder reorganization: create target directories, move/rename all files, archive legacy items | 17 | General-purpose Superintendent |
| D-002 | Path fixup: update every internal reference in 5 notebooks, 1 app script, .gitignore, README | 10 | General-purpose Superintendent |
| D-003 | Operations guide: create a 1,339-line interactive HTML document explaining how the system works | 16 | General-purpose Superintendent |

**Hard dependency chain:** D-001 before D-002 (cannot fix paths until files are in new locations). D-001 before D-003 (operations guide file map must reflect final structure). D-002 to D-003 was a soft dependency -- the guide could reference target paths from the plan and verify at integration.

### The Numbers

| Metric | Value |
|--------|-------|
| Files in pre-modification archive | 121 |
| Archive size | 12.6 MB |
| Archive integrity | SHA-256 manifest, all 121 hashes verified |
| Acceptance criteria defined | 43 (17 + 10 + 16) |
| QC inspections conducted | 4 (3 initial + 1 pre-final) |
| Total deficiencies found | 0 (0 Critical, 0 Major, 0 Minor) |
| Rework cycles | 0 |
| Files committed to reorganized structure | 102 |
| Numbered notebooks | 5 (1_environment_setup through 5_h2o_automl) |
| Operations guide | 1,339 lines, 56 KB, 8 sections, SVG diagram, searchable file map |
| Decisions documented | 12 (4 in D-001, 5 in D-002, 3 in D-003) |
| Assumptions independently audited by QC | 9 (3 per DFOW), all confirmed |

---

## Part 2: Technical Decisions That Mattered

### Decision 1: Constraint vs. Criteria -- assignment5/ and cqm-sessions/ at Root

**The tension:** Acceptance criterion S-1 specified the "exact" set of root directories. But the execution plan contained two explicit constraints: "Do NOT remove assignment5/" (it held live API keys in `.env`) and "Do NOT move or modify cqm-sessions/" (active CQM workspace).

**What was decided:** The Superintendent honored the constraints over the criteria's "exactly" language (DEC-001, DEC-002). The QC agent agreed: an explicit constraint from the plan owner overrides a criterion's implied exclusivity.

**What this teaches:** In any specification, constraints (things you must NOT do) take precedence over targets (things you should achieve). When a criterion says "exactly X" but a constraint says "do not touch Y," the constraint wins. The right response is not to fail the criterion silently -- it is to document the override, explain the reasoning, and let QC verify the judgment. Both the Superintendent's notes and the QC reports reference these decisions explicitly, so anyone reviewing the session can trace why S-1 has two extra items.

**Analogous to:** In military planning, ROE (rules of engagement) always override the operations order. If OPORD says "clear the building" but ROE says "do not enter the mosque," you do not enter the mosque and you document why the building was not fully cleared.

### Decision 2: Semantic Directory Design -- data/reference/ vs. data/training/ vs. data/cache/

**The tension:** The old structure had data scattered: `data/hr_handoff/` for reference Excels, loose CSVs at `data/` root, `raw_pages/` nested inside `notebooks/`. Everything was "data," but not all data serves the same purpose.

**What was decided:** Four semantic subdirectories:
- `data/reference/` -- the 7 DHRM Excel files (the "knowledge base," read-only after creation)
- `data/training/` -- the 4 ML pipeline CSVs (postings, training set, features, exclusions)
- `data/cache/` -- raw scrape caches (gitignored, regenerable from source)
- `data/schema/` -- SQL schema and visual diagram (structural documentation)

**What this teaches:** Directory names should communicate purpose, not origin. "hr_handoff" told you where the files came from (HR handed them off). "reference" tells you what the files are for (they are the reference tables the system reads). When a new team member opens the project, `data/reference/` is self-explanatory; `data/hr_handoff/` requires context.

### Decision 3: Path Fixup Strategy -- Relative Paths, One Exception Documented

**The tension:** The reorganization moved every file. Every `os.path.join`, `read_csv`, `read_excel`, and `open()` call in 5 notebooks and 1 application script now pointed to nonexistent locations. Additionally, Notebook 1 contained a hardcoded absolute path to the system conda executable (`C:\ProgramData\anaconda3\Scripts\conda.exe`).

**What was decided:** All project file references converted to relative paths from the file's new location. The conda executable path was left unchanged (DEC-001) because it references a system binary, not a project file. Cell outputs containing old paths were also left unchanged (DEC-005) because they are historical execution records, not code.

**What this teaches:** Path fixup scope must be defined precisely. "Fix all paths" sounds simple, but the conda path is technically a hardcoded absolute path -- just not one that the reorganization broke. The decision to exclude it was correct because: (a) changing it would break the notebook for the team member who wrote it, (b) the constraint said to modify only path strings related to the reorganized folder structure, and (c) QC verified the reasoning. Criterion C-3 passed "with note," which is the right outcome -- a clean pass with documented rationale, not a silent skip.

### Decision 4: CSV Fallback Redirected to data/reference/ (DEC-002)

**The tension:** Notebook 2's DHRM pipeline has a fallback path: if the database connection fails, it exports reference data as CSVs. Previously these went to `output_csv/` inside the notebooks directory. That folder no longer exists.

**What was decided:** Redirect to `../data/reference/` because the CSV fallback produces the same reference tables as the Excel primary path. The semantic home for "DHRM reference data" is `data/reference/`, regardless of format.

**What this teaches:** When redirecting output paths, think about what the output IS, not where it used to go. The CSVs are reference data. They belong with reference data. This is the semantic directory principle applied to a non-obvious case.

### Decision 5: Operations Guide Size vs. Target (D-003-DEC-001)

**The tension:** The plan estimated 600-900 lines. The actual file is 1,339 lines.

**What was decided:** Accept the overshoot. The file map table alone is 230+ lines with 34 verified entries. Cutting content to hit a line target would sacrifice accuracy or completeness. The 56KB file loads instantly in any browser.

**What this teaches:** Size targets in specifications are estimates, not contracts. The correct response to exceeding an estimate is to evaluate whether the overshoot harms the deliverable's purpose (it did not -- the guide is more thorough than planned) and document the decision. If the target had been a hard constraint ("must fit in a 10KB email"), the calculus would be different.

---

## Part 3: CQM Framework Lessons

### What Worked Well

**Reduced cadence was appropriate and efficient.** The task had three or fewer DFOWs, well-understood scope, and no prior failures -- all prerequisites for reduced cadence per POAM R2-015. The standard cadence would have required QC at 25%, 50%, 75%, and 100% for each DFOW. Reduced cadence used only Initial and Pre-Final. Given that all three DFOWs passed Initial with zero findings, the intermediate checkpoints would have been pure overhead. The reduced cadence saved four QC deployments without sacrificing quality.

**The pre-modification archive proved its value as insurance.** 121 files, 12.6 MB, SHA-256 manifest. No rollback was needed -- but the archive served three other purposes: (a) the QC agent used it to verify file sizes matched after D-001 moves, (b) the `environment.yml` SHA-256 comparison in criterion P-2 used the archive as ground truth, and (c) the archive now exists as a permanent record of the project's pre-reorganization state for anyone who needs to understand the before/after. The cost of creating it was trivial (one copy + hash operation). The cost of NOT having it, if something had gone wrong, would have been a full manual reconstruction.

**43 binary acceptance criteria eliminated ambiguity.** Every criterion was verifiable with a concrete test: "file exists at path X," "grep returns zero matches for pattern Y," "SHA-256 hash matches Z." There were no subjective criteria like "code is well-organized" or "documentation is clear." This made QC inspection mechanical -- the QC agent did not need to exercise judgment about what "good enough" meant. It checked each criterion against evidence and reported PASS or FAIL.

**The assumption audit layer caught what criteria alone cannot.** Each QC inspection independently audited three assumptions -- statements the Superintendent asserted as true but that could be wrong despite criteria passing. For example, D-001 QC audited "7 Excel files copied with identical content" by comparing byte sizes against the pre-modification manifest. This is stronger than criterion F-1 alone ("7 files exist in data/reference/"), which could pass even if files were corrupted during copy. Across 9 assumptions audited, all confirmed. This layer costs little and protects against the "all green but actually broken" failure mode.

### Zero-Defect Outcome Analysis

Was this luck, good criteria, or good Superintendents?

**Not luck.** The task had clear prerequisites (a frozen plan with explicit file-by-file instructions), well-defined scope boundaries (D-001 = moves only, D-002 = paths only, D-003 = one new file), and a hard dependency chain that prevented integration errors from compounding. Luck would mean "we got away with something" -- but there was nothing to get away with.

**Partly good criteria.** The 43 criteria covered the right failure modes: data loss (P-3: every file exists in new structure or archive), broken paths (C-1: no old path references remain), security (C-1/C-2: no real API keys exposed), content fidelity (FI-1: architecture decisions traceable to source). The criteria were comprehensive enough that a Superintendent who satisfied all of them would, by definition, have completed the task correctly.

**Mostly good execution design.** The plan itself was well-structured: copy-first-then-remove (prevents data loss), sequential DFOWs with hard dependencies (prevents integration errors), explicit constraints (prevents unauthorized modifications). The Superintendents followed the plan faithfully and documented every deviation. When a criterion conflicted with a constraint, they made the right call and documented it. Zero defects in this case reflects a well-scoped task with a well-designed plan, not heroic error-free execution.

### What Could Be Improved

**Some criteria were trivially true and added QC overhead without protective value.** F-8 ("models/ directory exists, empty") and F-9 ("ppt/ directory exists, empty") are one-line `mkdir` commands that could not meaningfully fail. Creating two criteria, two self-assessment entries, and two QC verification steps for "did you create an empty directory" is overhead that protects against nothing. In future sessions, trivially true criteria like these should be grouped into a single structural criterion ("all rubric placeholder directories exist") to reduce the inspection surface.

**The pre-final QC added limited incremental value when all Initial phases were clean.** The pre-final inspected all 43 criteria again plus cross-DFOW integration. Given that D-001, D-002, and D-003 all passed Initial with zero findings, the pre-final was mostly a re-verification rather than a discovery exercise. Its one unique contribution was the cross-DFOW integration check (verifying D-002 paths resolve to D-001 locations, and D-003's file map reflects D-001's structure). In future reduced-cadence sessions, the pre-final could be scoped to cross-DFOW integration only when all Initials pass clean.

**No criteria explicitly tested "can you actually run notebook 3 end-to-end after the path changes."** D-002's criteria verified that paths resolve to existing files and that old patterns are eliminated -- but they did not verify that a notebook would execute without error. This is appropriate for a reorganization task (running notebooks requires API keys, database connections, and Java), but it is a gap worth acknowledging. A "smoke test" criterion for at least one notebook's import cell would have added confidence.

---

## Part 4: Patterns for Future Projects

### Pattern 1: Archive Before You Touch

Before any modification task, create a complete archive of the current state with a SHA-256 manifest. This is non-negotiable (POAM R2-013). The archive is not just a rollback mechanism -- it is ground truth for verification, a historical record, and insurance against failure modes you did not anticipate.

**GRIFFIN application:** 121 files, 12.6 MB, completed in one operation before any file was moved. The manifest was referenced three times during QC.

**When to apply:** Any task that modifies, renames, moves, or deletes existing files. The cost is always low (disk space is cheap, hashing is fast). The cost of not having it is always high (manual reconstruction, lost state, contested outcomes).

### Pattern 2: Copy-First, Verify, Then Remove

Never move a file in one operation. Instead: (1) copy to the new location, (2) verify the copy matches the original (byte size or hash), (3) only then remove the original.

**GRIFFIN application:** The D-001 Superintendent explicitly stated "every source file verified at its new location by byte-size comparison before originals were deleted." This is why P-3 (no data loss) passed unambiguously.

**When to apply:** Any file reorganization. The `mv` command is atomic on most systems, but when you are moving dozens of files across a nested directory structure, one failed `mv` in the middle leaves you in an inconsistent state. Copy-verify-remove is idempotent: if it fails partway through, you still have all originals.

### Pattern 3: Numbered Artifacts for Pipeline Clarity

Prefix sequential artifacts with numbers: `1_environment_setup.ipynb`, `2_dhrm_pipeline.ipynb`, `3_workday_scrape.ipynb`, `4_feature_engineering.ipynb`, `5_h2o_automl.ipynb`.

**GRIFFIN application:** The old structure had notebooks named by content (`griffin_dhrm_pipeline.ipynb`, `griffin_workday_scrape.ipynb`). The new structure prepends a number. Any team member or professor can now see the execution order at a glance without reading documentation.

**When to apply:** Any project with sequential processing steps, multi-notebook pipelines, or ordered deliverables. The number prefix sorts correctly in file explorers and makes the pipeline self-documenting.

### Pattern 4: Semantic Directories Over Flat Structures

Organize by purpose (reference, training, cache, schema), not by origin (hr_handoff, output_csv, raw_pages) or tool (notebooks, scripts).

**GRIFFIN application:** `data/` went from a flat mix of CSVs, Excels, and cache folders to four purpose-driven subdirectories. Each subdirectory answers "what is this data FOR?" not "where did this data come FROM?"

**When to apply:** Any project with more than ~10 data files. The test: can a new team member, seeing only the directory name, understand what they will find inside?

### Pattern 5: Operations Guide as System Documentation

A single HTML page that answers: what does this system do, how do the pieces connect, how do I run each component, and where is every file.

**GRIFFIN application:** `griffin-operations-guide.html` -- 1,339 lines, 8 sections, SVG data flow diagram, searchable file map, collapsible notebook walkthroughs, team role assignments. Self-contained (inline CSS + JS, no external dependencies). This is the document a teammate opens when they need to pick up where someone else left off.

**When to apply:** Any multi-component project with more than one contributor. The operations guide is not a README (which orients newcomers) or API docs (which document interfaces). It is the "how it all works" document -- the system's owner's manual.

---

## Part 5: Post-Project Capture

### 1. If you had to solve this again, what would you do differently?

**Define criteria categories more carefully.** The functional, structural, content, and preservation categories were useful, but the line between them blurred. F-8/F-9 (empty directory exists) are structural, not functional. The fidelity category in D-003 (FI-1, FI-2) was a good addition -- it tested whether claims in the deliverable matched reality, which is distinct from "does the file exist" or "is the format correct." Future sessions should use a consistent category taxonomy: existence (does it exist?), correctness (is it right?), fidelity (does it match its source?), preservation (is the old thing still intact?), security (are secrets protected?).

**Scope the pre-final to integration-only when Initials are clean.** The full re-verification added time without finding anything new. Cross-DFOW integration is the unique value of the pre-final; lean into that.

**Add one smoke-test criterion per DFOW.** Even if full execution is impractical, "import the first cell without error" or "load the HTML in a browser without console errors" would catch integration failures that file-existence checks miss.

### 2. Anything reusable as a skill or template?

**Project reorganization template.** The three-DFOW pattern (structure, fixup, documentation) is generalizable to any codebase cleanup:
- D-001: Move files to target structure (archive first, copy-verify-remove)
- D-002: Fix all internal references (paths, imports, configs)
- D-003: Create or update system documentation reflecting the new structure

This could be codified as a CQM task template with pre-built criteria categories. The 43 criteria from this session are a starting point -- strip the GRIFFIN-specific details and you have a reusable checklist for any reorganization.

**Operations guide HTML template.** The 8-section structure (overview, data flow, how-to-run, quick start, architecture decisions, file map, environment setup, team roles) is a strong default for any multi-component project. The CSS/JS from `griffin-operations-guide.html` could be extracted into a template.

### 3. Key learning to persist?

**Constraint-over-criteria precedence rule.** When a specification contains both criteria (what to achieve) and constraints (what not to touch), constraints win. Document the override, explain the reasoning, and let QC verify. This pattern will recur in every CQM session where the plan has scope boundaries.

**The archive-as-ground-truth pattern.** The pre-modification archive was used more for verification (3 references during QC) than for rollback (0 uses). This reframes the archive from "insurance policy" to "verification infrastructure." Future sessions should plan to reference the archive during QC, not just hope they never need it.

**Binary criteria produce zero-ambiguity QC.** Subjective criteria ("is the code well-organized?") create judgment calls during QC that slow the process and introduce inter-rater variability. Binary criteria ("does file X exist at path Y with size > Z?") produce unambiguous results. The extra effort to make every criterion binary pays off in faster, more reliable QC.

---

## Memory Update Recommendations

### Additions to MEMORY.md

Add under `## CQM Orchestrator` or as a new section:

```markdown
## CQM Lessons Learned
- [GRIFFIN reorg lessons](../Courses/AI Course/HR_Classification_Project/docs/GRIFFIN-Lessons-Learned.md) -- first full CQM session; patterns: archive-as-ground-truth, constraint-over-criteria precedence, binary criteria for zero-ambiguity QC
- Reduced cadence validated: 3 DFOWs, 43 criteria, 0 defects, 0 rework. Intermediate checkpoints were correctly skipped.
- Pre-final scope opportunity: when all Initials pass clean, scope pre-final to cross-DFOW integration only.
- Trivially true criteria (empty dir exists) should be grouped to reduce QC surface.
```

### Updates to Existing Files

**`project_skill_backlog.md`** -- Add two candidate templates:
1. "Project Reorganization CQM Template" -- 3-DFOW pattern (structure/fixup/docs) with reusable criteria categories
2. "Operations Guide HTML Template" -- 8-section structure extracted from griffin-operations-guide.html

**`feedback_cqm_qc_independence.md`** -- Add note: "Pre-final adds limited value when all Initials are clean. Consider scoping to cross-DFOW integration checks only in reduced-cadence sessions."

### New Reference Files to Create

**`reference_cqm_criteria_design.md`** -- Codify the lessons on criteria design:
- Binary over subjective (always)
- Group trivially-true checks into single criteria
- Use five categories: existence, correctness, fidelity, preservation, security
- Include one smoke-test criterion per DFOW
- Constraint-over-criteria precedence rule with the GRIFFIN example

**`project_griffin.md`** -- Project reference file (similar format to `project_dv_course.md`):
- Location: `Desktop\MSBA\AI Course\HR_Classification_Project\`
- Status: Layers 1-3 complete (data pipeline, ML training, LangChain agents), Layer 4 pending (Streamlit UI)
- Team: Anmol (Streamlit/app), Brynn (reports/research), Jhei-R (deck/docs)
- Key docs: `docs/griffin-operations-guide.html`, `GRIFFIN_CLAUDE_MD.md`, `README.md`
- CQM session: `cqm-sessions/griffin-reorg/` (completed 2026-04-07, 43/43 PASS)
- Red team: Gemini adversarial review completed; prompt archived at `archive/old_docs/red-team-gemini-prompt.md`
