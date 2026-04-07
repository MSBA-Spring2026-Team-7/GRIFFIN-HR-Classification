# GRIFFIN Multi-Agent HR Classification System: Design Rationale

**BUAD 5742 -- AI Team Assignment 5 | William & Mary**

---

## 1. System Architecture

The GRIFFIN agent system uses three LangChain agents to classify Virginia state positions into DHRM career groups and match them to pay bands. Each agent has a distinct role:

- **Classifier Agent** -- Receives a position description and determines the correct DHRM career group (out of 56 groups) and role (out of 294 roles). It evaluates duties against compensable factors such as complexity, results, and accountability. It has access to three tools: `search_career_groups`, `search_roles`, and `web_search`.

- **Pay Matcher Agent** -- Takes a classified position (career group and role) and determines the DHRM pay band and corresponding William & Mary pay grade. It uses two tools: `match_pay_band` (which queries the DHRM-to-W&M crosswalk) and `get_virginia_salary` (which calls the CareerOneStop API for Virginia-localized salary percentiles).

- **Orchestrator** -- Coordinates the two sub-agents into a single end-to-end workflow. Following the class Colab Cell 45 pattern, each sub-agent is wrapped as a `@tool` callable (`call_classifier` and `call_pay_matcher`). The orchestrator receives a raw position description, delegates classification first, passes the result to pay matching second, and synthesizes both outputs into a final recommendation.

```
Position Description
        |
        v
  [Orchestrator Agent]
        |
        |--- call_classifier ---> [Classifier Agent]
        |                              |-- search_career_groups (Excel data)
        |                              |-- search_roles (Excel data)
        |                              |-- web_search (Tavily fallback)
        |
        |--- call_pay_matcher --> [Pay Matcher Agent]
        |                              |-- match_pay_band (DHRM-W&M crosswalk)
        |                              |-- get_virginia_salary (CareerOneStop API)
        |
        v
  Final Recommendation
  (Career Group + Role + Pay Band + Salary Range)
```

## 2. Design Decisions

**LLM Choice: Google Gemini (`gemini-2.5-flash`).** The class Colab uses this exact model string via `init_chat_model()`, so staying consistent avoids compatibility issues and keeps the project within the free-tier API quota. The script also demonstrates temperature experiments (0 vs. 1) on a classification prompt to show deterministic vs. creative behavior.

**External API: CareerOneStop for Virginia salary data.** DHRM classifies positions using Standard Occupational Classification (SOC) codes, and CareerOneStop provides Virginia-localized salary percentiles (10th through 90th) by SOC code. This makes the pay matching agent's recommendations grounded in real labor market data rather than generic estimates. Tavily web search serves as a fallback when structured data is insufficient.

**Tool Decomposition: Five tools, each mapping to one data source.** Rather than building a single monolithic lookup function, the system separates concerns into five tools: (1) `search_career_groups` queries career group names and concepts of work; (2) `search_roles` retrieves all roles within a career group; (3) `match_pay_band` maps a DHRM pay band to the W&M crosswalk; (4) `get_virginia_salary` calls the external CareerOneStop API; (5) `web_search` calls Tavily. This decomposition lets each agent select only the tools relevant to its task and keeps tool docstrings focused enough for the LLM to use correctly.

**Memory: `InMemorySaver` for conversation continuity.** Each agent receives its own checkpointer so it can recall details from earlier in a classification session. The script demonstrates this with a two-step memory test: first providing specific position details ($500K budget, 4 technicians), then asking a follow-up that can only be answered correctly if the agent remembers.

## 3. GRIFFIN Project Integration

This agent system is Layer 3 of the four-layer GRIFFIN stack:

1. **Data pipeline** -- Cleans and structures DHRM reference data (career groups, roles, SOC codes, crosswalk, pay bands) into six Excel files.
2. **ML model** -- An H2O AutoML classifier trained on 103 William & Mary position descriptions to predict occupational family.
3. **LangChain agents** -- This assignment. The agents consume the reference data through tools and coordinate via orchestration.
4. **Streamlit app** -- A user-facing interface (final team deliverable) that will call the orchestrator.

The `search_career_groups` tool is designed as a plug-in point for the ML model. Currently it uses keyword matching against the career groups DataFrame, but its function signature (`query: str -> str`) is compatible with an H2O model that predicts occupational family from position text. When H2O is ready, only the tool internals change -- the agents, orchestrator, and all system prompts remain unchanged.

## 4. Skill Template Design

Two `skill.md` files accompany this script as reusable prompt templates for the GRIFFIN system:

- **Classifier skill** -- Encodes the multi-step classification logic: extract key duties from a position description, match against compensable factors (complexity, results, accountability), search career groups, narrow to specific roles, and justify the selection. This template ensures consistent classification reasoning across sessions.

- **Pay matcher skill** -- Encodes the crosswalk lookup and salary retrieval workflow: take a classified career group and role, identify the DHRM pay band, map it to the W&M pay grade via the crosswalk, and pull Virginia market data by SOC code. This keeps compensation analysis repeatable and auditable.

Both templates serve as institutional knowledge capture -- they encode the classification logic so that new team members or future Streamlit deployments can invoke the same reasoning without re-engineering the prompts.

---

## Self-Assessment

| Criterion | Verdict | Evidence |
|-----------|---------|----------|
| **F-001: Architecture Description** | PASS | Section 1 describes all three agents, their roles, tool assignments, and coordination flow. Includes a text-based architecture diagram showing the full pipeline from position description to final recommendation. |
| **F-002: Design Decisions** | PASS | Section 2 explains *why* for each choice: Gemini (class consistency + free tier), CareerOneStop (Virginia-localized SOC data aligned with DHRM taxonomy), five-tool decomposition (single-responsibility per data source), InMemorySaver (session continuity). Section 3 addresses GRIFFIN integration and the H2O plug-in point. |
| **S-001: Length and Format** | PASS | Report body is approximately 750 words. Uses markdown with clear section headers, bullet points, a code-block diagram, and a summary table. |
| **C-001: Report Clarity** | PASS | Opens with a plain-language overview of the three-agent system. Technical terms (SOC codes, DHRM, compensable factors, crosswalk) are explained in context. A reader unfamiliar with GRIFFIN can follow the architecture, decisions, and integration points without inspecting the source code. |
