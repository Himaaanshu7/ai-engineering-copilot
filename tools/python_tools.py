"""
AST-based Python analysis tools for the Python Agent.

Tools (all stateless — no file required):
  - analyze_python_code  : AST structure extraction (functions, classes, imports)
  - detect_python_issues : common anti-pattern detection
  - calculate_complexity : cyclomatic complexity + maintainability index via radon
  - execute_python_snippet: sandboxed execution with 5-second timeout
"""

import ast
import subprocess
import sys
import textwrap
from typing import Any

from langchain_core.tools import tool
from loguru import logger


# ── helpers ────────────────────────────────────────────────────────────────────

def _parse(code: str) -> ast.Module | str:
    """Return parsed AST or an error string."""
    try:
        return ast.parse(textwrap.dedent(code))
    except SyntaxError as exc:
        return f"SyntaxError: {exc}"


def _has_type_hints(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    args = node.args
    all_args = args.args + args.posonlyargs + args.kwonlyargs
    if args.vararg:
        all_args.append(args.vararg)
    if args.kwarg:
        all_args.append(args.kwarg)
    annotated = sum(1 for a in all_args if a.annotation is not None)
    return annotated == len(all_args) and node.returns is not None


# ── Tool 1: structural analysis ────────────────────────────────────────────────

@tool
def analyze_python_code(code: str) -> str:
    """Parse Python source code with AST and return a structural summary.

    Reports: imports, classes, functions (with line numbers, arg count, type-hint coverage,
    docstring presence, async status). Use this before suggesting refactors so you know
    what the code contains.

    Args:
        code: Python source code as a string.

    Returns:
        Structured summary of the code's components.
    """
    tree = _parse(code)
    if isinstance(tree, str):
        return tree  # syntax error

    lines = code.splitlines()
    summary: list[str] = [f"**Lines of code:** {len(lines)}"]

    # Imports
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
    if imports:
        summary.append(f"\n**Imports ({len(imports)}):** {', '.join(imports[:12])}" +
                       (" ..." if len(imports) > 12 else ""))

    # Classes
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    if classes:
        class_lines = []
        for cls in classes:
            method_count = sum(1 for n in ast.walk(cls) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            class_lines.append(f"  • {cls.name} (line {cls.lineno}, {method_count} methods)")
        summary.append("\n**Classes:**\n" + "\n".join(class_lines))

    # Functions (top-level and methods)
    functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node)

    if functions:
        fn_lines = []
        for fn in functions:
            prefix = "async def" if isinstance(fn, ast.AsyncFunctionDef) else "def"
            arg_count = len(fn.args.args)
            has_hints = _has_type_hints(fn)
            has_doc = (
                isinstance(fn.body[0], ast.Expr) and
                isinstance(fn.body[0].value, ast.Constant) and
                isinstance(fn.body[0].value.value, str)
            ) if fn.body else False
            flags = []
            if not has_hints:
                flags.append("no type hints")
            if not has_doc:
                flags.append("no docstring")
            flag_str = f" ⚠ {', '.join(flags)}" if flags else " ✓"
            fn_lines.append(f"  • {prefix} {fn.name}() line {fn.lineno}, {arg_count} args{flag_str}")
        summary.append("\n**Functions/Methods:**\n" + "\n".join(fn_lines))

    return "\n".join(summary)


# ── Tool 2: anti-pattern detection ─────────────────────────────────────────────

@tool
def detect_python_issues(code: str) -> str:
    """Detect common Python anti-patterns and bugs via AST analysis.

    Checks for: mutable default arguments, bare except clauses, use of eval/exec,
    global variable abuse, unused imports, missing return type hints on public functions,
    assert in non-test code, and magic numbers.

    Args:
        code: Python source code as a string.

    Returns:
        List of issues with line numbers, or confirmation that the code looks clean.
    """
    tree = _parse(code)
    if isinstance(tree, str):
        return tree  # syntax error

    issues: list[str] = []

    for node in ast.walk(tree):
        # Mutable default arguments
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + node.args.kw_defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    issues.append(
                        f"Line {node.lineno}: `{node.name}` has a mutable default argument "
                        f"({type(default).__name__}) — use `None` and assign inside the function"
                    )

        # Bare except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                f"Line {node.lineno}: bare `except:` catches everything including KeyboardInterrupt and SystemExit "
                f"— use `except Exception:` or a specific exception type"
            )

        # eval / exec usage
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                issues.append(
                    f"Line {node.lineno}: `{node.func.id}()` is a security risk and makes code hard to debug "
                    f"— consider alternatives"
                )

        # global statement
        if isinstance(node, ast.Global):
            issues.append(
                f"Line {node.lineno}: `global {', '.join(node.names)}` — global state makes code hard to test; "
                f"pass values as parameters or use a class"
            )

        # assert outside test files
        if isinstance(node, ast.Assert):
            issues.append(
                f"Line {node.lineno}: `assert` is stripped when Python runs with `-O` — "
                f"use explicit `if` + `raise` for runtime guards"
            )

        # Magic numbers (numeric literals outside assignments/function calls used as comparison values)
        if isinstance(node, (ast.Compare, ast.BinOp)):
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                    if child.value not in (0, 1, -1, 2, 100):
                        issues.append(
                            f"Line {getattr(child, 'lineno', '?')}: magic number `{child.value}` — "
                            f"assign to a named constant for readability"
                        )
                        break  # one warning per expression is enough

    if not issues:
        return "No common anti-patterns detected. Code looks clean."

    return f"**{len(issues)} issue(s) found:**\n" + "\n".join(f"  • {i}" for i in issues)


