from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from loguru import logger

from tools.report_tools import build_report_prompt, messages_to_pdf, ReportType
from llm.factory import LLMFactory

router = APIRouter()


class ReportMessage(BaseModel):
    role: str
    content: str
    intent: str | None = None
    agent_used: str | None = None
    sources: list[str] = []
    file_name: str | None = None


class GenerateReportRequest(BaseModel):
    messages: list[ReportMessage]
    session_id: str
    report_type: ReportType = "summary"


class GenerateReportResponse(BaseModel):
    report_markdown: str
    report_type: str
    message_count: int
    session_id: str


@router.post("/reports/generate", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest) -> GenerateReportResponse:
    """Generate an AI-written structured report from session messages."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    messages = [m.model_dump() for m in request.messages]
    prompt = build_report_prompt(messages, request.report_type)

    logger.info(f"[API] POST /reports/generate | type={request.report_type} | msgs={len(messages)}")

    try:
        llm = LLMFactory.get_llm(temperature=0.1)
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        report_md = response.content
    except Exception as exc:
        logger.error(f"[Reports] LLM generation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}")

    return GenerateReportResponse(
        report_markdown=report_md,
        report_type=request.report_type,
        message_count=len(messages),
        session_id=request.session_id,
    )


@router.post("/reports/pdf")
async def generate_pdf(request: GenerateReportRequest) -> Response:
    """Generate a PDF from session messages and return it as a downloadable file."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    messages = [m.model_dump() for m in request.messages]

    try:
        pdf_bytes = messages_to_pdf(messages, request.session_id)
    except Exception as exc:
        logger.error(f"[Reports] PDF generation failed: {exc}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    filename = f"copilot-{request.session_id[:8]}.pdf"
    logger.info(f"[API] POST /reports/pdf | session={request.session_id[:8]} | size={len(pdf_bytes):,} bytes")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
