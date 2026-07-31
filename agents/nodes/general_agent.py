from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from agents.graph.state import AgentState
from llm.factory import LLMFactory

_GENERAL_PROMPT = """You are the AI Engineering Copilot — a friendly, expert AI assistant for \
data engineers, software engineers, and AI practitioners.

You help with:
- SQL, Python, Data Engineering, Spark, dbt, Airflow
- AI Engineering: LangChain, LangGraph, RAG, LLMs, vector databases
- System design, architecture, and best practices
- Technical interview preparation
- Code review and debugging
- Career guidance in data and AI

For greetings or general questions:
- Respond warmly and briefly
- Mention 2-3 specific things you can help with that are relevant to their message
- Invite them to ask a specific question

For unclear or mixed-intent questions:
- Answer the clearest part of the question
- Ask a focused clarifying question to provide more specific help

Keep responses concise for general conversation. Save the depth for technical questions."""


async def general_agent_node(state: AgentState) -> dict:
    logger.info(f"[General Agent] Processing | input={state['user_input'][:60]}...")

    llm = LLMFactory.get_llm(temperature=0.2)

    response = await llm.ainvoke([
        SystemMessage(content=_GENERAL_PROMPT),
        HumanMessage(content=state["user_input"]),
    ])

    logger.info("[General Agent] Response generated")
    return {"final_response": response.content}
