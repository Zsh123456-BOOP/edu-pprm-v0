from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, ROOT, read_jsonl_file, write_json, write_jsonl
from src.data.load_gsm8k import load as load_gsm8k
from src.data.load_math import load as load_math
from src.data.validate_schema import _reserved, validate_sample
from src.synthetic.inject_math_errors import SYNTHETIC_TYPES, inject_trace
from src.synthetic.verify_synthetic_steps import verify_synthetic_sample


def _step_objects(texts: list[str]) -> list[dict[str, Any]]:
    return [{"step_id": index + 1, "text": text} for index, text in enumerate(texts)]


def make_sample(row: dict[str, Any], source: str, index: int, synthetic_type: str) -> dict[str, Any]:
    injection = inject_trace(row, synthetic_type)
    sample = {
        "sample_id": f"pilot_{source}_synthetic_{index:04d}",
        "problem": {
            "problem_id": row.get("problem_id"),
            "source": source,
            "source_split": row.get("source_split"),
            "problem_text": row.get("problem_text"),
            "reference_solution_steps": _step_objects(row.get("gold_solution_steps", [])),
            "gold_answer": row.get("gold_answer"),
            "topic": row.get("topic"),
            "difficulty": row.get("difficulty"),
        },
        "student_trace": {
            "trace_id": f"trace_{source}_synthetic_{index:04d}",
            "trace_source": "synthetic_rule",
            "student_steps": _step_objects(injection.student_steps),
            "student_final_answer": str(row.get("gold_answer")) if injection.synthetic_type in {"no_error_correct_trace", "final_answer_correct_process_wrong"} else None,
            "is_correct": injection.synthetic_type in {"no_error_correct_trace", "self_corrected_error", "final_answer_correct_process_wrong"},
        },
        "existing_labels": {
            "first_wrong_step": None,
            "error_category": injection.injected_error_type,
            "error_description": f"Known synthetic case: {injection.synthetic_type}",
            "teacher_feedback": None,
        },
        "pedagogical_labels": {
            "intervention_needed": None,
            "earliest_actionable_step": None,
            "minimal_repair_type": None,
            "repair_target": None,
            "hint_level": None,
            "leakage_constraint": None,
            "actionable_diff_reason": None,
        },
        "label_metadata": {
            "quality_tier": "raw",
            "label_source": "auto",
            "annotator_ids": [],
            "adjudication_status": "none",
            "excluded_reason": None,
            "confidence": None,
            "short_rationale": None,
            "model_name": None,
            "raw_label_response_id": None,
        },
        "reserved": _reserved(),
        "synthetic_metadata": {
            "synthetic_type": injection.synthetic_type,
            "injected_error_step": injection.injected_error_step,
            "injected_error_type": injection.injected_error_type,
            "expected_first_wrong_step": injection.expected_first_wrong_step,
            "expected_earliest_actionable_step": injection.expected_earliest_actionable_step,
            "expected_intervention_needed": injection.expected_intervention_needed,
            "expected_minimal_repair_type": injection.expected_minimal_repair_type,
            "expected_hint_level": injection.expected_hint_level,
            "expected_leakage_constraint": injection.expected_leakage_constraint,
            "generation_method": "deterministic_rule_template_v1",
            "verification_status": "pending",
            "parent_problem_id": row.get("problem_id"),
            "repair_target": injection.repair_target,
        },
    }
    status, reason = verify_synthetic_sample(sample)
    sample["synthetic_metadata"]["verification_status"] = status
    if reason:
        sample["synthetic_metadata"]["verification_error"] = reason
    return sample


def build_synthetic(gsm8k_count: int = 80, math_count: int = 40) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gsm8k_rows = read_jsonl_file(ROOT / "data" / "interim" / "gsm8k.problem_bank.raw.jsonl")
    if len(gsm8k_rows) < gsm8k_count:
        gsm8k_rows = load_gsm8k(gsm8k_count)
    math_rows = read_jsonl_file(ROOT / "data" / "interim" / "math.problem_bank.raw.jsonl")
    if len(math_rows) < math_count:
        math_rows = load_math(math_count)
    samples: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for source, rows, count in [("gsm8k", gsm8k_rows, gsm8k_count), ("math", math_rows, math_count)]:
        for index in range(count):
            row = rows[index % len(rows)]
            synthetic_type = SYNTHETIC_TYPES[index % len(SYNTHETIC_TYPES)]
            sample = make_sample(row, source, index, synthetic_type)
            if sample["synthetic_metadata"]["verification_status"] == "passed":
                validate_sample(sample)
                samples.append(sample)
            else:
                failures.append(sample)
    return samples, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic pilot traces")
    parser.add_argument("--gsm8k-count", type=int, default=80)
    parser.add_argument("--math-count", type=int, default=40)
    args = parser.parse_args()
    samples, failures = build_synthetic(args.gsm8k_count, args.math_count)
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(PILOT_DIR / "synthetic_pilot.raw.jsonl", samples)
    write_jsonl(REPORT_DIR / "synthetic_pilot_40_examples.jsonl", samples[:40])
    write_jsonl(REPORT_DIR / "synthetic_generation_failures.jsonl", failures)
    type_counts = Counter(sample["synthetic_metadata"]["synthetic_type"] for sample in samples)
    summary = {
        "total_count": len(samples),
        "failure_count": len(failures),
        "source_distribution": Counter(sample["problem"]["source"] for sample in samples),
        "synthetic_type_distribution": dict(type_counts),
        "min_per_type": min(type_counts.values()) if type_counts else 0,
        "verification_failed_included": 0,
    }
    write_json(REPORT_DIR / "synthetic_pilot_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if len(samples) == args.gsm8k_count + args.math_count and all(v >= 5 for v in type_counts.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
