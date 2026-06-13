from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.audit.common import leak_scan_blind_rows
from src.data.common import DATA_DIR, REPORT_DIR, read_jsonl_file, write_json, write_jsonl

MANUAL_DIR = DATA_DIR / "manual"
SEED = 20260613
CALIBRATION_COUNT = 8
TARGET_SYNTHETIC_TYPES = {
    "sign_error": 2,
    "equation_setup_error": 2,
    "no_error_correct_trace": 2,
    "final_answer_correct_process_wrong": 2,
    "final_answer_wrong_prefix_correct": 2,
    "unit_conversion_error": 1,
    "sparse_insufficient_trace": 3,
    "hint_would_leak_answer": 2,
}

BLIND_OUT = MANUAL_DIR / "phase3_17_human_pack_24.blind.jsonl"
TEMPLATE_JSONL_OUT = MANUAL_DIR / "phase3_17_human_template_24.jsonl"
TEMPLATE_CSV_OUT = MANUAL_DIR / "phase3_17_human_template_24.csv"
LABELS_OUT = MANUAL_DIR / "phase3_17_human_labels_24.jsonl"
MANIFEST_OUT = MANUAL_DIR / "phase3_17_human_manifest.json"
PRIVATE_OUT = MANUAL_DIR / "phase3_17_human_analysis_private.jsonl"
SUMMARY_OUT = REPORT_DIR / "phase3_17_human_pack_summary.json"


def by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in rows}


def boundary_to_blind(row: dict[str, Any], sample_id: str) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "problem": {
            "problem_id": sample_id,
            "source": "manual_review",
            "source_split": "review",
            "problem_text": row["problem_sketch"],
            "reference_solution_steps": [],
            "gold_answer": None,
            "topic": None,
            "difficulty": None,
        },
        "student_trace": {
            "trace_id": sample_id,
            "trace_source": "student_trace",
            "student_steps": [{"step_id": index + 1, "text": text} for index, text in enumerate(row["student_steps"])],
            "student_final_answer": None,
            "is_correct": None,
        },
        "reference_solution_steps": [],
        "gold_answer": None,
        "source": "manual_review",
    }


def template_row(sample_id: str) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "reviewer_id": "",
        "first_wrong_step": None,
        "intervention_needed": "",
        "minimal_repair_coarse_6": "",
        "hint_level_coarse_3": "",
        "trace_validity_for_intended_type": "",
        "rationale": "",
        "earliest_actionable_step_optional": None,
        "leakage_risk_binary": None,
    }


