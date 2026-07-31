"""Shared fixtures for all test suites."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture
def sample_messages() -> list[dict]:
    return [
        {"role": "user", "content": "Explain LangGraph", "file_name": None},
        {
            "role": "assistant",
            "content": "LangGraph is a library for building stateful multi-agent applications.",
            "intent": "research",
            "agent_used": "research_agent",
            "sources": ["data/docs/langgraph.md"],
        },
        {"role": "user", "content": "Write a SQL query for top 5 customers", "file_name": None},
        {
            "role": "assistant",
            "content": "SELECT customer_id, SUM(revenue) AS total FROM orders GROUP BY customer_id ORDER BY total DESC LIMIT 5;",
            "intent": "sql",
            "agent_used": "sql_agent",
            "sources": [],
        },
    ]


@pytest.fixture
def clean_sql() -> str:
    return "SELECT customer_id, SUM(amount) AS total FROM orders WHERE status = 'paid' GROUP BY customer_id ORDER BY total DESC LIMIT 10"


@pytest.fixture
def bad_sql() -> str:
    return "SELECT * FROM orders"


@pytest.fixture
def simple_python() -> str:
    return """
def add(a: int, b: int) -> int:
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
"""


@pytest.fixture
def problematic_python() -> str:
    return """
def append_item(item, items=[]):
    items.append(item)
    return items

def risky():
    try:
        result = eval("1+1")
    except:
        pass
"""
