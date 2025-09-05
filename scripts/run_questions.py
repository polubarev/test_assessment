from __future__ import annotations

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import List, Dict

import pandas as pd

# Ensure project root is importable when running this file directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.lib.logging_config import setup_logging, get_logger  # noqa: E402
from app.agent.agent import build_agent  # noqa: E402
from app.agent.tools import make_sql_tool  # noqa: E402


logger = get_logger(__name__)


def _resolve_paths(explicit_data_csv: str | None, explicit_prompt_path: str | None) -> Dict[str, str]:
    data_csv = (
        explicit_data_csv
        or os.path.join(PROJECT_ROOT, "data", "ssh-audit.csv")
    )
    prompt_path = (
        explicit_prompt_path
        or os.path.join(PROJECT_ROOT, "app", "agent", "system_prompt.txt")
    )
    return {"data_csv": data_csv, "prompt_path": prompt_path}


def _load_system_prompt(prompt_path: str) -> str:
    default_prompt = (
        "You are a precise, terse data assistant. Use the SQL tool when needed."
    )
    try:
        with open(prompt_path, "r", encoding="utf-8") as fh:
            file_prompt = (fh.read() or "").strip()
            if file_prompt:
                logger.debug("Loaded system prompt from file", extra={"prompt_path": prompt_path})
                return file_prompt
    except Exception as exc:
        logger.warning(
            "Failed to read system prompt file; using default",
            extra={"error": str(exc), "prompt_path": prompt_path},
        )
    return default_prompt


def _default_questions() -> List[str]:
    return [
        "What are the top 5 attacking IP addresses?",
        "Show me all failed login attempts from yesterday",
        "Are there any signs of brute force attacks?",
        "Which usernames are being targeted most frequently?",
        "How many total login attempts were recorded?",
    ]


def run_questions(
    *,
    data_csv_path: str,
    prompt_path: str,
    output_csv_path: str,
    model_name: str = "qwen2.5:32b-instruct",
    temperature: float = 0.0,
    max_tokens: int | None = None,
    questions: List[str] | None = None,
) -> str:
    logger.info(
        "Starting question run",
        extra={
            "data_csv_path": data_csv_path,
            "prompt_path": prompt_path,
            "output_csv_path": output_csv_path,
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )

    if not os.path.exists(data_csv_path):
        raise FileNotFoundError(f"CSV not found at {data_csv_path}")

    df = pd.read_csv(data_csv_path)
    sql_tool = make_sql_tool({"ssh": df}, max_rows=200)

    system_prompt = _load_system_prompt(prompt_path)

    agent = build_agent(
        model_name=model_name,
        use_init_factory=False,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=[sql_tool],
        system_prompt=system_prompt,
    )

    qs = questions or _default_questions()
    rows: List[Dict[str, str]] = []

    for idx, q in enumerate(qs, start=1):
        logger.info("Invoking agent", extra={"question": q, "index": idx})
        try:
            result = agent.invoke({"messages": [("user", q)]})
        except Exception as exc:
            logger.exception("Agent invocation failed", extra={"question": q, "index": idx})
            answer_text = f"ERROR: {exc}"
        else:
            try:
                messages = result.get("messages") if isinstance(result, dict) else None
                if messages:
                    last = messages[-1]
                    answer_text = getattr(last, "content", None) or str(last)
                else:
                    answer_text = str(result)
            except Exception as parse_exc:
                logger.exception("Failed to parse agent result", extra={"error": str(parse_exc)})
                answer_text = str(result)

        rows.append(
            {
                "index": idx,
                "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "question": q,
                "answer": (answer_text or "").strip() or "No output",
            }
        )

    out_dir = os.path.dirname(output_csv_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    pd.DataFrame(rows).to_csv(output_csv_path, index=False)
    logger.info("Saved results", extra={"output_csv_path": output_csv_path, "rows": len(rows)})
    return output_csv_path


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run 5 security questions and save answers to CSV")
    parser.add_argument(
        "--data-csv",
        dest="data_csv",
        default=None,
        help="Path to input ssh-audit.csv (defaults to data/ssh-audit.csv)",
    )
    parser.add_argument(
        "--prompt",
        dest="prompt_path",
        default=None,
        help="Path to system prompt txt (defaults to app/agent/system_prompt.txt)",
    )
    parser.add_argument(
        "--out",
        dest="output_csv",
        default=os.path.join(PROJECT_ROOT, "data", "agent_answers.csv"),
        help="Path to write answers CSV (defaults to data/agent_answers.csv)",
    )
    parser.add_argument(
        "--model",
        dest="model_name",
        default="qwen2.5:32b-instruct",
        help="Ollama model name/tag",
    )
    parser.add_argument(
        "--temperature",
        dest="temperature",
        type=float,
        default=0.0,
        help="Sampling temperature",
    )
    parser.add_argument(
        "--max-tokens",
        dest="max_tokens",
        type=int,
        default=None,
        help="Maximum number of output tokens (Ollama num_predict)",
    )

    args = parser.parse_args(argv)

    setup_logging()
    paths = _resolve_paths(args.data_csv, args.prompt_path)

    try:
        run_questions(
            data_csv_path=paths["data_csv"],
            prompt_path=paths["prompt_path"],
            output_csv_path=args.output_csv,
            model_name=args.model_name,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    except SystemExit:
        raise
    except Exception as exc:
        logger.exception("run_questions failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


