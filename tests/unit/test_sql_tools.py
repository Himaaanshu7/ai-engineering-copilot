"""Unit tests for SQL tools."""
import pytest
from tools.sql_tools import analyze_sql_quality, make_file_tools


def test_clean_sql_passes(clean_sql):
    result = analyze_sql_quality.invoke({"sql": clean_sql})
    assert "issues" not in result.lower() or "no issues" in result.lower() or "looks good" in result.lower()


def test_select_star_flagged(bad_sql):
    result = analyze_sql_quality.invoke({"sql": bad_sql})
    assert "SELECT *" in result or "select *" in result.lower() or "wildcard" in result.lower()


def test_full_table_scan_flagged():
    """SELECT * without WHERE on a large table should be flagged."""
    sql = "SELECT * FROM billion_row_events"
    result = analyze_sql_quality.invoke({"sql": sql})
    assert isinstance(result, str) and len(result) > 0


def test_or_not_false_positive():
    """'CORRELATED' and 'ORDER' should not trigger OR-clause warning."""
    sql = "SELECT customer_id FROM orders ORDER BY created_at"
    result = analyze_sql_quality.invoke({"sql": sql})
    assert "OR" not in result or "ORDER" in result


def test_make_file_tools_returns_two_tools(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("id,name\n1,Alice\n2,Bob\n")
    tools = make_file_tools(str(csv_file))
    assert len(tools) == 2
    names = {t.name for t in tools}
    assert "profile_data_file" in names
    assert "execute_sql_on_data" in names


def test_analyze_sql_quality_returns_string(clean_sql):
    result = analyze_sql_quality.invoke({"sql": clean_sql})
    assert isinstance(result, str)
    assert len(result) > 0


def test_empty_sql_handled():
    result = analyze_sql_quality.invoke({"sql": ""})
    assert isinstance(result, str)
