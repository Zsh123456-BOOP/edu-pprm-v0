from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.audit.common import AUDIT_DIR, MANIFEST_PATH, all_expected_match
from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_json

HARD_TYPES = {
    "final_answer_correct_process_wrong",
    "hint_would_leak_answer",
    "equation_setup_error",
    "sign_error",
    "sparse_insufficient_trace",
}


def by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in rows}


def pick(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda row: row["sample_id"])
    if len(rows) < count:
        raise ValueError(f"not enough rows: need {count}, have {len(rows)}")
    return rows[:count]


def manifest_item(row: dict[str, Any], subset: str, strict_status: str, included: bool = True) -> dict[str, Any]:
    return {
        "sample_id": row["sample_id"],
        "audit_subset": subset,
        "source": row.get("problem", {}).get("source") or row.get("source"),
        "strict_status": strict_status,
        "included_in_metrics": included,
    }


def boundary_to_manifest_item(row: dict[str, Any], index: int) -> dict[str, Any]:
    sample_id = f"calibration_{index + 1:02d}_{row['case_id']}"
    return {
        "sample_id": sample_id,
        "audit_subset": "calibration_boundary_case",
        "source": "boundary_cases_20",
        "strict_status": "not_applicable",
        "included_in_metrics": False,
        "boundary_case_id": row["case_id"],
    }


def main() -> int:
    raw = by_id(read_jsonl_file(PILOT_DIR / "deepseek_synthetic_240.raw.jsonl"))
    verified_ids = set(by_id(read_jsonl_file(PILOT_DIR / "deepseek_synthetic_240.verified.raw.jsonl")))
    autolabeled = by_id(read_jsonl_file(PILOT_DIR / "deepseek_synthetic_240.autolabeled.jsonl"))
    stepverify = [
        row for row in read_jsonl_file(PILOT_DIR / "pilot_pool.raw.jsonl")
        if row.get("problem", {}).get("source") == "stepverify"
    ]
    boundary = read_jsonl_file(REPORT_DIR / "boundary_cases_20.jsonl")

    strict_pass = [row for sid, row in raw.items() if sid in verified_ids]
    strict_failed = [row for sid, row in raw.items() if sid not in verified_ids]
    pass_match = [row for row in strict_pass if all_expected_match(row, autolabeled[row["sample_id"]])]
    pass_mismatch = [row for row in strict_pass if not all_expected_match(row, autolabeled[row["sample_id"]])]
    failed_hard = [row for row in strict_failed if row["synthetic_metadata"].get("synthetic_type") in HARD_TYPES]
    failed_random = [row for row in strict_failed if row["synthetic_metadata"].get("synthetic_type") not in HARD_TYPES]

    selected = []
    selected.extend((row, "strict_pass_label_expected_match", "passed") for row in pick(pass_match, 12))
    selected.extend((row, "strict_pass_label_expected_mismatch", "passed") for row in pick(pass_mismatch, 18))
    selected.extend((row, "strict_failed_hard_types", "failed") for row in pick(failed_hard, 15))
    selected.extend((row, "strict_failed_random_types", "failed") for row in pick(failed_random, 5))
    selected.extend((row, "stepverify_raw", "not_applicable") for row in pick(stepverify, 10))

    items = [manifest_item(row, subset, strict_status) for row, subset, strict_status in selected]
    items.extend(boundary_to_manifest_item(row, index) for index, row in enumerate(boundary[:8]))
    metric_count = sum(1 for item in items if item["included_in_metrics"])
    calibration_count = len(items) - metric_count
    subset_distribution = Counter(item["audit_subset"] for item in items)
    payload = {
        "audit_name": "proxy_human_audit_60",
        "label_set_name": "ai_adjudicated_gold_candidate",
        "note": "Proxy audit only. These are not human gold labels.",
        "metric_count": metric_count,
        "calibration_count": calibration_count,
        "total_count": len(items),
        "subset_distribution": dict(subset_distribution),
        "items": items,
    }
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(MANIFEST_PATH, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
