"""
GRIFFIN Multi-Agent HR Classification System
=============================================
AI Team Assignment 5 — BUAD 5742, William & Mary

Uses LangChain agents to classify Virginia state positions into DHRM
career groups/roles and match them to appropriate pay bands. Built on
real GRIFFIN reference data (career groups, roles, SOC codes, pay bands,
and the DHRM-to-W&M crosswalk).

All 8 components implemented: LLM initialization, agent creation,
message handling, streaming, custom tools, external API tools,
agent memory, and multi-agent orchestration.
"""

# ============================================================
#  IMPORTS
# ============================================================
# Standard library
import os
import sys
from pprint import pprint

# Third-party
import pandas as pd
import requests

# Load API keys from .env file (keeps secrets out of source code).
# pip install python-dotenv if not already installed.
try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env file in the same directory as the script
except ImportError:
    pass  # dotenv not installed — keys must be set as system env vars instead

# Tavily is optional — only needed for the web_search tool in Component 6.
# Wrapped in try/except so the script doesn't crash if not installed.
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

# LangChain / LangGraph
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver


# ============================================================
#  CONFIGURATION
# ============================================================

# API keys loaded from environment — never hardcoded in source.
# Set these in your shell or .env before running.
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if not GOOGLE_API_KEY:
    print("[WARNING] GOOGLE_API_KEY not set. LLM calls will fail.")

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
CAREERONESTOP_TOKEN = os.environ.get("CAREERONESTOP_TOKEN", "")
CAREERONESTOP_USER_ID = os.environ.get("CAREERONESTOP_USER_ID", "")

# Paths are relative to *this script's* directory so the project stays
# portable across machines (Windows, Mac, Linux).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = SCRIPT_DIR  # Data lives alongside the script in the submission folder
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "hr_handoff")
TRAINING_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "workday_training.csv")


# ============================================================
#  DATA LOADING
# ============================================================
# Load all six reference Excel files once at module level so every tool
# and agent can access them without repeated I/O. Using the openpyxl
# engine because the files are .xlsx format.

print("[INFO] Loading GRIFFIN reference data ...")

career_groups_df = pd.read_excel(
    os.path.join(DATA_DIR, "career_groups.xlsx"), engine="openpyxl"
)
roles_df = pd.read_excel(
    os.path.join(DATA_DIR, "roles.xlsx"), engine="openpyxl"
)
soc_codes_df = pd.read_excel(
    os.path.join(DATA_DIR, "soc_codes.xlsx"), engine="openpyxl"
)
crosswalk_df = pd.read_excel(
    os.path.join(DATA_DIR, "crosswalk.xlsx"), engine="openpyxl"
)
dhrm_pay_bands_df = pd.read_excel(
    os.path.join(DATA_DIR, "dhrm_pay_bands.xlsx"), engine="openpyxl"
)
wm_pay_grades_df = pd.read_excel(
    os.path.join(DATA_DIR, "wm_pay_grades.xlsx"), engine="openpyxl"
)

# Load one sample position description for demo purposes.
# workday_training.csv has 103 rows of real W&M job postings.
training_df = pd.read_csv(TRAINING_DATA_PATH)
sample_position = training_df.iloc[0]["censored_text"]

print(f"[INFO] Loaded {len(career_groups_df)} career groups, "
      f"{len(roles_df)} roles, {len(soc_codes_df)} SOC mappings, "
      f"{len(crosswalk_df)} crosswalk rows, "
      f"{len(dhrm_pay_bands_df)} DHRM pay bands, "
      f"{len(wm_pay_grades_df)} W&M pay grades.")
print(f"[INFO] Training data: {len(training_df)} position descriptions loaded.")


# ============================================================
#  Component 1: LLM Initialization
# ============================================================
# Why Gemini: the class Colab uses google_genai:gemini-2.5-flash,
# so we match that to stay consistent with the professor's examples.

