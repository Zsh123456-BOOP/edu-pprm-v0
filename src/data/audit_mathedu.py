from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from src.data.common import DATA_DIR, REPORT_DIR, is_missing, split_steps, write_json, write_jsonl

GITHUB_API_ROOT = "https://api.github.com/repos/NYCU-NLP-Lab/MathEDU/contents"
RAW_GITHUB_ROOT = "https://raw.githubusercontent.com/NYCU-NLP-Lab/MathEDU/main"
RAW_ROOT = DATA_DIR / "raw" / "mathedu"
KNOWN_DATASET_PATHS = [
    *[
        f"dataset/leave_one_out/student{student}/{split}.json"
        for student in range(1, 7)
        for split in ("test", "train", "val")
    ],
    "dataset/time_series_split/test.json",
    "dataset/time_series_split/train.json",
    "dataset/time_series_split/val.json",
]
QUESTION_FIELDS = [
    "problem_text",
    "problem",
    "question",
    "prompt",
    "original_question",
]
ID_FIELDS = [
    "problem_id",
    "source_id",
    "image_id",
    "worksheet_id",
    "id",
]
STUDENT_FIELDS = ["student_solution_raw", "student_process", "student_solution", "student_answer"]
FEEDBACK_FIELDS = ["teacher_feedback", "teacher_review", "feedback"]
ERROR_FIELDS = [
    "error_type",
    "reason",
    "the_reason_why_student_cant_solve_en",
    "the_reason_why_student_cant_solve_ch",
]


def _github_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "edu-pprm-pilot/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _github_bytes(url: str, timeout: int = 180) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "edu-pprm-pilot/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        chunks = []
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)


def discover_dataset_files() -> list[dict[str, str]]:
    files: list[dict[str, str]] = []

    def walk(path: str) -> None:
        for item in _github_json(f"{GITHUB_API_ROOT}/{path}?ref=main"):
            if item["type"] == "dir":
                walk(item["path"])
            elif item["name"].endswith(".json"):
                files.append({"path": item["path"], "download_url": item["download_url"]})

    try:
        walk("dataset")
        return files
    except Exception:
        return [
            {"path": path, "download_url": f"{RAW_GITHUB_ROOT}/{path}"}
            for path in KNOWN_DATASET_PATHS
        ]


def sync_raw_files() -> list[Path]:
    local_paths: list[Path] = []
    for item in discover_dataset_files():
        relative = Path(*Path(item["path"]).parts[1:])
        target = RAW_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size > 0:
            local_paths.append(target)
            continue
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                tmp = target.with_suffix(target.suffix + ".tmp")
                tmp.write_bytes(_github_bytes(item["download_url"]))
                tmp.replace(target)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                time.sleep(2 * (attempt + 1))
        if last_error is not None:
            raise last_error
        local_paths.append(target)
    return local_paths


def _first_present(row: dict[str, Any], fields: list[str]) -> tuple[str | None, Any]:
    for field in fields:
        value = row.get(field)
        if not is_missing(value):
            return field, value
    return None, None


def _feedback_present(value: Any) -> bool:
    if is_missing(value):
        return False
    if isinstance(value, dict):
        return any(not is_missing(item) for item in value.values())
    return True


def iter_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            continue
        for index, row in enumerate(payload):
            if isinstance(row, dict):
                rows.append({"row": row, "file": str(path.relative_to(RAW_ROOT)), "index": index})
    return rows


