from __future__ import annotations

import json
from typing import Any

from src.audit.common import AUDIT_DIR, AUDIT_V2_DIR, BLIND_PATH, MANIFEST_PATH, PRIVATE_PATH, leak_scan_blind_rows
from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_jsonl


def by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in rows}


def boundary_to_blind(row: dict[str, Any], sample_id: str) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "problem": {
            "problem_id": row["case_id"],
            "source": "boundary_cases_20",
            "source_split": "calibration",
            "problem_text": row["problem_sketch"],
            "reference_solution_steps": [],
            "gold_answer": None,
            "topic": row.get("coverage"),
            "difficulty": None,
        },
        "student_trace": {
            "trace_id": sample_id,
            "trace_source": "calibration_boundary_case",
            "student_steps": [{"step_id": index + 1, "text": text} for index, text in enumerate(row["student_steps"])],
            "student_final_answer": None,
            "is_correct": None,
        },
        "reference_solution_steps": [],
        "gold_answer": None,
        "source": "boundary_cases_20",
    }


def sample_to_blind(row: dict[str, Any]) -> dict[str, Any]:
    problem = row["problem"]
    return {
        "sample_id": row["sample_id"],
        "problem": problem,
        "student_trace": row["student_trace"],
        "reference_solution_steps": problem.get("reference_solution_steps", []),
        "gold_answer": problem.get("gold_answer"),
        "source": problem.get("source"),
    }


def sample_to_private(row: dict[str, Any], manifest_item: dict[str, Any]) -> dict[str, Any]:
    synthetic = row.get("synthetic_metadata") or {}
    label = row.get("pedagogical_labels") or {}
    existing = row.get("existing_labels") or {}
    return {
        "sample_id": row["sample_id"],
        "source": row["problem"]["source"],
        "audit_subset": manifest_item["audit_subset"],
        "included_in_metrics": manifest_item["included_in_metrics"],
        "strict_status": manifest_item["strict_status"],
        "synthetic_type": synthetic.get("synthetic_type"),
        "injected_error_step": synthetic.get("injected_error_step"),
        "injected_error_type": synthetic.get("injected_error_type"),
        "expected_first_wrong_step": synthetic.get("expected_first_wrong_step"),
        "expected_earliest_actionable_step": synthetic.get("expected_earliest_actionable_step"),
        "expected_intervention_needed": synthetic.get("expected_intervention_needed"),
        "expected_minimal_repair_type": synthetic.get("expected_minimal_repair_type"),
        "expected_hint_level": synthetic.get("expected_hint_level"),
        "expected_leakage_constraint": synthetic.get("expected_leakage_constraint"),
        "deepseek_first_pass_first_wrong_step": existing.get("first_wrong_step"),
        "deepseek_first_pass_earliest_actionable_step": label.get("earliest_actionable_step"),
        "deepseek_first_pass_intervention_needed": label.get("intervention_needed"),
        "deepseek_first_pass_minimal_repair_type": label.get("minimal_repair_type"),
        "deepseek_first_pass_hint_level": label.get("hint_level"),
        "deepseek_first_pass_leakage_constraint": label.get("leakage_constraint"),
    }


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["items"]
    raw = by_id(read_jsonl_file(PILOT_DIR / "deepseek_synthetic_240.raw.jsonl"))
    autolabeled = by_id(read_jsonl_file(PILOT_DIR / "deepseek_synthetic_240.autolabeled.jsonl"))
    stepverify = by_id(read_jsonl_file(PILOT_DIR / "pilot_pool.raw.jsonl"))
    boundary = {row["case_id"]: row for row in read_jsonl_file(REPORT_DIR / "boundary_cases_20.jsonl")}

    blind_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for item in manifest:
        sample_id = item["sample_id"]
        if item["audit_subset"] == "calibration_boundary_case":
            case = boundary[item["boundary_case_id"]]
            blind_rows.append(boundary_to_blind(case, sample_id))
            private_rows.append({
                "sample_id": sample_id,
                "source": "boundary_cases_20",
                "audit_subset": item["audit_subset"],
                "included_in_metrics": False,
                "strict_status": "not_applicable",
                "boundary_case_id": case["case_id"],
                "expected_first_wrong_step": case["first_wrong_step"],
                "expected_earliest_actionable_step": case["earliest_actionable_step"],
                "expected_intervention_needed": case["intervention_needed"],
                "expected_minimal_repair_type": case["minimal_repair_type"],
                "expected_hint_level": case["hint_level"],
                "expected_leakage_constraint": case["leakage_constraint"],
            })
        elif item["audit_subset"] == "stepverify_raw":
            row = stepverify[sample_id]
            blind_rows.append(sample_to_blind(row))
            private_rows.append({
                "sample_id": sample_id,
                "source": "stepverify",
                "audit_subset": item["audit_subset"],
                "included_in_metrics": True,
                "strict_status": "not_applicable",
                "stepverify_first_wrong_step": row["existing_labels"].get("first_wrong_step"),
                "stepverify_error_category": row["existing_labels"].get("error_category"),
            })
        else:
            row = raw[sample_id]
            blind_rows.append(sample_to_blind(row))
            labeled_row = autolabeled[sample_id]
            private_rows.append(sample_to_private(labeled_row, item))

    leak_scan_blind_rows(blind_rows)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(BLIND_PATH, blind_rows)
    write_jsonl(PRIVATE_PATH, private_rows)
    AUDIT_V2_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(AUDIT_V2_DIR / "audit_60_blind.jsonl", blind_rows)
    write_jsonl(AUDIT_V2_DIR / "audit_60_analysis_private.jsonl", private_rows)
    print(json.dumps({"blind_rows": len(blind_rows), "private_rows": len(private_rows), "leakage_scan": "passed"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