def demo_llm_initialization():
    """Demonstrate direct LLM invocation and temperature experiments."""

    print("\n" + "=" * 60)
    print("  Component 1: LLM Initialization")
    print("=" * 60)

    llm = init_chat_model(model="google_genai:gemini-2.5-flash")

    # --- Direct invocation (no agent) ---
    # This shows the LLM can answer without any agent scaffolding,
    # which is useful for quick sanity checks.
    prompt = (
        "Given the following abbreviated position description, suggest "
        "which broad Virginia DHRM career group it might belong to. "
        "Reply in one sentence.\n\n"
        f"Position: {sample_position[:300]}"
    )

    print("\n--- Direct LLM invocation (default temperature) ---")
    response = llm.invoke(prompt)
    print(response.content)

    # --- Temperature experiment ---
    # temp=0 should give a focused, deterministic answer.
    # temp=1 should produce more creative / varied output.
    # We run both on the SAME prompt so the comparison is fair.
    classification_prompt = (
        "List three possible DHRM career groups that a 'Research Scientist' "
        "position at a Virginia university might fall under. Be specific."
    )

    print("\n--- Temperature = 0 (deterministic) ---")
    llm_temp0 = init_chat_model(
        model="google_genai:gemini-2.5-flash", temperature=0
    )
    response_temp0 = llm_temp0.invoke(classification_prompt)
    print(response_temp0.content)

    print("\n--- Temperature = 1 (creative) ---")
    llm_temp1 = init_chat_model(
        model="google_genai:gemini-2.5-flash", temperature=1
    )
    response_temp1 = llm_temp1.invoke(classification_prompt)
    print(response_temp1.content)

    # Return the default LLM for use in later components
    return llm


# ============================================================
#  Component 2: Agent Creation
# ============================================================
# Two domain-specific agents, each with a tailored system prompt that
# grounds it in the GRIFFIN data. Agents are created with InMemorySaver
# so they can be reused with memory in Component 7.

CLASSIFIER_SYSTEM_PROMPT = (
    "You are a Virginia DHRM position classification specialist. "
    "Given a position description, you analyze the duties and "
    "responsibilities to determine the correct DHRM career group and "
    "role classification. You have access to tools that search the 56 "
    "DHRM career groups and 294 roles. Match duties against compensable "
    "factors (Complexity, Results, Accountability) to find the best "
    "classification. Always explain your reasoning step-by-step."
)

PAY_MATCHER_SYSTEM_PROMPT = (
    "You are a compensation analyst specializing in Virginia state "
    "employee pay structures. Given a classified position (career group "
    "and role), you determine the appropriate DHRM pay band and "
    "corresponding W&M university pay grade. You can look up "
    "Virginia-specific salary data by SOC code and use the DHRM-to-W&M "
    "crosswalk for pay grade mapping. Provide specific salary ranges "
    "when possible."
)


def create_agents(llm):
    """Build the two core agents: classifier and pay matcher.

    Both get InMemorySaver checkpointers so Component 7 (memory) can
    demonstrate conversation recall later. Tools are wired in from
    Components 5 and 6 — the classifier gets data-search and web-search
    tools, while the pay matcher gets pay-band lookup and salary tools.
    """

    print("\n" + "=" * 60)
    print("  Component 2: Agent Creation")
    print("=" * 60)

    # Classifier agent — classifies positions into career groups / roles.
    # Tools: search_career_groups and search_roles (Component 5) plus
    # web_search (Component 6) for fallback research.
    classifier_memory = InMemorySaver()
    classifier_agent = create_agent(
        model=llm,
        tools=[search_career_groups, search_roles, web_search],
        system_prompt=CLASSIFIER_SYSTEM_PROMPT,
        checkpointer=classifier_memory,
    )
    print("[OK] classifier_agent created with 3 tools (search_career_groups, "
          "search_roles, web_search).")

    # Pay matcher agent — maps classified positions to pay bands.
    # Tools: match_pay_band (Component 5) plus get_virginia_salary
    # (Component 6) for real market data.
    pay_matcher_memory = InMemorySaver()
    pay_matcher_agent = create_agent(
        model=llm,
        tools=[match_pay_band, get_virginia_salary],
        system_prompt=PAY_MATCHER_SYSTEM_PROMPT,
        checkpointer=pay_matcher_memory,
    )
    print("[OK] pay_matcher_agent created with 2 tools (match_pay_band, "
          "get_virginia_salary).")

    return classifier_agent, pay_matcher_agent


