import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
import os


def try_parse_ts(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def analyze_csv(path: str, top_k: int = 10) -> None:
    total_rows = 0
    columns = []
    nan_counts = Counter()
    value_counts = {
        "event_type": Counter(),
        "ip_address": Counter(),
        "username": Counter(),
    }
    first_ts = None
    last_ts = None
    per_day = Counter()
    per_hour = Counter()

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for row in reader:
            total_rows += 1

            # track NaNs (empty strings considered NaN)
            for col in columns:
                val = row.get(col, "")
                if val is None or val == "":
                    nan_counts[col] += 1

            # value counts
            value_counts["event_type"][row.get("event_type", "")] += 1
            value_counts["ip_address"][row.get("ip_address", "")] += 1
            value_counts["username"][row.get("username", "")] += 1

            # time aggregates
            ts = try_parse_ts(row.get("timestamp", ""))
            if ts is not None:
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts
                per_day[ts.strftime("%Y-%m-%d")] += 1
                per_hour[ts.strftime("%Y-%m-%d %H:00")] += 1

    print(f"File: {path}")
    print(f"Rows: {total_rows}")
    print(f"Columns: {columns}")
    print("\nNaNs per column:")
    for col in columns:
        print(f"  {col}: {nan_counts[col]}")

    print("\nEvent types (top):")
    for val, cnt in value_counts["event_type"].most_common(top_k):
        print(f"  {val}: {cnt}")

    print("\nTop IPs:")
    for val, cnt in value_counts["ip_address"].most_common(top_k):
        print(f"  {val}: {cnt}")

    print("\nTop usernames:")
    for val, cnt in value_counts["username"].most_common(top_k):
        print(f"  {val}: {cnt}")

    if first_ts and last_ts:
        print(f"\nTime range: {first_ts} -> {last_ts}")

    # per-day summary (top)
    print("\nEvents per day (top):")
    for day, cnt in per_day.most_common(top_k):
        print(f"  {day}: {cnt}")

    # per-hour summary (top)
    print("\nEvents per hour (top):")
    for hour, cnt in per_hour.most_common(top_k):
        print(f"  {hour}: {cnt}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Descriptive analysis for SSH audit CSV")
    parser.add_argument(
        "--input",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data/ssh-audit.csv")),
        help="Path to input CSV (default: data/ssh-audit.csv)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Top K entries to show for counts (default: 10)",
    )
    args = parser.parse_args()
    analyze_csv(args.input, args.top)


if __name__ == "__main__":
    main()


