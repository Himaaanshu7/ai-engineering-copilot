from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from config.settings import settings
from database.connection import get_db
from database import crud
from backend.models.file import FileUploadResponse
from backend.services.file_service import save_upload

router = APIRouter()

_MAX_BYTES = settings.max_file_size_mb * 1024 * 1024
_ALLOWED_EXTENSIONS = {
    "py", "sql", "txt", "md", "csv", "json", "yaml", "yml",
    "parquet", "pdf", "js", "ts", "java", "go", "sh", "toml",
}


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
    db: AsyncSession | None = Depends(get_db),
) -> FileUploadResponse:
    original_name = file.filename or "upload"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '.{ext}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_file_size_mb} MB limit.",
        )

    stored_name, file_path, ext = save_upload(content, original_name)

    if db is not None:
        try:
            await crud.save_uploaded_file(
                db,
                session_id=session_id,
                filename=stored_name,
                original_filename=original_name,
                file_type=ext,
                file_path=file_path,
                size_bytes=len(content),
            )
        except Exception as exc:
            logger.warning(f"[Files] DB record failed (non-fatal): {exc}")

    logger.info(f"[API] POST /files/upload | {original_name} | {len(content):,} bytes")
    return FileUploadResponse(
        filename=stored_name,
        original_filename=original_name,
        file_type=ext,
        size_bytes=len(content),
        session_id=session_id,
    )