# ============================================================
#  Component 3: Message Handling
# ============================================================
# Multi-turn conversation using HumanMessage / AIMessage. This simulates
# a realistic back-and-forth where a user progressively refines a
# classification request — first describing the position, then asking
# for clarification, then requesting a final determination.

def demo_message_handling(classifier_agent):
    """Show multi-turn message handling with the classifier agent."""

    print("\n" + "=" * 60)
    print("  Component 3: Message Handling")
    print("=" * 60)

    # Build a realistic 3-message conversation for position classification.
    # The AIMessage simulates an earlier assistant response to show the
    # agent can process a full conversation history, not just one-shot.
    messages = [
        HumanMessage(content=(
            "I need to classify a position at William & Mary. "
            "The role involves conducting marine biology research, "
            "managing a small lab team, writing grant proposals, "
            "and teaching one graduate seminar per semester."
        )),
        AIMessage(content=(
            "Based on your initial description, this sounds like it could "
            "fall under the Natural & Applied Sciences career group. The "
            "combination of research, team management, and teaching duties "
            "suggests a senior-level role. Could you tell me more about "
            "the level of budget responsibility and independent "
            "decision-making authority?"
        )),
        HumanMessage(content=(
            "The position manages an annual research budget of $500K, "
            "makes independent decisions on research direction, and "
            "reports directly to the department chair. The complexity "
            "level is high — they design novel experimental approaches "
            "and publish in peer-reviewed journals."
        )),
    ]

    print("\n--- Multi-turn conversation (3 messages) ---")
    for i, msg in enumerate(messages):
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        # Truncate display for readability
        preview = msg.content[:120] + "..." if len(msg.content) > 120 else msg.content
        print(f"  [{i + 1}] {role}: {preview}")

    # Invoke the classifier agent with the full conversation history.
    # Using a thread_id so memory can track this conversation.
    config = {"configurable": {"thread_id": "classification-demo-1"}}
    response = classifier_agent.invoke({"messages": messages}, config)

    print("\n--- Classifier Agent Response ---")
    pprint(response["messages"][-1].content)

    return response


# ============================================================
#  Component 4: Streaming Output
# ============================================================
# Stream the classifier agent's response token-by-token, matching the
# exact Colab pattern: agent.stream() with stream_mode="messages".
# This is useful for long classification explanations so the user sees
# output progressively rather than waiting for the full response.

def demo_streaming(classifier_agent):
    """Stream a classification response token-by-token."""

    print("\n" + "=" * 60)
    print("  Component 4: Streaming Output")
    print("=" * 60)

    prompt = HumanMessage(content=(
        "Classify this position into a DHRM career group and role: "
        "An IT professional who designs and maintains enterprise database "
        "systems, leads a team of 3 DBAs, and ensures compliance with "
        "Virginia security standards. The role requires a master's degree "
        "and 7+ years of experience."
    ))

    # New thread so this doesn't mix with Component 3's conversation
    config = {"configurable": {"thread_id": "streaming-demo-1"}}

    print("\n--- Streaming classifier response ---\n")
    for token, metadata in classifier_agent.stream(
        {"messages": [prompt]}, config, stream_mode="messages"
    ):
        if token.content:
            print(token.content, end="", flush=True)

    # Newline after streaming completes
    print("\n")


# ============================================================
#  Component 5: Custom Tools
# ============================================================
# Three custom tools that query the GRIFFIN reference DataFrames.
# Defined at module level so they can be wired into agents in
# create_agents() and also demoed in the main block.


