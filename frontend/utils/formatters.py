"""
Pure-Python helpers for building file context strings.
No Streamlit imports — safe to use in tests.
"""


def build_file_context(uploaded_file) -> tuple[str, str]:
    """
    Read an uploaded file and return (context_string, filename).
    The context_string is prepended to the user's message before sending to the backend.
    Caps text files at 8,000 characters to stay within LLM context limits.
    """
    name: str = uploaded_file.name
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    # ── Text-based source files ──────────────────────────────────────────────
    if ext in ("py", "sql", "txt", "md", "json", "yaml", "yml"):
        content = uploaded_file.read().decode("utf-8", errors="replace")
        lang_map = {
            "py": "python",
            "sql": "sql",
            "txt": "text",
            "md": "markdown",
            "json": "json",
            "yaml": "yaml",
            "yml": "yaml",
        }
        lang = lang_map.get(ext, "text")
        truncated = content[:8000]
        context = (
            f"I've attached a file `{name}`. Here is its content:\n\n"
            f"```{lang}\n{truncated}\n```"
        )
        if len(content) > 8000:
            context += (
                f"\n\n*(File truncated — showing first 8,000 of {len(content):,} characters)*"
            )
        return context, name

    # ── CSV ──────────────────────────────────────────────────────────────────
    if ext == "csv":
        try:
            import pandas as pd

            df = pd.read_csv(uploaded_file)
            shape_info = f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns"
            dtypes = df.dtypes.to_string()
            sample = df.head(20).to_markdown(index=False)
            context = (
                f"I've attached a CSV file `{name}`.\n\n"
                f"**{shape_info}**\n\n"
                f"**Column types:**\n```\n{dtypes}\n```\n\n"
                f"**First 20 rows:**\n{sample}"
            )
            return context, name
        except Exception as exc:
            return f"Attached CSV `{name}` (preview failed: {exc})", name

    # ── Parquet ──────────────────────────────────────────────────────────────
    if ext == "parquet":
        try:
            import pandas as pd

            df = pd.read_parquet(uploaded_file)
            shape_info = f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns"
            dtypes = df.dtypes.to_string()
            sample = df.head(10).to_markdown(index=False)
            context = (
                f"I've attached a Parquet file `{name}`.\n\n"
                f"**{shape_info}**\n\n"
                f"**Column types:**\n```\n{dtypes}\n```\n\n"
                f"**First 10 rows:**\n{sample}"
            )
            return context, name
        except Exception as exc:
            return f"Attached Parquet `{name}` (preview failed: {exc})", name

    # ── PDF — deferred to Phase 8 ────────────────────────────────────────────
    if ext == "pdf":
        return (
            f"I've attached a PDF file `{name}`. "
            f"Full PDF parsing via PyMuPDF + RAG will be available in Phase 8. "
            f"Please describe what you'd like to know about this document.",
            name,
        )

    # ── Unknown / unsupported ────────────────────────────────────────────────
    return (
        f"Attached file `{name}` — unsupported format for inline preview.",
        name,
    )
