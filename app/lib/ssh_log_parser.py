import argparse
import csv
import os
import re
from datetime import datetime
from typing import Dict, Iterator, Optional
from app.lib.logging_config import get_logger
logger = get_logger(__name__)


MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


TIMESTAMP_PREFIX_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+([ 0-9]{1,2})\s+([0-9]{2}:[0-9]{2}:[0-9]{2})\s+(.*)$")

# message repeated N times: [ ... ]
REPEATED_WRAPPER_RE = re.compile(r"message repeated (\d+) times: \[(.+)\]")

# Failed password (with optional 'invalid user ')
FAILED_PASSWORD_RE = re.compile(
    r"Failed password for (invalid user )?(?P<username>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"
)

# Invalid user
INVALID_USER_RE = re.compile(
    r"Invalid user (?P<username>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"
)

# PAM authentication failure
PAM_AUTH_FAILURE_RE = re.compile(
    r"authentication failure;.*?rhost=(?P<ip>[\w\.-]+?)\s+user=(?P<username>\S+)",
    re.IGNORECASE,
)


def parse_syslog_timestamp_from_parts(month_abbr: str, day_str: str, time_str: str, default_year: int) -> Optional[str]:
    logger.debug("Parsing timestamp parts", extra={"month": month_abbr, "day": day_str, "time": time_str, "year": default_year})
    month = MONTHS.get(month_abbr)
    if month is None:
        logger.warning("Unknown month abbreviation", extra={"month": month_abbr})
        return None
    try:
        day = int(day_str.strip())
        dt = datetime.strptime(f"{default_year}-{month:02d}-{day:02d} {time_str}", "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        logger.exception("Failed to parse timestamp")
        return None


def split_prefix_and_message(line: str) -> Optional[Dict[str, str]]:
    m = TIMESTAMP_PREFIX_RE.match(line)
    if not m:
        return None
    month_abbr, day_str, time_str, rest = m.groups()
    return {
        "month": month_abbr,
        "day": day_str,
        "time": time_str,
        "rest": rest,
    }


def classify_and_extract(message: str) -> Optional[Dict[str, str]]:
    logger.debug("Classifying message", extra={"message_preview": message[:200]})
    # Failed password
    m = FAILED_PASSWORD_RE.search(message)
    if m:
        username = m.group("username")
        ip = m.group("ip")
        is_invalid = m.group(1) is not None
        event_type = "FAILED_LOGIN_INVALID_USER" if is_invalid else "FAILED_LOGIN"
        return {"event_type": event_type, "username": username, "ip_address": ip}

    # Invalid user
    m = INVALID_USER_RE.search(message)
    if m:
        return {
            "event_type": "INVALID_USER",
            "username": m.group("username"),
            "ip_address": m.group("ip"),
        }

    # PAM authentication failure
    m = PAM_AUTH_FAILURE_RE.search(message)
    if m:
        return {
            "event_type": "PAM_AUTH_FAILURE",
            "username": m.group("username"),
            "ip_address": m.group("ip"),
        }

    return None


def parse_line(line: str, default_year: int) -> Optional[Dict[str, object]]:
    logger.debug("Parsing line", extra={"line_preview": line[:200]})
    parts = split_prefix_and_message(line)
    if not parts:
        logger.debug("Line did not match timestamp prefix")
        return None

    timestamp = parse_syslog_timestamp_from_parts(parts["month"], parts["day"], parts["time"], default_year)
    if not timestamp:
        logger.debug("Timestamp parsing failed")
        return None

    rest = parts["rest"]

    # Find the message portion after process tag, if present: "host process[pid]: message"
    # Split on first ': ' which usually separates the message content
    msg_split_idx = rest.find(": ")
    message = rest[msg_split_idx + 2 :] if msg_split_idx != -1 else rest

    # Handle repeated wrapper
    rm = REPEATED_WRAPPER_RE.search(message)
    repetition_count = 1
    if rm:
        try:
            repetition_count = int(rm.group(1))
        except ValueError:
            repetition_count = 1
        inner_message = rm.group(2)
        logger.debug("Detected repeated wrapper", extra={"repetitions": repetition_count})
        details = classify_and_extract(inner_message)
    else:
        details = classify_and_extract(message)

    if not details:
        return None

    record = {
        "timestamp": timestamp,
        "ip_address": details.get("ip_address", ""),
        "username": details.get("username", ""),
        "event_type": details.get("event_type", "UNKNOWN"),
        "repetition_count": repetition_count,
        "raw_message": line.rstrip("\n"),
    }
    logger.debug("Parsed record", extra={"event_type": record["event_type"], "ip_address": record["ip_address"]})
    return record


def parse_log_file(path: str, default_year: Optional[int] = None) -> Iterator[Dict[str, object]]:
    logger.info("Parsing log file", extra={"path": path, "default_year": default_year})
    year = default_year or datetime.now().year
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            rec = parse_line(line, year)
            if rec:
                yield rec


def write_csv(records: Iterator[Dict[str, object]], out_path: str) -> None:
    logger.info("Writing CSV", extra={"out_path": out_path})
    fieldnames = [
        "timestamp",
        "ip_address",
        "username",
        "event_type",
        "repetition_count",
        "raw_message",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)
    logger.info("CSV write complete", extra={"out_path": out_path})


def main() -> None:
    logger.info("ssh_log_parser main invoked")
    parser = argparse.ArgumentParser(description="Parse SSH auth logs into structured CSV")
    parser.add_argument(
        "--input",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data/ssh-audit.log")),
        help="Path to input log file (default: data/ssh-audit.log)",
    )
    parser.add_argument(
        "--output",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "data/ssh-audit.csv")),
        help="Path to output CSV file (default: data/ssh-audit.csv)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Fallback year for syslog timestamps (default: current year)",
    )
    args = parser.parse_args()

    records = parse_log_file(args.input, args.year)
    write_csv(records, args.output)
    print(f"Wrote CSV: {args.output}")


if __name__ == "__main__":
    main()