@tool
def search_career_groups(query: str) -> str:
    """Search DHRM career groups by keyword in name and concept of work.

    Args:
        query: Keyword to search for (case-insensitive). Matches against
               career_group_name and concept_of_work columns.

    Returns:
        Top 3 matching career groups with code, name, family, and pay
        band range. Returns a message if no matches found.
    """
    q = query.lower()
    mask = (
        career_groups_df["career_group_name"].str.lower().str.contains(q, na=False)
        | career_groups_df["concept_of_work"].str.lower().str.contains(q, na=False)
    )
    matches = career_groups_df[mask].head(3)

    if matches.empty:
        return f"No career groups found matching '{query}'."

    results = []
    for _, row in matches.iterrows():
        results.append(
            f"Code: {row['career_group_code']} | "
            f"Name: {row['career_group_name']} | "
            f"Family: {row['occupational_family']} | "
            f"Pay Bands: {int(row['pay_band_min'])}-{int(row['pay_band_max'])}"
        )
    return "\n".join(results)


@tool
def search_roles(career_group_code: str) -> str:
    """Look up all roles within a specific DHRM career group.

    Args:
        career_group_code: The 5-digit career group code (e.g., "19030").

    Returns:
        All roles in that group with role_code, role_name, pay_band,
        track, and a truncated role_summary. Returns a message if no
        roles found.
    """
    # Convert to int for matching since the DataFrame column is numeric
    try:
        code_int = int(career_group_code)
    except ValueError:
        return f"Invalid career group code: '{career_group_code}'. Expected a numeric code like '19030'."

    matches = roles_df[roles_df["career_group_code"] == code_int]

    if matches.empty:
        return f"No roles found for career group code '{career_group_code}'."

    results = []
    for _, row in matches.iterrows():
        summary = str(row["role_summary"])[:150] + "..." if len(str(row["role_summary"])) > 150 else str(row["role_summary"])
        results.append(
            f"Role Code: {row['role_code']} | "
            f"Name: {row['role_name']} | "
            f"Pay Band: {row['pay_band']} | "
            f"Track: {row['track']} | "
            f"Summary: {summary}"
        )
    return "\n".join(results)


@tool
def match_pay_band(pay_band: int) -> str:
    """Look up salary ranges for a DHRM pay band and its W&M equivalent.

    Uses the DHRM-to-W&M crosswalk to map a DHRM pay band number to
    the corresponding W&M pay grade with full salary details.

    Args:
        pay_band: DHRM pay band number (1 through 9).

    Returns:
        DHRM salary range and corresponding W&M pay grade with
        min/midpoint/max. Returns a message if pay band not found.
    """
    xwalk_row = crosswalk_df[crosswalk_df["dhrm_pay_band"] == pay_band]

    if xwalk_row.empty:
        return f"Pay band {pay_band} not found in the crosswalk. Valid range is 1-9."

    row = xwalk_row.iloc[0]
    return (
        f"DHRM Pay Band {pay_band}: "
        f"${row['dhrm_min']:,.0f} - ${row['dhrm_max']:,.0f}\n"
        f"W&M Pay Grade: {row['wm_pay_grade']} | "
        f"Min: ${row['wm_min']:,.0f} | "
        f"Midpoint: ${row['wm_midpoint']:,.0f} | "
        f"Max: ${row['wm_max']:,.0f}"
    )


def demo_custom_tools():
    """Demonstrate the three custom tools operating on GRIFFIN data."""

    print("\n" + "=" * 60)
    print("  Component 5: Custom Tools")
    print("=" * 60)

    print("\n--- search_career_groups('engineering') ---")
    result = search_career_groups.invoke({"query": "engineering"})
    pprint(result)

    print("\n--- search_roles('39050') ---")
    result = search_roles.invoke({"career_group_code": "39050"})
    pprint(result)

    print("\n--- match_pay_band(5) ---")
    result = match_pay_band.invoke({"pay_band": 5})
    pprint(result)


