"""Unit tests for report generation tools."""
import pytest
from tools.report_tools import messages_to_pdf, build_report_prompt, _strip_markdown, _to_latin1


def test_pdf_returns_bytes(sample_messages):
    result = messages_to_pdf(sample_messages, "test-session-abc123")
    assert isinstance(result, bytes)
    assert len(result) > 100


def test_pdf_starts_with_pdf_header(sample_messages):
    result = messages_to_pdf(sample_messages, "test-session-abc123")
    assert result[:4] == b"%PDF"


def test_pdf_handles_unicode(sample_messages):
    msgs = sample_messages + [{
        "role": "user",
        "content": "Em-dash — en-dash – curly quotes ‘hi’ and ellipsis…",
        "file_name": None,
    }]
    result = messages_to_pdf(msgs, "unicode-test")
    assert isinstance(result, bytes) and len(result) > 100


def test_pdf_empty_messages():
    result = messages_to_pdf([], "empty-session")
    assert isinstance(result, bytes)


def test_build_report_prompt_summary(sample_messages):
    prompt = build_report_prompt(sample_messages, "summary")
    assert "Summary" in prompt or "summary" in prompt.lower()
    assert "Overview" in prompt
    assert "Action Items" in prompt


def test_build_report_prompt_technical(sample_messages):
    prompt = build_report_prompt(sample_messages, "technical")
    assert "Technical" in prompt
    assert "Architecture" in prompt or "architecture" in prompt.lower()
    assert "Code Solutions" in prompt


def test_build_report_prompt_interview(sample_messages):
    prompt = build_report_prompt(sample_messages, "interview")
    assert "Interview" in prompt or "interview" in prompt.lower()
    assert "Questions" in prompt or "questions" in prompt.lower()


def test_build_report_includes_transcript(sample_messages):
    prompt = build_report_prompt(sample_messages, "summary")
    assert "LangGraph" in prompt or "SQL" in prompt


def test_strip_markdown_removes_headings():
    assert _strip_markdown("# Hello World") == "Hello World"
    assert _strip_markdown("## Section") == "Section"


def test_strip_markdown_removes_bold():
    assert _strip_markdown("**bold text**") == "bold text"


def test_strip_markdown_removes_code_blocks():
    result = _strip_markdown("```python\nprint('hi')\n```")
    assert "```" not in result


def test_to_latin1_replaces_emdash():
    result = _to_latin1("Hello — World")
    assert "—" not in result
    assert "-" in result


def test_to_latin1_replaces_curly_quotes():
    result = _to_latin1("‘hello’")
    assert "‘" not in result and "’" not in result
