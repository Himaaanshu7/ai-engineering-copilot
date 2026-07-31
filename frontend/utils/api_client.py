import httpx
import streamlit as st
from loguru import logger


class APIClient:
    """HTTP client for communicating with the FastAPI backend."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._chat_timeout = 90.0
        self._upload_timeout = 60.0

    def health_check(self) -> dict:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.warning(f"[APIClient] Health check failed: {exc}")
            return {"status": "error", "detail": str(exc)}

    def send_message(self, message: str, session_id: str) -> dict:
        try:
            with httpx.Client(timeout=self._chat_timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/chat",
                    json={"message": message, "session_id": session_id},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"[APIClient] HTTP {exc.response.status_code}")
            return {"error": f"Backend error ({exc.response.status_code}): {exc.response.text}"}
        except httpx.TimeoutException:
            logger.error("[APIClient] Request timed out")
            return {"error": "Request timed out. The model may be processing a complex query."}
        except Exception as exc:
            logger.error(f"[APIClient] Unexpected error: {exc}")
            return {"error": str(exc)}

    def upload_file(self, file_bytes: bytes, filename: str, session_id: str) -> dict:
        """
        Upload a file for server-side processing.
        Full endpoint implementation arrives in Phase 4 (/api/v1/files/upload).
        """
        try:
            with httpx.Client(timeout=self._upload_timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/files/upload",
                    files={"file": (filename, file_bytes)},
                    data={"session_id": session_id},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"error": "File upload endpoint not yet available (Phase 4)"}
            return {"error": f"Upload failed ({exc.response.status_code})"}
        except Exception as exc:
            return {"error": str(exc)}

    def get_history(self, session_id: str) -> dict:
        """
        Retrieve persisted chat history.
        Full endpoint implementation arrives in Phase 4 (/api/v1/chat/history).
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/v1/chat/history/{session_id}")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"messages": [], "note": "History endpoint available in Phase 4"}
            return {"error": f"History fetch failed ({exc.response.status_code})"}
        except Exception as exc:
            return {"error": str(exc)}


@st.cache_resource
def get_api_client(base_url: str = "http://localhost:8000") -> APIClient:
    """One shared APIClient instance per Streamlit server process."""
    logger.info(f"[APIClient] Initializing client → {base_url}")
    return APIClient(base_url)
