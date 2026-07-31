from langchain_core.language_models import BaseChatModel
from loguru import logger

from config.settings import settings


class LLMFactory:
    """
    Returns a configured LangChain chat model for the specified provider.
    Switching LLM providers requires only a config change — no agent code changes.
    """

    @staticmethod
    def get_llm(provider: str | None = None, temperature: float = 0.1) -> BaseChatModel:
        provider = provider or settings.llm_provider
        logger.debug(f"Initializing LLM | provider={provider}")

        if provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                temperature=temperature,
            )

        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=temperature,
            )

        if provider == "claude":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.anthropic_model,
                api_key=settings.anthropic_api_key,
                temperature=temperature,
            )

        if provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
            )

        raise ValueError(f"Unknown LLM provider: '{provider}'. Valid options: groq, openai, claude, ollama")
