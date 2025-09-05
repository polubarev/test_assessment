# tools/sql_tool.py
from __future__ import annotations

from typing import Dict, Optional
import pandas as pd
import duckdb
from langchain_core.tools import tool
from app.lib.logging_config import get_logger


logger = get_logger(__name__)


def make_sql_tool(
    tables: Dict[str, pd.DataFrame],
    *,
    max_rows: int = 200
):
    """
    Returns an @tool-wrapped callable that executes read-only SQL (SELECT)
    against the provided DataFrames using DuckDB.
    """
    if not tables:
        raise ValueError("No DataFrames provided.")

    # Initialize in-memory DuckDB and register provided DataFrames once.
    logger.debug("Initializing DuckDB in-memory connection for SQL tool")
    conn = duckdb.connect(database=":memory:")
    table_schemas = {}
    for name, df in tables.items():
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"Table '{name}' is not a pandas.DataFrame.")
        logger.debug("Registering DataFrame as DuckDB table", extra={"table": name, "rows": getattr(df, 'shape', ('?', '?'))[0]})
        conn.register(name, df)
        # Capture schema (column names) for prompt clarity
        try:
            columns = list(df.columns)
        except Exception:
            columns = []
        table_schemas[name] = columns

    table_list = ", ".join(sorted(tables.keys()))
    schema_lines = []
    for t in sorted(table_schemas.keys()):
        cols = table_schemas[t]
        schema_lines.append(f"- {t}({', '.join(cols)})")
    schema_text = "\n".join(schema_lines)

    @tool
    def sql_query(query: str) -> str:
        """
        Execute a read-only SQL SELECT query against registered DataFrames.

        Constraints:
        - Only SELECT statements are allowed.
        - Available tables: {table_list}
        - Schemas:\n{schema_text}
        - Output: CSV with header, truncated to {max_rows} rows.

        Examples (adjust to your tables/columns):
        SELECT ip_address, COUNT(*) AS failed_attempts
        FROM ssh
        WHERE event_type IN ('FAILED_LOGIN','FAILED_LOGIN_INVALID_USER')
        GROUP BY ip_address
        ORDER BY failed_attempts DESC
        """
        q = query.strip().rstrip(";")
        logger.info(
            "SQL tool invoked",
            extra={
                "query": q,
                "query_length": len(q),
                "tables": sorted(tables.keys()),
                "max_rows": max_rows,
            },
        )
        if not q.upper().startswith("SELECT"):
            logger.warning("Rejected non-SELECT query", extra={"query": q})
            return "SQL error: Only SELECT queries are allowed."

        try:
            df = conn.execute(q).fetch_df()
            logger.debug(
                "SQL executed successfully",
                extra={
                    "rows": len(df),
                    "columns": list(df.columns),
                },
            )
        except Exception as e:
            logger.exception("SQL execution error: %s", e, extra={"query": q})
            return f"SQL error: {e}"

        if len(df) > max_rows:
            logger.info(
                "Truncating SQL result",
                extra={"max_rows": max_rows, "original_rows": len(df)},
            )
            df = df.head(max_rows)
        csv_out = df.to_csv(index=False)
        logger.debug("SQL tool returning CSV output", extra={"bytes": len(csv_out)})
        return csv_out

    # Bake table names & limits into the docstring for LLM discoverability
    sql_query.__doc__ = sql_query.__doc__.format(
        table_list=table_list,
        max_rows=max_rows,
    )
    return sql_query