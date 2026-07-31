"""
Phase 3 unit tests — frontend utilities.

Tests target pure-Python helpers only (no Streamlit runtime required).
APIClient tests mock httpx to avoid needing a live server.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from frontend.utils.export import messages_to_markdown
from frontend.utils.formatters import build_file_context


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_file(name: str, content: bytes) -> MagicMock:
    f = MagicMock()
    f.name = name
    f.read.return_value = content
    f.seek = MagicMock()
    return f


# ── Export tests ───────────────────────────────────────────────────────────────


class TestMessagesToMarkdown:
    def test_empty_session(self):
        result = messages_to_markdown([], "test-session-abc")
        assert "AI Engineering Copilot" in result
        assert "test-session-abc" in result
        assert "0" in result  # 0 exchanges

    def test_user_and_assistant_messages(self):
        messages = [
            {"role": "user", "content": "Optimize this SQL"},
            {
                "role": "assistant",
                "content": "Here is the optimized query…",
                "intent": "sql",
                "sources": [],
            },
        ]
        result = messages_to_markdown(messages, "abc-123")
        assert "You" in result
        assert "Copilot" in result
        assert "Optimize this SQL" in result
        assert "sql" in result

    def test_sources_included(self):
        messages = [
            {"role": "user", "content": "Explain RAG"},
            {
                "role": "assistant",
                "content": "RAG stands for…",
                "intent": "research",
                "sources": ["https://docs.langchain.com/rag"],
            },
        ]
        result = messages_to_markdown(messages, "sid")
        assert "https://docs.langchain.com/rag" in result

    def test_file_name_in_user_label(self):
        messages = [
            {"role": "user", "content": "Review my code", "file_name": "script.py"},
            {"role": "assistant", "content": "Looks good", "intent": "python", "sources": []},
        ]
        result = messages_to_markdown(messages, "sid")
        assert "script.py" in result

    def test_error_intent_not_labeled(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Backend error", "intent": "error", "sources": []},
        ]
        result = messages_to_markdown(messages, "sid")
        # error intent should not appear as an intent tag
        assert "· `error`" not in result

    def test_output_is_valid_markdown(self):
        """Rudimentary check: output starts with H1 and contains at least one ---."""
        result = messages_to_markdown([], "session-x")
        assert result.startswith("# AI Engineering Copilot")
        assert "---" in result


# ── Formatter tests ────────────────────────────────────────────────────────────


class TestBuildFileContext:
    def test_python_file(self):
        f = _mock_file("main.py", b"def hello():\n    print('hello')")
        context, fname = build_file_context(f)
        assert fname == "main.py"
        assert "```python" in context
        assert "hello" in context

    def test_sql_file(self):
        f = _mock_file("query.sql", b"SELECT id, name FROM users WHERE active = 1")
        context, fname = build_file_context(f)
        assert fname == "query.sql"
        assert "```sql" in context
        assert "SELECT" in context

    def test_json_file(self):
        f = _mock_file("config.json", b'{"key": "value"}')
        context, fname = build_file_context(f)
        assert "```json" in context

    def test_yaml_file(self):
        f = _mock_file("pipeline.yaml", b"name: my_pipeline\nsteps:\n  - load")
        context, fname = build_file_context(f)
        assert "```yaml" in context

    def test_markdown_file(self):
        f = _mock_file("README.md", b"# My Project\n\nThis is a test.")
        context, fname = build_file_context(f)
        assert "```markdown" in context

    def test_long_file_is_truncated(self):
        long_content = b"x" * 10_000
        f = _mock_file("big.py", long_content)
        context, _ = build_file_context(f)
        assert "truncated" in context.lower()
        assert "8,000" in context or "8000" in context

    def test_pdf_returns_phase8_note(self):
        f = _mock_file("report.pdf", b"%PDF-1.4 binary content")
        context, fname = build_file_context(f)
        assert fname == "report.pdf"
        assert "Phase 8" in context

    def test_unsupported_extension(self):
        f = _mock_file("photo.png", b"\x89PNG\r\n")
        context, fname = build_file_context(f)
        assert fname == "photo.png"
        assert "unsupported" in context.lower()

    def test_no_extension(self):
        f = _mock_file("Makefile", b"all:\n\techo hello")
        context, fname = build_file_context(f)
        assert fname == "Makefile"
        assert "unsupported" in context.lower()

    def test_csv_file(self):
        csv_content = b"id,name,age\n1,Alice,30\n2,Bob,25\n3,Carol,35"
        f = _mock_file("users.csv", csv_content)

        import io
        real_file = MagicMock()
        real_file.name = "users.csv"
        real_file.read.return_value = csv_content
        real_file.seek = MagicMock()

        # pandas.read_csv works with a BytesIO object; patch the call
        with patch("pandas.read_csv") as mock_csv:
            import pandas as pd

            mock_csv.return_value = pd.DataFrame(
                {"id": [1, 2, 3], "name": ["Alice", "Bob", "Carol"], "age": [30, 25, 35]}
            )
            context, fname = build_file_context(real_file)

        assert fname == "users.csv"
        assert "3" in context  # row count
        assert "columns" in context.lower()


# ── APIClient tests ────────────────────────────────────────────────────────────


class TestAPIClient:
    """Tests that mock the HTTP transport — no live server needed."""

    def _make_client(self):
        from frontend.utils.api_client import APIClient
        return APIClient("http://localhost:8000")

    def _mock_httpx(self, mock_cls, status_code=200, json_body=None, exception=None):
        mock_response = MagicMock()
        mock_response.json.return_value = json_body or {}
        mock_response.status_code = status_code
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        if exception:
            mock_client.get.side_effect = exception
            mock_client.post.side_effect = exception
        else:
            mock_client.get.return_value = mock_response
            mock_client.post.return_value = mock_response

        mock_cls.return_value = mock_client
        return mock_response

    def test_health_check_success(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            self._mock_httpx(mock_cls, json_body={"status": "ok", "llm_provider": "groq"})
            result = client.health_check()
        assert result["status"] == "ok"
        assert result["llm_provider"] == "groq"

    def test_health_check_connection_error(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            self._mock_httpx(mock_cls, exception=Exception("Connection refused"))
            result = client.health_check()
        assert result["status"] == "error"
        assert "Connection refused" in result["detail"]

    def test_send_message_success(self):
        client = self._make_client()
        payload = {
            "response": "Use an index on status.",
            "intent": "sql",
            "agent_used": "sql_agent",
            "sources": [],
        }
        with patch("httpx.Client") as mock_cls:
            self._mock_httpx(mock_cls, json_body=payload)
            result = client.send_message("Optimize my query", "sess-123")
        assert result["intent"] == "sql"
        assert "index" in result["response"]

    def test_send_message_timeout(self):
        client = self._make_client()
        with patch("httpx.Client") as mock_cls:
            self._mock_httpx(mock_cls, exception=httpx.TimeoutException("timeout"))
            result = client.send_message("test", "sess-123")
        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_send_message_http_error(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        exc = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
        with patch("httpx.Client") as mock_cls:
            self._mock_httpx(mock_cls, exception=exc)
            result = client.send_message("test", "sess-123")
        assert "error" in result
        assert "500" in result["error"]

    def test_upload_file_endpoint_not_found(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.status_code = 404
        exc = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
        with patch("httpx.Client") as mock_cls:
            self._mock_httpx(mock_cls, exception=exc)
            result = client.upload_file(b"content", "script.py", "sess-123")
        assert "error" in result
        assert "Phase 4" in result["error"]

    def test_get_history_not_found(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.status_code = 404
        exc = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
        with patch("httpx.Client") as mock_cls:
            self._mock_httpx(mock_cls, exception=exc)
            result = client.get_history("sess-123")
        assert "messages" in result
        assert result["messages"] == []
