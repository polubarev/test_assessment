from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import pandas as pd
import logging

from app.lib.ssh_log_parser import parse_log_file, write_csv
from app.agent.agent import build_agent
from app.agent.tools import make_sql_tool
from app.lib.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Simple API", version="1.0.0")

class PostRequest(BaseModel):
    message: str

class PostResponse(BaseModel):
    status: str
    received_message: str
    llm_response: str
    timestamp: str



@app.get("/health")
async def health():
    """Health check endpoint"""
    logger.debug("Health check called")
    resp = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    logger.debug("Health check response prepared")
    return resp

@app.post("/api/query", response_model=PostResponse)
async def query_endpoint(request: PostRequest):
    """POST endpoint that sends query to LLM and returns response"""
    try:
        logger.info("/api/query invoked", extra={"request_message": request.message})
        agent = getattr(app.state, "agent", None)
        if agent is None:
            logger.error("Agent not initialized")
            raise RuntimeError("Agent not initialized")

        logger.debug("Invoking agent with user message")
        result = agent.invoke({"messages": [("user", request.message)]})
        logger.debug("Agent returned result of type %s", type(result).__name__)

        output = ""
        try:
            messages = result.get("messages") if isinstance(result, dict) else None
            if messages:
                last = messages[-1]
                output = getattr(last, "content", None) or str(last)
        except Exception as parse_exc:
            logger.exception("Failed to parse agent result: %s", parse_exc)
            output = str(result)
        output = (output or "").strip() or "No output"
        logger.info("Responding to /api/query", extra={"truncated_llm_response": output[:200]})
        resp = PostResponse(
            status="success",
            received_message=request.message,
            llm_response=output,
            timestamp=datetime.now().isoformat()
        )
        return resp
    except Exception as e:
        logger.exception("Error in /api/query: %s", e)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.on_event("startup")
async def init_ssh_dataframe() -> None:
    """Generate CSV from log if needed and load into pandas DataFrame for later use."""
    # Resolve paths relative to project root (one level up from this file's directory)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    log_path = os.path.join(project_root, "data/ssh-audit.log")
    csv_path = os.path.join(project_root, "data/ssh-audit.csv")

    try:
        logger.info("Startup: initializing SSH DataFrame and agent")
        log_exists = os.path.exists(log_path)
        csv_exists = os.path.exists(csv_path)

        regenerate_csv = False
        if log_exists:
            if not csv_exists:
                regenerate_csv = True
            else:
                regenerate_csv = os.path.getmtime(csv_path) < os.path.getmtime(log_path)

        if regenerate_csv:
            logger.info("Regenerating CSV from log", extra={"log_path": log_path, "csv_path": csv_path})
            records = parse_log_file(log_path, None)
            write_csv(records, csv_path)

        if csv_exists or regenerate_csv:
            logger.debug("Loading DataFrame from CSV", extra={"csv_path": csv_path})
            app.state.ssh_df = pd.read_csv(csv_path)
        else:
            # If no files present, set empty DataFrame with expected columns
            logger.warning("No log or csv present; initializing empty DataFrame")
            app.state.ssh_df = pd.DataFrame(
                columns=[
                    "timestamp",
                    "ip_address",
                    "username",
                    "event_type",
                    "repetition_count",
                    "raw_message",
                ]
            )

        # Initialize the agent once with the SQL tool bound to the DataFrame
        try:
            logger.debug("Creating SQL tool for DataFrame", extra={"rows": getattr(app.state.ssh_df, 'shape', ('?', '?'))[0]})
            sql_tool = make_sql_tool({"ssh": app.state.ssh_df}, max_rows=200)
            # Load system prompt from file with safe fallback
            prompt_path = os.path.join(project_root, "app/agent/system_prompt.txt")
            default_prompt = (
                "You are a precise, terse data assistant. Use the SQL tool when needed."
            )
            try:
                with open(prompt_path, "r", encoding="utf-8") as fh:
                    file_prompt = (fh.read() or "").strip()
                    system_prompt = file_prompt or default_prompt
                    logger.debug("Loaded system prompt from file")
            except Exception as prompt_exc:
                logger.warning("Failed to read system prompt file; using default: %s", prompt_exc)
                system_prompt = default_prompt
            logger.info("Building agent", extra={"model": "qwen2.5:32b-instruct"})
            app.state.agent = build_agent(
                model_name="qwen2.5:32b-instruct",
                use_init_factory=False,
                temperature=0.0,
                tools=[sql_tool],
                system_prompt=system_prompt,
            )
            logger.info("Agent initialized successfully")
        except Exception as agent_exc:
            logger.exception("Failed to initialize agent: %s", agent_exc)
            app.state.agent = None
    except Exception as exc:
        # Fallback to empty DataFrame on initialization errors
        logger.exception("Startup initialization failed: %s", exc)
        app.state.ssh_df = pd.DataFrame(
            columns=[
                "timestamp",
                "ip_address",
                "username",
                "event_type",
                "repetition_count",
                "raw_message",
            ]
        )
        app.state.agent = None
        # Error already logged

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)