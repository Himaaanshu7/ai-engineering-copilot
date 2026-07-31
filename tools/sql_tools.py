"""
DuckDB-powered SQL tools for the SQL Agent.

Always available:
  - analyze_sql_quality: static anti-pattern detection

Available when a file is uploaded (via make_file_tools):
  - profile_data_file: schema, row count, column stats
  - execute_sql_on_data: run arbitrary SQL against the uploaded file
"""

from pathlib import Path

import duckdb
from langchain_core.tools import tool
from loguru import logger


# ── Static analysis (no file required) ────────────────────────────────────────

@tool
def analyze_sql_quality(sql: str) -> str:
    """Analyze a SQL query for anti-patterns, inefficiencies, and improvement opportunities.

    Args:
        sql: The SQL query to analyze.

    Returns:
        A structured list of issues and suggestions.
    """
    sql_upper = sql.upper()
    issues: list[str] = []
    suggestions: list[str] = []

    if "SELECT *" in sql_upper:
        issues.append("SELECT * fetches every column — name only the columns you need to reduce I/O and network transfer")

    if "NOT IN" in sql_upper:
        issues.append("NOT IN fails silently with NULL values and often skips indexes — use NOT EXISTS or LEFT JOIN ... IS NULL instead")

    if "LIKE '%" in sql_upper:
        issues.append("Leading-wildcard LIKE ('%value') prevents B-tree index usage — consider a full-text index or ILIKE for case-insensitive search")

    nested_selects = sql_upper.count("SELECT") - 1
    if nested_selects >= 2 and "WITH" not in sql_upper:
        issues.append(f"Found {nested_selects} nested subqueries without CTEs — refactor to WITH clauses for readability and optimizer hints")

    if sql_upper.count("SELECT") > 1 and sql_upper.count("JOIN") == 0 and "EXISTS" not in sql_upper:
        suggestions.append("Correlated subquery detected — may execute once per row; a JOIN is usually faster")

    if "DISTINCT" in sql_upper:
        suggestions.append("DISTINCT is often a symptom of an accidental cross join — verify your JOIN conditions are correct")

    if "ORDER BY" in sql_upper and "LIMIT" not in sql_upper:
        suggestions.append("ORDER BY without LIMIT sorts the entire result — add LIMIT if you only need top-N rows")

    # Match " OR " with spaces to avoid matching "ORDER", "CORRELATED", etc.
    if " OR " in sql_upper and "WHERE" in sql_upper:
        suggestions.append("OR in WHERE clause may force a full table scan — consider rewriting as UNION ALL of two indexed queries")

    if not issues and not suggestions:
        return "No obvious anti-patterns detected. Query looks structurally sound."

    parts: list[str] = []
    if issues:
        parts.append("**Issues (should fix):**\n" + "\n".join(f"  • {i}" for i in issues))
    if suggestions:
        parts.append("**Suggestions (consider):**\n" + "\n".join(f"  • {s}" for s in suggestions))
    return "\n\n".join(parts)


# ── File-aware tool factory ────────────────────────────────────────────────────

def _load_file_into_duckdb(conn: duckdb.DuckDBPyConnection, file_path: str) -> None:
    """Register the uploaded file as a DuckDB view named 'data'."""
    path = Path(file_path)
    ext = path.suffix.lower()
    escaped = file_path.replace("\\", "/")

    if ext == ".csv":
        conn.execute(f"CREATE OR REPLACE VIEW data AS SELECT * FROM read_csv_auto('{escaped}')")
    elif ext in (".parquet", ".pq"):
        conn.execute(f"CREATE OR REPLACE VIEW data AS SELECT * FROM read_parquet('{escaped}')")
    elif ext in (".xlsx", ".xls"):
        # DuckDB can read Excel via the spatial or excel extension
        conn.execute("INSTALL excel; LOAD excel;")
        conn.execute(f"CREATE OR REPLACE VIEW data AS SELECT * FROM read_xlsx('{escaped}')")
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: .csv, .parquet, .xlsx")


def make_file_tools(file_path: str) -> list:
    """
    Return file-specific DuckDB tools closed over the given file path.
    Call this only when an uploaded file exists.
    """

    @tool
    def profile_data_file() -> str:
        """Get the schema, row count, column types, and a 5-row sample from the uploaded data file.
        Use this before writing queries so you know the column names and data types.

        Returns:
            Schema description, row count, and sample rows.
        """
        try:
            conn = duckdb.connect()
            _load_file_into_duckdb(conn, file_path)

            schema_df = conn.execute("DESCRIBE data").df()
            row_count = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]
            sample_df = conn.execute("SELECT * FROM data LIMIT 5").df()
            null_pct = conn.execute(
                "SELECT " + ", ".join(
                    f"ROUND(100.0 * COUNT(*) FILTER (WHERE {col} IS NULL) / COUNT(*), 1) AS {col}_null_pct"
                    for col in schema_df["column_name"]
                ) + " FROM data"
            ).df().to_string(index=False)

            return (
                f"**Schema ({row_count:,} rows):**\n{schema_df.to_string(index=False)}\n\n"
                f"**Null % per column:**\n{null_pct}\n\n"
                f"**Sample (5 rows):**\n{sample_df.to_string(index=False)}"
            )
        except Exception as exc:
            logger.warning(f"[SQL Tool] profile_data_file failed: {exc}")
            return f"Error reading file: {exc}"

    @tool
    def execute_sql_on_data(sql: str) -> str:
        """Execute a SQL query against the uploaded data file using DuckDB.
        The table is always named 'data'. Always call profile_data_file first to confirm column names.

        Args:
            sql: Valid DuckDB SQL. Table name must be 'data'. Example: SELECT * FROM data LIMIT 10

        Returns:
            Query results as a formatted table (capped at 100 rows).
        """
        try:
            conn = duckdb.connect()
            _load_file_into_duckdb(conn, file_path)

            result_df = conn.execute(sql).df()
            if result_df.empty:
                return "Query returned 0 rows."

            truncated = len(result_df) > 100
            display = result_df.head(100)
            out = display.to_string(index=False)
            if truncated:
                out += f"\n\n_(Showing 100 of {len(result_df):,} rows)_"
            return out
        except Exception as exc:
            logger.warning(f"[SQL Tool] execute_sql_on_data failed: {exc}")
            return f"SQL Error: {exc}"

    return [profile_data_file, execute_sql_on_data]
