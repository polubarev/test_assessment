# LLM-Powered SSH Log Analysis API

This project provides a REST API service that can answer natural language questions about SSH log data. It uses a local LLM, managed by Ollama, to analyze log entries and provide structured answers.

This project was built to satisfy the requirements of the "AI/ML Engineer Coding Exercise - LLM-Powered Log Analysis".

## Features

- **Natural Language Queries:** Ask questions about SSH logs in plain English.
- **Fast & Efficient:** Uses DuckDB for high-performance, in-memory SQL analytics on log data.
- **Advanced Agentic Architecture:** Built with LangChain and LangGraph, using a ReAct (Reason-Act) agent for intelligent tool use.
- **Robust Data Parsing:** Efficiently parses standard and non-standard SSH log formats into structured data.
- **Scalable Design:** The core logic is designed to handle datasets much larger than system memory with minor adjustments.
- **Asynchronous API:** Built with FastAPI for high-performance, non-blocking I/O.

## Architecture Overview

The system is designed for efficiency and intelligence, combining several modern data and AI engineering practices.

1.  **Log Preprocessing:** On startup, the service scans the `data/ssh-audit.log` file. It parses the raw text into a structured `data/ssh-audit.csv` file. This parsing step is optimized to only run if the log file is newer than the existing CSV.
2.  **In-Memory Analytics Engine:** The structured CSV data is loaded into a Pandas DataFrame, which is then registered as a virtual table in an in-memory DuckDB database. This provides a powerful, zero-latency SQL interface for the LLM to query.
3.  **Agentic LLM Core:** A LangGraph ReAct agent is initialized with a single, powerful tool: `sql_query`. The agent's system prompt and the tool's docstring are dynamically generated to give the LLM precise instructions and context about the database schema, enabling it to write its own SQL queries to answer user questions.
4.  **API Layer:** A FastAPI server exposes a single endpoint, `/api/query`, which passes the user's question directly to the agent for processing.

## Setup and Installation

### 1. Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running.

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-repository-name>
```

### 3. Install Dependencies

Create and activate a virtual environment, then install the required packages.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Set up the LLM

Pull the required model using Ollama. The application is configured to use `qwen2.5:32b-instruct`, but this can be changed in `app/main.py`.

```bash
ollama pull qwen2.5:32b-instruct
```

## Running the Application

This project can be used in two ways: as a real-time REST API server or as a command-line tool for batch processing.

### 1. API Server

Launch the API server using Uvicorn.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### 2. Command-Line Scripts

The `scripts/` directory contains powerful tools for interacting with the agent from the command line.

#### Running Batch Questions

The `run_questions.py` script executes a predefined list of questions, invokes the agent for each, and saves the complete results to a CSV file.

```bash
python scripts/run_questions.py
```

By default, this saves the output to `data/agent_answers.csv`. You can customize the model, questions, and output path via command-line arguments. Use `--help` to see all options.

```bash
python scripts/run_questions.py --help
```

#### Inspecting the Database Schema

The `describe_sql.py` script is a developer utility that prints the schema of the in-memory DuckDB table. This is useful for understanding the data structure the agent sees.

```bash
python scripts/describe_sql.py
```

## API Documentation

The API provides two endpoints.

### Health Check

You can check if the service is running by making a GET request to `/health`.

```bash
curl http://localhost:8000/health
```

### Natural Language Query

Submit questions as a JSON payload to the `/api/query` endpoint.

**Request:**

```bash
curl -X POST http://localhost:8000/api/query \
-H "Content-Type: application/json" \
-d '{
  "message": "What are the top 5 attacking IP addresses?"
}'
```

**Example Response:**

The API returns a structured JSON response containing the original question, the LLM\'s answer, and metadata. The LLM has been prompted to provide a direct summary, key findings, and the exact SQL query it executed.

```json
{
  "status": "success",
  "received_message": "What are the top 5 attacking IP addresses?",
  "llm_response": "Summary: The top 5 attacking IP addresses are 180.101.148.135, 222.186.56.13, 112.90.143.11, 221.229.166.231, and 121.18.238.124.\n\nFindings:\n- 180.101.148.135: 10 attempts\n- 222.186.56.13: 8 attempts\n- 112.90.143.11: 7 attempts\n- 221.229.166.231: 6 attempts\n- 121.18.238.124: 5 attempts\n\nSQL:\n```sql\nSELECT ip_address, COUNT(*) AS attempt_count\nFROM ssh\nWHERE event_type LIKE \'FAILED_LOGIN%\'\nGROUP BY ip_address\nORDER BY attempt_count DESC\nLIMIT 5;\n```",
  "timestamp": "2023-10-27T10:00:00.123456"
}
```