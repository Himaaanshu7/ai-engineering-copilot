"""
GitHub Agent — Phase 10

Capabilities:
  • Fetch live repo data: metadata, file tree, README, commits, key files
  • Architecture analysis from file structure
  • Code quality review from README + key files
  • CI/CD and dependency assessment
  • Improvement recommendations

Architecture: pre-fetch all repo data → inject as LLM context → single LLM call.
Falls back to pure LLM advice when no GitHub URL is found in the user's message.
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from agents.graph.state import AgentState
from llm.factory import LLMFactory
from tools.github_tools import build_repo_context, parse_repo_url

_SYSTEM_PROMPT = """You are a Staff Engineer and open-source contributor with 10+ years of experience \
reviewing codebases at companies like Google, Netflix, and Databricks.

You have been given live data fetched directly from a GitHub repository. \
Analyze it thoroughly and produce a structured architectural review.

{context_block}

Your review must cover:

## 1. Project Summary
What the project does, its purpose, and target users. (2-3 sentences)

## 2. Architecture Analysis
- Overall architecture pattern (MVC, layered, microservices, monolith, etc.)
- Key components and how they interact
- Module/package organization quality
- Separation of concerns

## 3. Tech Stack Assessment
- Languages and frameworks used
- Notable dependencies — are they well-chosen?
- Any outdated or risky dependencies?

## 4. Code Quality Signals
- README quality and documentation completeness
- Project structure clarity
- CI/CD setup (GitHub Actions, testing pipelines)
- Test coverage signals (test directories, test files)

## 5. Strengths
What this project does well (be specific, cite actual files/patterns you see)

## 6. Issues & Improvements
Prioritized list of concrete improvements:
  - Critical (security, correctness)
  - High (performance, maintainability)
  - Medium (quality, documentation)
  - Low (nice-to-haves)

## 7. Overall Score
Rate the project: Architecture /10, Code Quality /10, Documentation /10, CI/CD /10
Give one-line verdict.

Be specific — cite actual filenames, patterns, and code you see in the data. \
Never give generic advice that could apply to any project."""


async def github_agent_node(state: AgentState) -> dict:
    user_input = state["user_input"]
    logger.info(f"[GitHub Agent] Processing | input={user_input[:60]}...")

    # Try to extract a GitHub repo URL from the message
    parsed = parse_repo_url(user_input)

    if parsed:
        owner, repo = parsed
        logger.info(f"[GitHub Agent] Repo detected | {owner}/{repo}")

        context_str, sources = build_repo_context(owner, repo)

        if context_str.startswith("Repository"):
            # Not found / private
            context_block = f"**Note:** {context_str}\n\nAnswer based on any details the user provided."
        else:
            context_block = (
                "**The following data was fetched live from the GitHub API. "
                "Base your entire review on this real data — do not make things up.**\n\n"
                + context_str
            )
    else:
        # No URL found — fall back to reviewing pasted code/description
        logger.info("[GitHub Agent] No repo URL — reviewing pasted content")
        sources = []
        context_block = (
            "**No GitHub URL was detected in the user's message.** "
            "Review any code or architecture description they have provided directly. "
            "If they haven't provided code, ask for a GitHub URL or code to review."
        )

    system_prompt = _SYSTEM_PROMPT.format(context_block=context_block)
    llm = LLMFactory.get_llm(temperature=0.05)

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input),
    ])

    logger.info(f"[GitHub Agent] Review complete | sources={sources}")
    return {
        "github_result": response.content,
        "final_response": response.content,
        "sources": sources,
    }
