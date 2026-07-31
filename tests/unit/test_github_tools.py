"""Unit tests for GitHub URL parsing and tool utilities."""
import pytest
from tools.github_tools import parse_repo_url


def test_parse_full_github_url():
    owner, repo = parse_repo_url("https://github.com/Himaaanshu7/ai-engineering-copilot")
    assert owner == "Himaaanshu7"
    assert repo == "ai-engineering-copilot"


def test_parse_owner_slash_repo():
    owner, repo = parse_repo_url("Himaaanshu7/ai-engineering-copilot")
    assert owner == "Himaaanshu7"
    assert repo == "ai-engineering-copilot"


def test_parse_url_with_subdirectory():
    owner, repo = parse_repo_url("https://github.com/langchain-ai/langgraph/tree/main/examples")
    assert owner == "langchain-ai"
    assert repo == "langgraph"


def test_parse_url_with_trailing_slash():
    owner, repo = parse_repo_url("https://github.com/Himaaanshu7/ai-engineering-copilot/")
    assert owner == "Himaaanshu7"
    assert repo == "ai-engineering-copilot"


def test_parse_embedded_in_sentence():
    owner, repo = parse_repo_url("Please analyze this repo: https://github.com/openai/openai-python for me")
    assert owner == "openai"
    assert repo == "openai-python"


def test_parse_no_match_returns_none():
    result = parse_repo_url("Can you explain LangGraph to me?")
    assert result is None


def test_parse_plain_text_no_slash():
    result = parse_repo_url("just some text with no repo")
    assert result is None
