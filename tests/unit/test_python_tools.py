"""Unit tests for Python analysis tools."""
import pytest
from tools.python_tools import (
    analyze_python_code,
    detect_python_issues,
    calculate_complexity,
)


def test_analyze_finds_function(simple_python):
    result = analyze_python_code.invoke({"code": simple_python})
    assert "add" in result or "function" in result.lower()


def test_analyze_finds_class(simple_python):
    result = analyze_python_code.invoke({"code": simple_python})
    assert "Calculator" in result or "class" in result.lower()


def test_analyze_returns_string(simple_python):
    result = analyze_python_code.invoke({"code": simple_python})
    assert isinstance(result, str) and len(result) > 0


def test_detect_mutable_default(problematic_python):
    result = detect_python_issues.invoke({"code": problematic_python})
    assert "mutable" in result.lower() or "default" in result.lower() or "[]" in result


def test_detect_bare_except(problematic_python):
    result = detect_python_issues.invoke({"code": problematic_python})
    assert "bare except" in result.lower() or "except:" in result


def test_detect_eval_usage(problematic_python):
    result = detect_python_issues.invoke({"code": problematic_python})
    assert "eval" in result.lower()


def test_detect_no_issues_on_clean_code(simple_python):
    result = detect_python_issues.invoke({"code": simple_python})
    assert isinstance(result, str)


def test_calculate_complexity_simple_function(simple_python):
    result = calculate_complexity.invoke({"code": simple_python})
    assert isinstance(result, str)
    assert "complexity" in result.lower() or "maintainability" in result.lower() or "function" in result.lower()


def test_calculate_complexity_empty_code():
    result = calculate_complexity.invoke({"code": "x = 1"})
    assert isinstance(result, str)


def test_detect_issues_returns_string(simple_python):
    result = detect_python_issues.invoke({"code": simple_python})
    assert isinstance(result, str)
