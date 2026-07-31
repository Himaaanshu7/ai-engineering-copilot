from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from agents.graph.state import AgentState
from llm.factory import LLMFactory

_VALID_INTENTS = {"sql", "python", "research", "github", "data_analysis", "interview", "general"}

_PLANNER_PROMPT = """You are the routing brain of an AI Engineering Copilot.

Your ONLY job: classify the user's request into exactly one category.

Categories:
- sql          : SQL queries, optimization, indexes, execution plans, anti-patterns, DBA tasks
- python       : Python code, debugging, refactoring, algorithms, complexity, data structures
- research     : Tech explanations, comparisons, architecture concepts, best practices, tutorials (e.g. "what is LangGraph", "how does Spark work")
- github       : Repository analysis, code review, architecture review, README analysis
- data_analysis: CSV, Parquet, Excel, data profiling, statistical exploration, uploaded file analysis
- interview    : Interview questions, system design, career guidance, behavioral questions, coding challenges
- general      : Greetings, off-topic, meta questions, unclear or mixed intent

Rules:
1. Output ONLY the category name — nothing else, no punctuation.
2. When in doubt between research and another category, prefer the more specific one.
3. If the message contains code to review → python or sql (not research).

Examples:
"Optimize this slow JOIN query" → sql
"Why is my list comprehension slow?" → python
"What is LangGraph and when should I use it?" → research
"Explain the difference between Spark RDD and DataFrame" → research
"Review my GitHub repo architecture" → github
"What are the top rows of my uploaded CSV?" → data_analysis
"How do I answer Amazon leadership principle questions?" → interview
"Hi" → general"""


async def planner_node(state: AgentState) -> dict:
    logger.info(f"[Planner] Classifying | input={state['user_input'][:60]}...")

    llm = LLMFactory.get_llm(temperature=0.0)

    response = await llm.ainvoke([
        SystemMessage(content=_PLANNER_PROMPT),
        HumanMessage(content=state["user_input"]),
    ])

    raw = response.content.strip().lower().split()[0] if response.content.strip() else "general"
    intent = raw if raw in _VALID_INTENTS else "general"

    logger.info(f"[Planner] Classified | intent={intent} | raw={raw!r}")

    return {
        "intent": intent,
        "active_agents": [f"{intent}_agent"],
        "messages": [HumanMessage(content=state["user_input"])],
    }
