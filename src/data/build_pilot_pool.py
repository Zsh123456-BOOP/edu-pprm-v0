from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, split_steps, write_json, write_jsonl
from src.data.load_stepverify import load as load_stepverify
from src.data.validate_schema import _reserved, validate_sample
from src.synthetic.generate_pilot_synthetic import build_synthetic


def _step_objects(texts: list[Any]) -> list[dict[str, Any]]:
    return [{"step_id": index + 1, "text": None if text is None else str(text)} for index, text in enumerate(texts)]


def _reference_steps(text: str | None) -> list[dict[str, Any]]:
    return _step_objects(split_steps(text))


def _stepverify_schema(row: dict[str, Any], index: int) -> dict[str, Any]:
    student_raw = row.get("student_solution_raw")
    student_steps = student_raw if isinstance(student_raw, list) else split_steps(student_raw)
    source_first_wrong = row.get("first_wrong_step_source")
    first_wrong = source_first_wrong + 1 if isinstance(source_first_wrong, int) else source_first_wrong
    sample = {
        "sample_id": f"pilot_stepverify_{index:04d}",
        "problem": {
            "problem_id": row.get("source_id"),
            "source": "stepverify",
            "source_split": "train",
            "problem_text": row.get("problem_text"),
            "reference_solution_steps": _reference_steps(row.get("reference_solution_raw")),
            "gold_answer": None,
            "topic": row.get("metadata", {}).get("topic"),
            "difficulty": None,
        },
        "student_trace": {
            "trace_id": row.get("source_id"),
            "trace_source": "stepverify",
            "student_steps": _step_objects(student_steps),
            "student_final_answer": str(student_steps[-1]) if student_steps else None,
            "is_correct": False,
        },
        "existing_labels": {
            "first_wrong_step": first_wrong,
            "error_category": row.get("error_category_source"),
            "error_description": row.get("error_description_source"),
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
            "label_source": "converted",
            "annotator_ids": [],
            "adjudication_status": "none",
            "excluded_reason": None,
            "confidence": None,
            "short_rationale": None,
            "model_name": None,
            "raw_label_response_id": None,
        },
        "reserved": _reserved(),
        "synthetic_metadata": None,
    }
    validate_sample(sample)
    return sample


def stratified_stepverify(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, Any, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        student_raw = row.get("student_solution_raw")
        length = len(student_raw) if isinstance(student_raw, list) else len(split_steps(student_raw))
        length_bucket = "short" if length <= 3 else "medium" if length <= 6 else "long"
        key = (row.get("error_category_source"), row.get("first_wrong_step_source"), length_bucket)
        buckets[key].append(row)
    selected = []
    while len(selected) < count and buckets:
        for key in sorted(list(buckets), key=lambda item: str(item)):
            if buckets[key]:
                selected.append(buckets[key].pop(0))
                if len(selected) >= count:
                    break
            if not buckets.get(key):
                buckets.pop(key, None)
    return selected


def build_pilot_pool(stepverify_count: int = 120, gsm8k_count: int = 80, math_count: int = 40) -> list[dict[str, Any]]:
    stepverify_raw = load_stepverify(max(stepverify_count, 140))
    stepverify_selected = stratified_stepverify(stepverify_raw, stepverify_count)
    stepverify_samples = [_stepverify_schema(row, index) for index, row in enumerate(stepverify_selected)]
    synthetic_samples, failures = build_synthetic(gsm8k_count, math_count)
    if failures:
        write_jsonl(REPORT_DIR / "synthetic_generation_failures.jsonl", failures)
    samples = stepverify_samples + synthetic_samples
    for sample in samples:
        validate_sample(sample)
    return samples


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    first_wrong = Counter(str(sample["existing_labels"]["first_wrong_step"]) for sample in samples if sample["existing_labels"]["first_wrong_step"] is not None)
    for sample in samples:
        meta = sample.get("synthetic_metadata")
        if meta:
            first_wrong[str(meta.get("expected_first_wrong_step"))] += 1
    step_counts = [len(sample["student_trace"]["student_steps"]) for sample in samples]
    return {
        "total_count": len(samples),
        "source_distribution": dict(Counter(sample["problem"]["source"] for sample in samples)),
        "first_wrong_step_distribution": dict(first_wrong),
        "error_category_distribution": dict(Counter(sample["existing_labels"]["error_category"] for sample in samples)),
        "avg_student_step_count": round(mean(step_counts), 3) if step_counts else 0,
        "excluded_source_reason_summary": {
            "mathedu": "excluded: full audit found 0% recoverable question/problem text",
            "prm800k": "excluded: baseline/pretrain only, no pedagogical repair labels",
            "processbench": "excluded: external eval only",
            "handwrite": "excluded: out of scope and no text process labels",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Edu-PPRM auto-silver pilot raw pool")
    parser.add_argument("--stepverify-count", type=int, default=120)
    parser.add_argument("--gsm8k-count", type=int, default=80)
    parser.add_argument("--math-count", type=int, default=40)
    args = parser.parse_args()
    samples = build_pilot_pool(args.stepverify_count, args.gsm8k_count, args.math_count)
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(PILOT_DIR / "pilot_pool.raw.jsonl", samples)
    write_jsonl(REPORT_DIR / "pilot_pool_30_examples.jsonl", samples[:30])
    summary = summarize(samples)
    write_json(REPORT_DIR / "pilot_pool_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    expected = args.stepverify_count + args.gsm8k_count + args.math_count
    return 0 if len(samples) == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