def audit_rows(items: list[dict[str, Any]]) -> dict[str, Any]:
    counters = {
        "problem_text_direct": 0,
        "recoverable_question": 0,
        "student_solution_raw": 0,
        "teacher_feedback": 0,
        "error_type_or_reason": 0,
        "step_level_pilot_candidate": 0,
        "missing_question_but_matchable_id": 0,
        "fully_unrecoverable": 0,
    }
    recoverable_examples = []
    unusable_examples = []
    field_hits = {field: 0 for field in QUESTION_FIELDS + ID_FIELDS + STUDENT_FIELDS + FEEDBACK_FIELDS + ERROR_FIELDS}

    for item in items:
        row = item["row"]
        question_field, question_value = _first_present(row, QUESTION_FIELDS)
        id_field, id_value = _first_present(row, ID_FIELDS)
        student_field, student_value = _first_present(row, STUDENT_FIELDS)
        feedback_field, feedback_value = _first_present(row, FEEDBACK_FIELDS)
        error_field, error_value = _first_present(row, ERROR_FIELDS)

        for field in field_hits:
            if not is_missing(row.get(field)):
                field_hits[field] += 1

        has_direct_problem = not is_missing(row.get("problem_text"))
        has_recoverable_question = question_field is not None
        has_student_solution = student_field is not None
        has_feedback = feedback_field is not None and _feedback_present(feedback_value)
        has_error = error_field is not None
        has_matchable_id = id_field is not None
        step_count = len(split_steps(str(student_value))) if has_student_solution else 0
        is_step_candidate = has_recoverable_question and has_student_solution and step_count >= 2

        counters["problem_text_direct"] += int(has_direct_problem)
        counters["recoverable_question"] += int(has_recoverable_question)
        counters["student_solution_raw"] += int(has_student_solution)
        counters["teacher_feedback"] += int(has_feedback)
        counters["error_type_or_reason"] += int(has_error)
        counters["step_level_pilot_candidate"] += int(is_step_candidate)
        counters["missing_question_but_matchable_id"] += int((not has_recoverable_question) and has_matchable_id)
        counters["fully_unrecoverable"] += int((not has_recoverable_question) and (not has_matchable_id))

        example = {
            "source_file": item["file"],
            "row_index": item["index"],
            "id": row.get("id"),
            "question_field": question_field,
            "id_field": id_field,
            "student_field": student_field,
            "feedback_field": feedback_field,
            "error_field": error_field,
            "step_count_estimate": step_count,
            "sample": {
                "question_value": question_value,
                "id_value": id_value,
                "student_solution_raw": student_value,
                "teacher_feedback": feedback_value,
                "error_type_or_reason": error_value,
            },
        }
        if has_recoverable_question or has_matchable_id:
            if len(recoverable_examples) < 20:
                recoverable_examples.append(example)
        elif len(unusable_examples) < 20:
            unusable_examples.append(example)

    total = len(items)
    ratios = {
        name: round(count / total, 4) if total else 0.0
        for name, count in counters.items()
    }
    usable_ratio = ratios["recoverable_question"]
    if usable_ratio >= 0.5:
        decision = "candidate_for_phase3_pilot"
    elif usable_ratio >= 0.1:
        decision = "small_real_student_auxiliary_subset"
    else:
        decision = "exclude_from_phase3_pilot_keep_for_later_enhancement"
    return {
        "source": "mathedu",
        "raw_root": str(RAW_ROOT),
        "total_rows_scanned": total,
        "counts": counters,
        "ratios": ratios,
        "field_hits": field_hits,
        "decision_rule": {
            "candidate_for_phase3_pilot": "recoverable question ratio >= 0.50",
            "small_real_student_auxiliary_subset": "0.10 <= recoverable question ratio < 0.50",
            "exclude_from_phase3_pilot_keep_for_later_enhancement": "recoverable question ratio < 0.10",
        },
        "recommendation": decision,
        "notes": [
            "Audited local raw JSON synced from NYCU-NLP-Lab/MathEDU dataset directory.",
            "The field named id is counted as a matchable source row id, not as a recovered problem id.",
            "No problem text is inferred from student process or teacher feedback.",
        ],
        "recoverable_examples": recoverable_examples,
        "unusable_examples": unusable_examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit full local MathEDU raw data for question recoverability")
    parser.add_argument("--no-sync", action="store_true", help="audit existing data/raw/mathedu files only")
    args = parser.parse_args()

    paths = sorted(RAW_ROOT.rglob("*.json")) if args.no_sync else sync_raw_files()
    rows = iter_rows(paths)
    summary = audit_rows(rows)
    write_json(REPORT_DIR / "mathedu_full_audit.json", {k: v for k, v in summary.items() if not k.endswith("_examples")})
    write_jsonl(REPORT_DIR / "mathedu_recoverable_examples.jsonl", summary["recoverable_examples"])
    write_jsonl(REPORT_DIR / "mathedu_unusable_examples.jsonl", summary["unusable_examples"])
    print(
        "MathEDU audit:",
        summary["total_rows_scanned"],
        "rows, recommendation=",
        summary["recommendation"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
