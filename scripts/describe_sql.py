from __future__ import annotations

import os
import sys
import argparse
from typing import Literal

import pandas as pd
import duckdb

# Ensure project root is importable when running this file directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.lib.logging_config import setup_logging, get_logger  # noqa: E402


logger = get_logger(__name__)


def describe_table(
    *,
    data_csv_path: str,
    table_name: str = "ssh",
    output_format: Literal["text", "csv", "json"] = "text",
) -> str:
    if not os.path.exists(data_csv_path):
        raise FileNotFoundError(f"CSV not found at {data_csv_path}")

    logger.info(
        "Describing SQL table",
        extra={
            "data_csv_path": data_csv_path,
            "table_name": table_name,
            "output_format": output_format,
        },
    )

    df = pd.read_csv(data_csv_path)

    conn = duckdb.connect(database=":memory:")
    conn.register(table_name, df)

    desc_df = conn.execute(f"DESCRIBE {table_name}").fetch_df()

    if output_format == "csv":
        return desc_df.to_csv(index=False)
    if output_format == "json":
        return desc_df.to_json(orient="records")
    # default text (pretty)
    return desc_df.to_string(index=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show DuckDB DESCRIBE output for the registered table (default: ssh)",
    )
    parser.add_argument(
        "--data-csv",
        dest="data_csv",
        default=os.path.join(PROJECT_ROOT, "data", "ssh-audit.csv"),
        help="Path to input ssh-audit.csv (defaults to data/ssh-audit.csv)",
    )
    parser.add_argument(
        "--table",
        dest="table_name",
        default="ssh",
        help="Table name to register and describe (defaults to ssh)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "csv", "json"],
        default="text",
        help="Output format (text, csv, json)",
    )

    args = parser.parse_args(argv)

    setup_logging()

    try:
        out = describe_table(
            data_csv_path=args.data_csv,
            table_name=args.table_name,
            output_format=args.output_format,
        )
    except SystemExit:
        raise
    except Exception as exc:
        logger.exception("describe_sql failed: %s", exc)
        return 1

    # Write to stdout
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


