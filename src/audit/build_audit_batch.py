from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from typing import Any

from src.audit.common import AUDIT_DIR, AUDIT_V2_DIR, MANIFEST_PATH, all_expected_match, compare_expected
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


SEED = 20260609


def stratified_pick(rows: list[dict[str, Any]], count: int, key_fn, *, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(key_fn(row))].append(row)
    for bucket_rows in buckets.values():
        bucket_rows.sort(key=lambda row: row["sample_id"])
        rng.shuffle(bucket_rows)
    selected: list[dict[str, Any]] = []
    keys = sorted(buckets)
    while len(selected) < count and any(buckets.values()):
        for key in keys:
            if buckets[key] and len(selected) < count:
                selected.append(buckets[key].pop(0))
    if len(selected) < count:
        raise ValueError(f"not enough rows: need {count}, have {len(selected)}")
    return selected


def pick(rows: list[dict[str, Any]], count: int, *, seed: int = SEED) -> list[dict[str, Any]]:
    rows = list(rows)
    rows.sort(key=lambda row: row["sample_id"])
    random.Random(seed).shuffle(rows)
    if len(rows) < count:
        raise ValueError(f"not enough rows: need {count}, have {len(rows)}")
    return rows[:count]


def mismatch_field(row: dict[str, Any], autolabeled: dict[str, dict[str, Any]]) -> str:
    checks = compare_expected(row, autolabeled[row["sample_id"]])
    for field, ok in checks.items():
        if not ok:
            return field
    return "none"


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
    selected.extend(
        (row, "strict_pass_expected_match", "passed")
        for row in stratified_pick(pass_match, 12, lambda row: row["synthetic_metadata"].get("synthetic_type"))
    )
    selected.extend(
        (row, "strict_pass_expected_mismatch", "passed")
        for row in stratified_pick(pass_mismatch, 18, lambda row: mismatch_field(row, autolabeled))
    )
    selected.extend(
        (row, "strict_failed_hard_types", "failed")
        for row in stratified_pick(failed_hard, 15, lambda row: row["synthetic_metadata"].get("synthetic_type"))
    )
    selected.extend((row, "strict_failed_random_types", "failed") for row in pick(failed_random, 5))
    selected.extend((row, "stepverify_raw", "not_applicable") for row in stratified_pick(stepverify, 10, lambda row: row["existing_labels"].get("error_category")))

    items = [manifest_item(row, subset, strict_status) for row, subset, strict_status in selected]
    items.extend(boundary_to_manifest_item(row, index) for index, row in enumerate(boundary[:8]))
    metric_count = sum(1 for item in items if item["included_in_metrics"])
    calibration_count = len(items) - metric_count
    subset_distribution = Counter(item["audit_subset"] for item in items)
    payload = {
        "audit_name": "proxy_human_audit_60",
        "audit_version": "v2",
        "sampling_seed": SEED,
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
    AUDIT_V2_DIR.mkdir(parents=True, exist_ok=True)
    write_json(AUDIT_V2_DIR / "audit_60_manifest.json", payload)
    selected_rows = [row for row, _, _ in selected]
    sampling_report = {
        "audit_version": "v2",
        "sampling_seed": SEED,
        "synthetic_type_distribution": dict(Counter((row.get("synthetic_metadata") or {}).get("synthetic_type") for row in selected_rows if row.get("synthetic_metadata"))),
        "strict_status_distribution": dict(Counter(item["strict_status"] for item in items)),
        "expected_match_mismatch_distribution": dict(Counter(item["audit_subset"] for item in items if item["audit_subset"].startswith("strict_pass_expected"))),
        "source_distribution": dict(Counter(item["source"] for item in items)),
        "subset_distribution": dict(subset_distribution),
    }
    write_json(REPORT_DIR / "audit_60_sampling_report.json", sampling_report)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
