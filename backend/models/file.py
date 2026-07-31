from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    size_bytes: int
    session_id: str | None = None
