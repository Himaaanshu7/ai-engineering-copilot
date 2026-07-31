import uuid
from pathlib import Path

from loguru import logger

from config.settings import settings


def save_upload(file_bytes: bytes, original_filename: str) -> tuple[str, str, str]:
    """
    Persist raw bytes to the upload directory.
    Returns (stored_filename, absolute_file_path, extension).
    """
    ext = (
        original_filename.rsplit(".", 1)[-1].lower()
        if "." in original_filename
        else "bin"
    )
    stored_name = f"{uuid.uuid4().hex}.{ext}"

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / stored_name
    file_path.write_bytes(file_bytes)

    logger.info(
        f"[FileService] Saved | {original_filename} → {stored_name} | {len(file_bytes):,} bytes"
    )
    return stored_name, str(file_path), ext
