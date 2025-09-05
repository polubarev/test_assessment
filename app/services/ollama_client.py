from functools import lru_cache
from langchain_community.chat_models import ChatOllama
from app.lib.logging_config import get_logger

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3.2"

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_llm(model_name: str = MODEL_NAME, base_url: str = OLLAMA_BASE_URL) -> ChatOllama:
    logger.debug("Creating ChatOllama client", extra={"model": model_name, "base_url": base_url})
    return ChatOllama(model=model_name, base_url=base_url)


def call_ollama(prompt: str, model_name: str = MODEL_NAME, base_url: str = OLLAMA_BASE_URL) -> str:
    """Call LLM via LangChain ChatOllama and return the response text."""
    try:
        logger.info("Calling Ollama LLM", extra={"model": model_name, "prompt_preview": prompt[:200]})
        llm = _get_llm(model_name=model_name, base_url=base_url)
        response = llm.invoke(prompt)
        # response is an AIMessage; extract content
        text = (getattr(response, "content", None) or str(response) or "").strip() or "No response from LLM"
        logger.debug("LLM response received", extra={"bytes": len(text)})
        return text
    except Exception as e:
        logger.exception("LLM call failed: %s", e)
        return f"Error: {str(e)}"


