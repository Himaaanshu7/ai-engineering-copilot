"""
Pure-Python export utilities.
No Streamlit imports — safe to use in tests.
"""

import datetime


def messages_to_markdown(messages: list[dict], session_id: str) -> str:
    """Convert a list of session messages into a downloadable Markdown document."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    user_count = len([m for m in messages if m["role"] == "user"])

    lines: list[str] = [
        "# AI Engineering Copilot — Session Export",
        "",
        "| | |",
        "|---|---|",
        f"| **Session** | `{session_id}` |",
        f"| **Exported** | {now} |",
        f"| **Exchanges** | {user_count} |",
        "",
        "---",
        "",
    ]

    for msg in messages:
        if msg["role"] == "user":
            file_tag = f" · `{msg['file_name']}`" if msg.get("file_name") else ""
            lines.append(f"### You{file_tag}")
        else:
            intent = msg.get("intent", "")
            intent_tag = f" · `{intent}`" if intent and intent not in ("error", "") else ""
            lines.append(f"### Copilot{intent_tag}")

        lines.append("")
        lines.append(msg["content"])
        lines.append("")

        if msg.get("sources"):
            lines.append("**Sources:**")
            for src in msg["sources"]:
                lines.append(f"- {src}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