# ============================================================
#  Component 6: External API Tool
# ============================================================
# Two external API tools: CareerOneStop Virginia salary lookup and
# Tavily web search. API keys come from environment variables set in
# the Configuration section above.


@tool
def get_virginia_salary(soc_code: str) -> str:
    """Get Virginia-specific salary data from CareerOneStop API.

    Calls the CareerOneStop Compare Salaries endpoint to retrieve
    salary percentiles (10th, 25th, median, 75th, 90th) for a given
    SOC code in Virginia.

    Args:
        soc_code: Standard Occupational Classification code (e.g.,
                  "15-1252" for Software Developers).

    Returns:
        Formatted salary percentile data for Virginia, or an error
        message if the API call fails.
    """
    if not CAREERONESTOP_TOKEN or not CAREERONESTOP_USER_ID:
        return (
            "CareerOneStop API credentials not configured. "
            "Set CAREERONESTOP_TOKEN and CAREERONESTOP_USER_ID "
            "environment variables."
        )

    url = (
        f"https://api.careeronestop.org/v1/comparesalaries/"
        f"{CAREERONESTOP_USER_ID}/{soc_code}/wages"
        f"?location=VA&keyword={soc_code}"
    )
    headers = {
        "Authorization": f"Bearer {CAREERONESTOP_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Extract salary percentiles from the response
        if "OccupationDetail" in data and data["OccupationDetail"]:
            occ = data["OccupationDetail"][0]
            return (
                f"Virginia Salary Data for SOC {soc_code} "
                f"({occ.get('OccupationTitle', 'N/A')}):\n"
                f"  10th percentile: ${occ.get('Pct10', 'N/A')}\n"
                f"  25th percentile: ${occ.get('Pct25', 'N/A')}\n"
                f"  Median:          ${occ.get('Median', 'N/A')}\n"
                f"  75th percentile: ${occ.get('Pct75', 'N/A')}\n"
                f"  90th percentile: ${occ.get('Pct90', 'N/A')}"
            )
        return f"No salary data returned for SOC {soc_code} in Virginia."

    except requests.exceptions.RequestException as e:
        return f"CareerOneStop API error: {e}"


@tool
def web_search(query: str) -> str:
    """Search the web using Tavily for HR/compensation information.

    Useful as a fallback when structured GRIFFIN data doesn't have the
    answer. Returns top 3 results with titles, URLs, and snippets.

    Args:
        query: The search query string.

    Returns:
        Formatted top 3 search results, or an error message if the
        API is unavailable.
    """
    if not TAVILY_API_KEY:
        return (
            "Tavily API key not configured. "
            "Set TAVILY_API_KEY environment variable."
        )

    if TavilyClient is None:
        return (
            "Tavily package not installed. "
            "Run: pip install tavily-python"
        )

    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        response = tavily_client.search(query)

        results = response.get("results", [])[:3]
        if not results:
            return f"No web results found for: {query}"

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   URL: {r.get('url', 'N/A')}\n"
                f"   {r.get('content', 'No snippet')[:200]}"
            )
        return "\n\n".join(formatted)

    except Exception as e:
        return f"Tavily search error: {e}"


def demo_external_tools():
    """Demonstrate the external API tools."""

    print("\n" + "=" * 60)
    print("  Component 6: External API Tools")
    print("=" * 60)

    # CareerOneStop salary lookup for Software Developers in Virginia
    print("\n--- get_virginia_salary('15-1252') ---")
    result = get_virginia_salary.invoke({"soc_code": "15-1252"})
    pprint(result)

    # Tavily web search
    print("\n--- web_search('Virginia DHRM pay band structure 2025') ---")
    result = web_search.invoke({"query": "Virginia DHRM pay band structure 2025"})
    pprint(result)


