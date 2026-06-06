from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_json, write_jsonl


def build_inputs(path: Path) -> list[dict]:
    rows = read_jsonl_file(path)
    stepverify = [row for row in rows if row["problem"]["source"] == "stepverify"][:30]
    synthetic = [row for row in rows if row.get("synthetic_metadata")][:30]
    selected = stepverify + synthetic
    inputs = []
    for row in selected:
        base = {
            "sample_id": row["sample_id"],
            "problem_text": row["problem"]["problem_text"],
            "student_steps": row["student_trace"]["student_steps"],
            "gold_answer": row["problem"].get("gold_answer"),
            "generation_config": {"model": "deepseek-v4-pro", "temperature": 0.0, "max_tokens": 180},
        }
        inputs.append(
            {
                **base,
                "condition": "T2",
                "first_wrong_step": row["existing_labels"]["first_wrong_step"],
                "error_description": row["existing_labels"]["error_description"],
            }
        )
        inputs.append(
            {
                **base,
                "condition": "T3",
                "first_wrong_step": row["existing_labels"]["first_wrong_step"],
                "earliest_actionable_step": row["pedagogical_labels"]["earliest_actionable_step"],
                "intervention_needed": row["pedagogical_labels"]["intervention_needed"],
                "minimal_repair_type": row["pedagogical_labels"]["minimal_repair_type"],
                "repair_target": row["pedagogical_labels"]["repair_target"],
                "hint_level": row["pedagogical_labels"]["hint_level"],
                "leakage_constraint": row["pedagogical_labels"]["leakage_constraint"],
            }
        )
    return inputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Build T2/T3 tutor auto input pairs")
    parser.add_argument("--input", type=Path, default=PILOT_DIR / "pilot_pool.autolabeled.jsonl")
    args = parser.parse_args()
    inputs = build_inputs(args.input)
    write_jsonl(REPORT_DIR / "tutor_auto_inputs.jsonl", inputs)
    write_json(REPORT_DIR / "tutor_generation_config.json", {"conditions": ["T2", "T3"], "sample_pairs": len(inputs) // 2, "model": "deepseek-v4-pro", "temperature": 0.0, "max_tokens": 180})
    print(len(inputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
