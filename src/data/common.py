from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
REPORT_DIR = DATA_DIR / "reports"
INTERIM_DIR = DATA_DIR / "interim"
EXTERNAL_EVAL_DIR = DATA_DIR / "external_eval"
PILOT_DIR = DATA_DIR / "pilot"
CACHE_DIR = DATA_DIR / "cache"


def load_json_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def read_url_json(url: str, timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "edu-pprm-pilot/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def read_url_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "edu-pprm-pilot/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_hf_rows(dataset: str, config: str, split: str, limit: int) -> list[dict[str, Any]]:
    if limit > 100:
        rows: list[dict[str, Any]] = []
        offset = 0
        while len(rows) < limit:
            page_length = min(100, limit - len(rows))
            query = urllib.parse.urlencode(
                {
                    "dataset": dataset,
                    "config": config,
                    "split": split,
                    "offset": offset,
                    "length": page_length,
                }
            )
            payload = read_url_json(f"https://datasets-server.huggingface.co/rows?{query}")
            page = [item["row"] for item in payload.get("rows", [])]
            if not page:
                break
            rows.extend(page)
            offset += len(page)
        return rows
    query = urllib.parse.urlencode(
        {
            "dataset": dataset,
            "config": config,
            "split": split,
            "offset": 0,
            "length": limit,
        }
    )
    payload = read_url_json(f"https://datasets-server.huggingface.co/rows?{query}")
    return [item["row"] for item in payload.get("rows", [])]


def read_jsonl_url_prefix(url: str, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    req = urllib.request.Request(url, headers={"User-Agent": "edu-pprm-pilot/0.1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def refresh_problem_bank() -> int:
    rows = []
    rows.extend(read_jsonl_file(INTERIM_DIR / "gsm8k.problem_bank.raw.jsonl"))
    rows.extend(read_jsonl_file(INTERIM_DIR / "math.problem_bank.raw.jsonl"))
    return write_jsonl(INTERIM_DIR / "problem_bank.raw.jsonl", rows)


def write_missing_csv(path: Path, rows: list[dict[str, Any]], required: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    missing_rows = []
    for row in rows:
        missing = [field for field in required if is_missing(row.get(field))]
        if missing:
            missing_rows.append(
                {
                    "source_id": row.get("source_id", ""),
                    "missing_fields": ";".join(missing),
                }
            )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_id", "missing_fields"])
        writer.writeheader()
        writer.writerows(missing_rows)
    return len(missing_rows)


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def field_coverage(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, dict[str, float | int]]:
    total = len(rows)
    coverage: dict[str, dict[str, float | int]] = {}
    for field in fields:
        present = sum(0 if is_missing(row.get(field)) else 1 for row in rows)
        coverage[field] = {
            "present": present,
            "total": total,
            "coverage": round(present / total, 4) if total else 0.0,
        }
    return coverage


def summarize_source(
    *,
    source: str,
    rows: list[dict[str, Any]],
    fields: list[str],
    output_path: Path,
    examples_path: Path,
    notes: list[str] | None = None,
    mappable_fields: dict[str, str] | None = None,
    unmappable_fields: dict[str, str] | None = None,
) -> dict[str, Any]:
    summary = {
        "source": source,
        "row_count": len(rows),
        "field_coverage": field_coverage(rows, fields),
        "mappable_fields": mappable_fields or {},
        "unmappable_fields": unmappable_fields or {},
        "notes": notes or [],
    }
    write_json(output_path, summary)
    write_jsonl(examples_path, rows[:20])
    return summary


def split_steps(text: str | None) -> list[str]:
    if not text:
        return []
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.replace("\\\\", "\n")
    raw_parts = re.split(r"\n+|(?<=\.)\s+(?=[A-Z0-9$\\-])|={2,}|#+", cleaned)
    parts = []
    for part in raw_parts:
        item = re.sub(r"\s+", " ", part).strip()
        if item:
            parts.append(item)
    return parts


def extract_gsm8k_answer(answer: str | None) -> tuple[str | None, str | None]:
    if not answer:
        return None, None
    if "####" in answer:
        solution, final = answer.rsplit("####", 1)
        return solution.strip(), final.strip()
    return answer.strip(), None


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def default_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--limit", type=positive_int, default=20)
    parser.add_argument("--offline", action="store_true", help="only use local data/raw files")
    return parser


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)