# ============================================================
#  Component 7: Agent Memory
# ============================================================
# The InMemorySaver checkpointers are wired in Component 2. This section
# demonstrates memory RECALL — the agent is asked a follow-up question
# that requires remembering specific details from an earlier exchange.


def demo_memory_recall(classifier_agent):
    """Show that InMemorySaver lets the agent recall earlier conversation details.

    This is a two-step test:
    1. Send a classification request with specific, memorable details
       (e.g., a $500K budget).
    2. Ask a follow-up question that can ONLY be answered correctly if
       the agent remembers those details from step 1.
    """

    print("\n" + "=" * 60)
    print("  Component 7: Agent Memory (Recall Demo)")
    print("=" * 60)

    # Use a dedicated thread so this conversation is isolated
    config = {"configurable": {"thread_id": "memory-recall-demo"}}

    # Step 1: Send a request with distinctive details the agent must remember
    initial_message = HumanMessage(content=(
        "I need to classify a new position at William & Mary. "
        "It's a Senior Marine Biologist role with an annual research "
        "budget of $500,000. The position supervises 4 lab technicians "
        "and reports to the Dean of the School of Marine Science. "
        "The salary is targeted at pay band 6."
    ))

    print("\n--- Step 1: Initial classification request ---")
    print(f"  User: {initial_message.content[:120]}...")
    response1 = classifier_agent.invoke({"messages": [initial_message]}, config)
    print("\n--- Classifier response (step 1) ---")
    pprint(response1["messages"][-1].content)

    # Step 2: Ask a follow-up that requires recalling specific facts
    # The agent must remember the $500K budget, 4 technicians, and pay band 6
    # from the first message — this is ONLY possible with memory.
    recall_message = HumanMessage(content=(
        "What was the budget amount I mentioned for that position, "
        "and how many people does it supervise?"
    ))

    print("\n--- Step 2: Follow-up requiring memory recall ---")
    print(f"  User: {recall_message.content}")
    response2 = classifier_agent.invoke({"messages": [recall_message]}, config)
    print("\n--- Classifier response (recall test) ---")
    pprint(response2["messages"][-1].content)
    print("\n[INFO] If the agent correctly recalled $500,000 and 4 technicians, "
          "memory is working.")


# ============================================================
#  Component 8: Multi-Agent Orchestration
# ============================================================
# Follows the Colab Cell 45 pattern exactly: sub-agents are wrapped
# as @tool callables, then an orchestrator agent delegates to them.
# The orchestrator takes a raw position description, delegates
# classification, then delegates pay matching, and returns a combined
# recommendation.

ORCHESTRATOR_SYSTEM_PROMPT = (
    "You are an HR Classification Orchestrator for Virginia state "
    "positions. Given a position description, you coordinate two "
    "specialist agents:\n"
    "1. The Classifier agent — determines the DHRM career group and role.\n"
    "2. The Pay Matcher agent — determines the pay band and salary range.\n\n"
    "Workflow: First call the classifier to get the career group and role "
    "classification, then pass that result to the pay matcher to get "
    "compensation details. Finally, synthesize both results into a "
    "single, clear recommendation with career group, role, pay band, "
    "and salary range."
)


