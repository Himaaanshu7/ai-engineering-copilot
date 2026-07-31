"""
Report generation utilities — Markdown and PDF.
No Streamlit imports — safe to use in backend and tests.
"""

import datetime
import io
import re
import textwrap
from typing import Literal

ReportType = Literal["summary", "technical", "interview"]


# ── Markdown helpers ───────────────────────────────────────────────────────────

_UNICODE_REPLACEMENTS = str.maketrans({
    "–": "-",   # en-dash
    "—": "-",   # em-dash
    "‘": "'",   # left single quote
    "’": "'",   # right single quote
    "“": '"',   # left double quote
    "”": '"',   # right double quote
    "…": "...", # ellipsis
    "•": "*",   # bullet
    "·": "*",   # middle dot
    "→": "->",  # right arrow
    "←": "<-",  # left arrow
    "★": "*",   # star
    " ": " ",   # non-breaking space
})


def _to_latin1(text: str) -> str:
    """Replace common Unicode characters with Latin-1 equivalents."""
    text = text.translate(_UNICODE_REPLACEMENTS)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _strip_markdown(text: str) -> str:
    """Remove basic Markdown syntax for plain-text PDF rendering."""
    text = re.sub(r"#{1,6}\s+", "", text)          # headings
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # italic
    text = re.sub(r"`(.+?)`", r"\1", text)          # inline code
    text = re.sub(r"```[\s\S]*?```", "[code block]", text)  # code blocks
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text) # links
    text = re.sub(r"^\s*[-*]\s+", "* ", text, flags=re.MULTILINE)
    return text.strip()


def messages_to_pdf(messages: list[dict], session_id: str) -> bytes:
    """
    Convert session messages to a PDF file.
    Returns raw PDF bytes suitable for st.download_button.
    """
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(14, 165, 233)   # sky blue
            self.cell(0, 8, "AI Engineering Copilot", align="L")
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, f"Session: {session_id[:12]}...", align="R")
            self.ln(4)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, f"Page {self.page_no()} - Generated {datetime.datetime.now().strftime('%Y-%m-%d')}", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Session Export", ln=True)
    pdf.ln(2)

    # Metadata
    user_count = len([m for m in messages if m["role"] == "user"])
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Exported: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}   |   Exchanges: {user_count}", ln=True)
    pdf.ln(6)

    for msg in messages:
        role = msg["role"]
        content = _to_latin1(_strip_markdown(msg.get("content", "")))

        # Role header
        if role == "user":
            pdf.set_fill_color(240, 249, 255)
            pdf.set_text_color(14, 165, 233)
            pdf.set_font("Helvetica", "B", 10)
            label = "You"
            if msg.get("file_name"):
                label += f"  [{_to_latin1(msg['file_name'])}]"
        else:
            pdf.set_fill_color(248, 250, 252)
            intent = msg.get("intent", "")
            pdf.set_text_color(16, 185, 129)
            pdf.set_font("Helvetica", "B", 10)
            label = f"Copilot [{intent}]" if intent else "Copilot"

        pdf.cell(0, 7, _to_latin1(label), ln=True)

        # Message content
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "", 9)
        for line in content.split("\n"):
            wrapped = textwrap.wrap(line, width=105) or [""]
            for wline in wrapped:
                pdf.cell(0, 5, wline, ln=True)

        # Sources
        sources = msg.get("sources") or []
        if sources:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
            src_text = _to_latin1("Sources: " + ", ".join(str(s) for s in sources[:3]))
            pdf.cell(0, 5, src_text, ln=True)

        pdf.ln(3)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    return bytes(pdf.output())


# ── AI report templates ────────────────────────────────────────────────────────

def build_report_prompt(messages: list[dict], report_type: ReportType) -> str:
    """
    Build the LLM prompt for generating a structured report from session messages.
    """
    # Summarize messages into a compact transcript
    transcript_lines: list[str] = []
    for m in messages[-40:]:  # last 40 messages max
        role = "User" if m["role"] == "user" else f"Copilot [{m.get('intent','')}]"
        content = m.get("content", "")[:400]
        transcript_lines.append(f"{role}: {content}")

    transcript = "\n\n".join(transcript_lines)

    if report_type == "summary":
        return f"""You are a technical writer. Based on the session transcript below, generate a clean executive summary report.

## Session Transcript
{transcript}

---

Generate a report with these sections:

# Session Summary Report
*Generated {datetime.datetime.now().strftime("%Y-%m-%d")}*

## Overview
2-3 sentences describing what was accomplished in this session.

## Topics Covered
Bullet list of specific technical topics discussed.

## Key Findings & Solutions
The most important answers, code fixes, or insights from the session.

## Action Items
What the user should do next based on this session.

## Resources Referenced
Any tools, libraries, or documentation mentioned.

Write in professional technical documentation style. Be specific — reference actual code, queries, or concepts from the transcript."""

    elif report_type == "technical":
        return f"""You are a Senior Engineer writing technical documentation. Based on this session transcript, generate comprehensive technical documentation.

## Session Transcript
{transcript}

---

Generate a technical report with these sections:

# Technical Deep-Dive Report
*Generated {datetime.datetime.now().strftime("%Y-%m-%d")}*

## Problem Statement
What technical problem or question was being addressed.

## Architecture / Approach
The technical approach discussed or recommended.

## Code Solutions
Any SQL queries, Python code, or configurations from the session (use code blocks).

## Performance & Optimization Notes
Any performance considerations, complexity analysis, or optimization tips discussed.

## Best Practices Applied
Engineering best practices highlighted in this session.

## Technical Debt & Risks
Issues identified that need future attention.

## Next Steps
Concrete technical next steps with priority order.

Be specific and technical. Include actual code from the session."""

    else:  # interview
        return f"""You are an interview coach. Based on this session transcript, generate an interview preparation cheat sheet.

## Session Transcript
{transcript}

---

Generate an interview prep sheet with these sections:

# Interview Preparation Sheet
*Generated {datetime.datetime.now().strftime("%Y-%m-%d")}*

## Topics to Master
The technical topics from this session that commonly appear in interviews.

## Key Questions & Strong Answers
For each topic discussed, provide:
- **Q:** The interview question
- **A:** A strong, concise answer using the STAR method where applicable

## Code Patterns to Know
Important code patterns or SQL queries from this session that interviewers test.

## System Design Concepts
Any architecture or system design concepts discussed.

## Company-Specific Tips
If any specific companies (Amazon, Databricks, Snowflake, etc.) were mentioned, add targeted tips.

## 30-Second Elevator Pitches
Brief, confident explanations for each core concept covered.

Format for easy review the night before an interview."""