def csv_row(blind: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    steps = blind["student_trace"].get("student_steps", [])
    step_text = "\n".join(f"{step.get('step_id')}. {step.get('text')}" for step in steps)
    row = {
        "sample_id": blind["sample_id"],
        "problem_text": blind.get("problem", {}).get("problem_text"),
        "student_steps": step_text,
        "student_final_answer": blind.get("student_trace", {}).get("student_final_answer"),
        "gold_answer": blind.get("gold_answer"),
        **template,
    }
    row["sample_id"] = blind["sample_id"]
    return row


def choose_core_samples(private_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in private_rows:
        if not row.get("included_in_metrics"):
            continue
        if row.get("source") == "stepverify":
            continue
        synthetic_type = row.get("synthetic_type")
        if synthetic_type in TARGET_SYNTHETIC_TYPES:
            buckets[synthetic_type].append(row)
    selected: list[dict[str, Any]] = []
    for synthetic_type, count in TARGET_SYNTHETIC_TYPES.items():
        candidates = sorted(buckets.get(synthetic_type, []), key=lambda item: item["sample_id"])
        rng.shuffle(candidates)
        if len(candidates) < count:
            raise ValueError(f"not enough rows for {synthetic_type}: need {count}, have {len(candidates)}")
        selected.extend(candidates[:count])
    selected.sort(key=lambda row: (list(TARGET_SYNTHETIC_TYPES).index(row["synthetic_type"]), row["sample_id"]))
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 3.17 human repair-taxonomy review pack")
    parser.add_argument("--blind", default=str(DATA_DIR / "audit" / "audit_60_blind.jsonl"))
    parser.add_argument("--private", default=str(DATA_DIR / "audit" / "audit_60_analysis_private.jsonl"))
    parser.add_argument("--boundary", default=str(REPORT_DIR / "boundary_cases_20.jsonl"))
    args = parser.parse_args()

    blind_by_id = by_id(read_jsonl_file(Path(args.blind)))
    private_rows = read_jsonl_file(Path(args.private))
    boundary_rows = read_jsonl_file(Path(args.boundary))

    calibration_blind: list[dict[str, Any]] = []
    calibration_private: list[dict[str, Any]] = []
    visible_index = 1
    for row in boundary_rows[:CALIBRATION_COUNT]:
        sample_id = f"phase3_17_{visible_index:03d}"
        visible_index += 1
        calibration_blind.append(boundary_to_blind(row, sample_id))
        calibration_private.append(
            {
                "sample_id": sample_id,
                "original_sample_id": row["case_id"],
                "review_group": "calibration",
                "boundary_case_id": row["case_id"],
                "coverage": row.get("coverage"),
                "expected_first_wrong_step": row.get("first_wrong_step"),
                "expected_intervention_needed": row.get("intervention_needed"),
                "expected_minimal_repair_type": row.get("minimal_repair_type"),
                "expected_hint_level": row.get("hint_level"),
                "expected_rationale": row.get("reason"),
            }
        )

    core_private = choose_core_samples(private_rows)
    core_blind: list[dict[str, Any]] = []
    remapped_core_private = []
    for row in core_private:
        sample_id = f"phase3_17_{visible_index:03d}"
        visible_index += 1
        blind = json.loads(json.dumps(blind_by_id[row["sample_id"]], ensure_ascii=False))
        original_sample_id = blind["sample_id"]
        blind["sample_id"] = sample_id
        blind["student_trace"]["trace_id"] = sample_id
        blind["student_trace"]["trace_source"] = "student_trace"
        core_blind.append(blind)
        private_row = dict(row)
        private_row["sample_id"] = sample_id
        private_row["original_sample_id"] = original_sample_id
        private_row["review_group"] = "core_synthetic"
        remapped_core_private.append(private_row)

    blind_rows = [*calibration_blind, *core_blind]
    leak_scan_blind_rows(blind_rows)
    template_rows = [template_row(row["sample_id"]) for row in blind_rows]

    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(BLIND_OUT, blind_rows)
    write_jsonl(TEMPLATE_JSONL_OUT, template_rows)
    LABELS_OUT.write_text("", encoding="utf-8")
    write_jsonl(PRIVATE_OUT, [*calibration_private, *remapped_core_private])

    csv_rows = [csv_row(blind, template) for blind, template in zip(blind_rows, template_rows)]
    with TEMPLATE_CSV_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    manifest = {
        "phase": "3.17",
        "name": "repair_taxonomy_human_check_24",
        "sampling_seed": SEED,
        "total_count": len(blind_rows),
        "calibration_count": len(calibration_blind),
        "core_count": len(core_blind),
        "teacher_visible_files": [
            str(BLIND_OUT.relative_to(DATA_DIR.parent)),
            str(TEMPLATE_JSONL_OUT.relative_to(DATA_DIR.parent)),
            str(TEMPLATE_CSV_OUT.relative_to(DATA_DIR.parent)),
        ],
        "private_do_not_send_to_teacher": [
            str(PRIVATE_OUT.relative_to(DATA_DIR.parent)),
            str(MANIFEST_OUT.relative_to(DATA_DIR.parent)),
        ],
        "core_synthetic_type_targets": TARGET_SYNTHETIC_TYPES,
        "core_synthetic_type_distribution": dict(Counter(row["synthetic_type"] for row in remapped_core_private)),
        "reviewer_instructions": [
            "Do not use hidden expected labels, synthetic_type, DeepSeek labels, or proxy adjudicated labels during review.",
            "Fill phase3_17_human_template_24.csv or convert it to phase3_17_human_labels_24.jsonl.",
            "Use 6-class minimal_repair_coarse_6 as the main repair label.",
            "Treat earliest_actionable_step_optional and leakage_risk_binary as optional diagnostics.",
        ],
    }
    write_json(MANIFEST_OUT, manifest)
    write_json(SUMMARY_OUT, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