def demo_orchestration(llm, classifier_agent, pay_matcher_agent):
    """Demonstrate multi-agent orchestration using the Colab Cell 45 pattern.

    Creates @tool wrappers around sub-agents, builds an orchestrator agent
    that delegates to them, and runs a full classification + pay matching
    workflow on a real position from workday_training.csv.
    """

    print("\n" + "=" * 60)
    print("  Component 8: Multi-Agent Orchestration")
    print("=" * 60)

    # --- Step 1: Wrap sub-agents as @tool callables ---
    # The orchestrator sees these as tools it can call. Each tool
    # invokes the corresponding agent and returns its response text.
    @tool
    def call_classifier(position_description: str) -> str:
        """Call the classifier agent to classify a position into DHRM career groups and roles."""
        response = classifier_agent.invoke(
            {"messages": [HumanMessage(content=position_description)]},
            {"configurable": {"thread_id": "orchestrator-classify"}},
        )
        return response["messages"][-1].content

    @tool
    def call_pay_matcher(classification_info: str) -> str:
        """Call the pay matcher agent to determine pay band and salary range for a classified position."""
        response = pay_matcher_agent.invoke(
            {"messages": [HumanMessage(content=classification_info)]},
            {"configurable": {"thread_id": "orchestrator-pay"}},
        )
        return response["messages"][-1].content

    # --- Step 2: Create the orchestrator agent ---
    orchestrator_memory = InMemorySaver()
    orchestrator = create_agent(
        model=llm,
        tools=[call_classifier, call_pay_matcher],
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        checkpointer=orchestrator_memory,
    )
    print("[OK] Orchestrator agent created with classifier and pay matcher tools.")

    # --- Step 3: Run a full orchestration on a real position ---
    # Use a real position from workday_training.csv for domain relevance
    demo_position = training_df.iloc[2]["censored_text"] if len(training_df) > 2 else sample_position
    truncated = demo_position[:500] if len(demo_position) > 500 else demo_position

    orchestration_prompt = HumanMessage(content=(
        "Please classify the following position and determine the "
        "appropriate pay band and salary range. Use your tools to "
        "first classify, then match pay.\n\n"
        f"Position Description:\n{truncated}"
    ))

    config = {"configurable": {"thread_id": "orchestration-demo-1"}}

    print("\n--- Orchestrator processing position description ---")
    print(f"  Position (first 150 chars): {truncated[:150]}...")
    print("\n--- Orchestrator response ---\n")

    response = orchestrator.invoke({"messages": [orchestration_prompt]}, config)
    pprint(response["messages"][-1].content)


# ============================================================
#  MAIN — Demo Execution
# ============================================================

if __name__ == "__main__":
    import time

    # Gemini free tier allows 5 requests/minute. Components that call
    # the LLM need breathing room between them to avoid 429 errors.
    # A short pause after each LLM-heavy component keeps us under the limit.
    RATE_LIMIT_PAUSE = 30  # seconds between LLM-heavy components

    print("\n" + "#" * 60)
    print("#  GRIFFIN Multi-Agent HR Classification System")
    print("#  Components 1-8 Demo")
    print("#" * 60)

    # Component 1: Initialize the LLM and run temperature experiment
    llm = demo_llm_initialization()
    print(f"\n[PAUSE] Waiting {RATE_LIMIT_PAUSE}s for Gemini rate limit...")
    time.sleep(RATE_LIMIT_PAUSE)

    # Component 2: Create the two domain-specific agents (with tools wired in)
    classifier_agent, pay_matcher_agent = create_agents(llm)

    # Component 3: Multi-turn message handling demo
    demo_message_handling(classifier_agent)
    print(f"\n[PAUSE] Waiting {RATE_LIMIT_PAUSE}s for Gemini rate limit...")
    time.sleep(RATE_LIMIT_PAUSE)

    # Component 4: Streaming output demo
    demo_streaming(classifier_agent)
    print(f"\n[PAUSE] Waiting {RATE_LIMIT_PAUSE}s for Gemini rate limit...")
    time.sleep(RATE_LIMIT_PAUSE)

    # Component 5: Custom tools demo (search career groups, roles, pay bands)
    demo_custom_tools()

    # Component 6: External API tools demo (CareerOneStop, Tavily)
    demo_external_tools()

    # Component 7: Agent memory recall demonstration
    demo_memory_recall(classifier_agent)
    print(f"\n[PAUSE] Waiting {RATE_LIMIT_PAUSE}s for Gemini rate limit...")
    time.sleep(RATE_LIMIT_PAUSE)

    # Component 8: Multi-agent orchestration demo
    demo_orchestration(llm, classifier_agent, pay_matcher_agent)

    print("\n" + "#" * 60)
    print("#  All 8 components demonstrated successfully.")
    print("#" * 60)
