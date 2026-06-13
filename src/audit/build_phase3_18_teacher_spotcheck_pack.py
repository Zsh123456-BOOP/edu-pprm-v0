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
TARGET_COUNT = 24


def blind_row(sample: dict[str, Any], visible_id: str) -> dict[str, Any]:
    return {
        "sample_id": visible_id,
        "problem": sample["problem"],
        "student_trace": {
            **sample["student_trace"],
            "trace_id": visible_id,
            "trace_source": "student_trace",
        },
        "reference_solution_steps": sample["problem"]["reference_solution_steps"],
        "gold_answer": sample["problem"]["gold_answer"],
        "source": sample["problem"]["source"],
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
    steps = "\n".join(f"{step['step_id']}. {step['text']}" for step in blind["student_trace"]["student_steps"])
    row = {
        "sample_id": blind["sample_id"],
        "problem_text": blind["problem"]["problem_text"],
        "student_steps": steps,
        "student_final_answer": blind["student_trace"].get("student_final_answer"),
        "gold_answer": blind.get("gold_answer"),
        **template,
    }
    row["sample_id"] = blind["sample_id"]
    return row


def select_samples(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row["synthetic_metadata"]["synthetic_type"]].append(row)
    selected: list[dict[str, Any]] = []
    types = sorted(buckets)
    per_type = max(1, count // len(types))
    for synthetic_type in types:
        candidates = sorted(buckets[synthetic_type], key=lambda item: item["sample_id"])
        rng.shuffle(candidates)
        selected.extend(candidates[:per_type])
    leftovers = [row for row in rows if row not in selected]
    rng.shuffle(leftovers)
    selected.extend(leftovers[: max(0, count - len(selected))])
    return sorted(selected[:count], key=lambda item: item["sample_id"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 3.18 teacher spot-check pack")
    parser.add_argument("--input", type=Path, default=DATA_DIR / "pilot" / "synthetic_v2_150.autolabeled.jsonl")
    parser.add_argument("--count", type=int, default=TARGET_COUNT)
    args = parser.parse_args()
    samples = read_jsonl_file(args.input)
    selected = select_samples(samples, args.count)
    blind_rows = []
    private_rows = []
    for index, sample in enumerate(selected, start=1):
        visible_id = f"phase3_18_{index:03d}"
        blind_rows.append(blind_row(sample, visible_id))
        private_rows.append(
            {
                "sample_id": visible_id,
                "original_sample_id": sample["sample_id"],
                "synthetic_type": sample["synthetic_metadata"]["synthetic_type"],
                "expected_first_wrong_step": sample["synthetic_metadata"].get("expected_first_wrong_step"),
                "expected_intervention_needed": sample["synthetic_metadata"].get("expected_intervention_needed"),
                "expected_minimal_repair_type": sample["synthetic_metadata"].get("expected_minimal_repair_type"),
                "expected_minimal_repair_coarse_6": sample["synthetic_metadata"].get("expected_minimal_repair_coarse_6"),
                "deepseek_first_wrong_step": sample["existing_labels"].get("first_wrong_step"),
                "deepseek_intervention_needed": sample["pedagogical_labels"].get("intervention_needed"),
                "deepseek_minimal_repair_type": sample["pedagogical_labels"].get("minimal_repair_type"),
            }
        )
    leak_scan_blind_rows(blind_rows)
    template_rows = [template_row(row["sample_id"]) for row in blind_rows]
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    blind_path = MANUAL_DIR / "phase3_18_teacher_spotcheck_24.blind.jsonl"
    template_jsonl = MANUAL_DIR / "phase3_18_teacher_spotcheck_24.template.jsonl"
    template_csv = MANUAL_DIR / "phase3_18_teacher_spotcheck_24.template.csv"
    private_path = MANUAL_DIR / "phase3_18_teacher_spotcheck_24.private.jsonl"
    write_jsonl(blind_path, blind_rows)
    write_jsonl(template_jsonl, template_rows)
    write_jsonl(private_path, private_rows)
    csv_rows = [csv_row(blind, template) for blind, template in zip(blind_rows, template_rows)]
    with template_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    summary = {
        "phase": "3.18",
        "count": len(selected),
        "sampling_seed": SEED,
        "teacher_visible_files": [
            str(blind_path),
            str(template_csv),
            str(template_jsonl),
        ],
        "private_do_not_send_to_teacher": [str(private_path)],
        "synthetic_type_distribution": dict(Counter(row["synthetic_type"] for row in private_rows)),
    }
    write_json(REPORT_DIR / "phase3_18_teacher_spotcheck_pack_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