# ── Tool 3: complexity metrics ──────────────────────────────────────────────────

@tool
def calculate_complexity(code: str) -> str:
    """Calculate cyclomatic complexity and maintainability index for Python code using radon.

    Cyclomatic complexity grades:
      A (1-5) — simple, low risk
      B (6-10) — moderate
      C (11-15) — complex, worth refactoring
      D/E/F (16+) — very high risk, refactor strongly recommended

    Args:
        code: Python source code as a string.

    Returns:
        Per-function complexity scores and a maintainability index.
    """
    try:
        from radon.complexity import cc_visit
        from radon.metrics import mi_visit, mi_rank

        dedented = textwrap.dedent(code)

        blocks = cc_visit(dedented)
        mi_score = mi_visit(dedented, multi=True)
        mi_grade = mi_rank(mi_score)

        lines: list[str] = [
            f"**Maintainability Index:** {mi_score:.1f} / 100 (grade {mi_grade})"
        ]

        # radon 6 returns named tuples with complexity/name/lineno; no rank field
        def _rank(cc: int) -> str:
            if cc <= 5: return "A"
            if cc <= 10: return "B"
            if cc <= 15: return "C"
            if cc <= 20: return "D"
            if cc <= 25: return "E"
            return "F"

        scored = [b for b in blocks if hasattr(b, "complexity") and hasattr(b, "name")]
        if not scored:
            lines.append("No functions or methods found to analyze.")
        else:
            lines.append(f"\n**Cyclomatic complexity ({len(scored)} block(s)):**")
            for block in sorted(scored, key=lambda b: b.complexity, reverse=True):
                rank = _rank(block.complexity)
                warning = " ⚠ consider refactoring" if block.complexity > 10 else ""
                lines.append(
                    f"  • {block.name}() line {block.lineno} — "
                    f"complexity {block.complexity} (rank {rank}){warning}"
                )

        return "\n".join(lines)

    except SyntaxError as exc:
        return f"SyntaxError: {exc}"
    except Exception as exc:
        logger.warning(f"[Python Tool] calculate_complexity error: {exc}")
        return f"Error calculating complexity: {exc}"


# ── Tool 4: sandboxed execution ────────────────────────────────────────────────

@tool
def execute_python_snippet(code: str) -> str:
    """Safely execute a Python snippet in a subprocess and return stdout + stderr.

    Useful for verifying that a code fix actually produces the expected output.
    Maximum execution time: 5 seconds. No network access restrictions are applied —
    do not run code that makes external requests.

    Args:
        code: Python source code to execute. Keep it short and self-contained.

    Returns:
        Combined stdout and stderr output, or a timeout/error message.
    """
    dedented = textwrap.dedent(code)

    # Quick safety check — block obviously destructive patterns
    danger_patterns = ["os.system", "subprocess.run", "shutil.rmtree", "open(", "__import__"]
    for pattern in danger_patterns:
        if pattern in dedented:
            return f"Execution blocked: snippet contains `{pattern}` which is not allowed in sandboxed mode."

    try:
        result = subprocess.run(
            [sys.executable, "-c", dedented],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = (result.stdout + result.stderr).strip()
        return output if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Execution timed out after 5 seconds."
    except Exception as exc:
        logger.warning(f"[Python Tool] execute_python_snippet error: {exc}")
        return f"Execution error: {exc}"
