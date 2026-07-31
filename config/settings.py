from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "AI Engineering Copilot"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:8501"

    # LLM Provider
    llm_provider: Literal["groq", "openai", "claude", "ollama"] = "groq"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # PostgreSQL
    postgres_url: str = "postgresql+asyncpg://copilot:copilot123@localhost:5432/copilot_db"
    postgres_pool_size: int = 10

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "copilot_docs"

    # Embedding Model (local)
    embedding_model: str = "all-MiniLM-L6-v2"

    # External APIs
    github_token: str = ""
    tavily_api_key: str = ""

    # File Uploads
    upload_dir: str = "./data/uploads"
    max_file_size_mb: int = 50


settings = Settings()
