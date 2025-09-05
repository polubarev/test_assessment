import os
import sys
import json
import time
from typing import Any, Dict

import requests


def wait_for_server(base_url: str, timeout_seconds: int = 15) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            r = requests.get(f"{base_url}/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Server did not become ready in time")


def check_health(base_url: str) -> None:
    r = requests.get(f"{base_url}/health", timeout=10)
    r.raise_for_status()
    data = r.json()
    assert data.get("status") == "healthy", f"Unexpected health payload: {data}"
    print("/health OK", data)


def check_query(base_url: str, message: str = "Hello") -> None:
    payload: Dict[str, Any] = {"message": message}
    headers = {"Content-Type": "application/json"}
    r = requests.post(f"{base_url}/api/query", data=json.dumps(payload), headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    assert data.get("status") == "success", f"Unexpected query status: {data}"
    assert data.get("received_message") == message, f"Echo mismatch: {data}"
    assert isinstance(data.get("llm_response"), str) and len(data.get("llm_response")) >= 0
    print("/api/query OK", {k: v for k, v in data.items() if k != "llm_response"})


def main() -> None:
    base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    try:
        wait_for_server(base_url)
        check_health(base_url)
        check_query(base_url, os.environ.get("TEST_MESSAGE", "Hello from test"))
        print("All endpoint checks passed.")
    except Exception as e:
        print(f"Endpoint checks FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


