"""
Quick standalone runner for Component 8 (Orchestration) only.
Assumes Components 1-7 have already been verified.
"""
import time

# Import everything from the main script — this loads data and defines tools
from griffin_langchain_agents import (
    init_chat_model, create_agents, demo_orchestration
)

print("Initializing LLM...")
llm = init_chat_model(model="google_genai:gemini-2.5-flash")

print("Creating agents (with tools)...")
classifier_agent, pay_matcher_agent = create_agents(llm)

print(f"\nWaiting 30s before orchestration to stay under rate limit...")
time.sleep(30)

print("\nRunning Component 8: Multi-Agent Orchestration...")
demo_orchestration(llm, classifier_agent, pay_matcher_agent)

print("\nDone!")
