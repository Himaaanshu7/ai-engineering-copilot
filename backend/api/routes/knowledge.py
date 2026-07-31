from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


class IngestRequest(BaseModel):
    file_path: str
    source_name: str | None = None


class IngestResponse(BaseModel):
    source: str
    chunks_ingested: int
    collection_size: int


class KnowledgeStatsResponse(BaseModel):
    collection_name: str
    total_chunks: int
    web_search_available: bool


@router.get("/knowledge/stats", response_model=KnowledgeStatsResponse)
async def knowledge_stats() -> KnowledgeStatsResponse:
    """Return current knowledge base statistics."""
    try:
        from rag.vectorstore import collection_stats
        from tools.web_search_tools import is_search_available
        stats = collection_stats()
        return KnowledgeStatsResponse(
            collection_name=stats["name"],
            total_chunks=stats["count"],
            web_search_available=is_search_available(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/knowledge/ingest", response_model=IngestResponse)
async def ingest_file(request: IngestRequest) -> IngestResponse:
    """Ingest a file into the ChromaDB knowledge base."""
    try:
        from rag.ingestion import ingest_file as do_ingest
        from rag.vectorstore import collection_stats
        from pathlib import Path

        path = Path(request.file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

        count = do_ingest(path, source_name=request.source_name)
        stats = collection_stats()

        logger.info(f"[API] POST /knowledge/ingest | source={path.name} | chunks={count}")
        return IngestResponse(
            source=request.source_name or path.name,
            chunks_ingested=count,
            collection_size=stats["count"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
