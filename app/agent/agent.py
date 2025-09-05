# agent.py
from __future__ import annotations

# Ensure project root is importable when running this file directly
import os
import sys
if __package__ is None or __package__ == "":
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

from typing import Dict, Optional
import pandas as pd
import logging
from app.lib.logging_config import get_logger, setup_logging
from app.agent.tools import make_sql_tool

# LangGraph ReAct agent
from langgraph.prebuilt import create_react_agent

# ---- Model selection (two compatible paths) ----
# Preferred explicit class (works with langchain-ollama):
logger = get_logger(__name__)


def _make_model_via_class(model_name: str, temperature: float = 0.0):
    from langchain_ollama import ChatOllama
    logger.debug("Instantiating ChatOllama", extra={"model": model_name, "temperature": temperature})
    return ChatOllama(model=model_name, temperature=temperature)

# Alternative unified factory (if you prefer init_chat_model):
def _make_model_via_init(model_name: str, temperature: float = 0.0):
    from langchain.chat_models import init_chat_model
    # Supports provider prefixes like "ollama:llama3.1:8b" in modern LangChain
    logger.debug("Instantiating chat model via init_chat_model", extra={"model": model_name, "temperature": temperature})
    return init_chat_model(model_name, temperature=temperature)

def build_agent(
    *,
    model_name: str = "llama3.1:8b",  # the name as visible in `ollama list`
    use_init_factory: bool = False,
    temperature: float = 0.0,
    tools: Optional[list] = None,
    system_prompt: Optional[str] = None,
):
    """
    Create a ReAct agent over an Ollama-backed LangChain chat model.
    - model_name: Ollama model tag, e.g. "llama3.1:8b" or "qwen2.5:7b"
      (with `use_init_factory=True`, you can also pass "ollama:llama3.1:8b")
    - tools: list of callables (tool functions) with docstrings & type hints
    - system_prompt: static instructions for the agent (optional)
    """
    tools = tools or []
    logger.info("Building ReAct agent", extra={"model_name": model_name, "use_init_factory": use_init_factory, "temperature": temperature, "num_tools": len(tools)})

    if use_init_factory:
        model = _make_model_via_init(f"ollama:{model_name}", temperature=temperature)
    else:
        model = _make_model_via_class(model_name, temperature=temperature)

    logger.debug("Creating LangGraph ReAct agent")
    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=(
            system_prompt
            or "You are a precise, terse data assistant. "
               "When querying data, first decide if the SQL tool is needed. "
               "If you run SQL, SHOW the SQL you executed and summarize the result."
        ),
    )
    logger.info("Agent created")
    return agent


if __name__ == "__main__":
    setup_logging()
    logger.info(
        "The CLI has moved to scripts/run_questions.py. Use that script instead.")