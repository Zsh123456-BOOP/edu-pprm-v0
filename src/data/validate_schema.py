from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.data.common import REPORT_DIR, ROOT, read_jsonl_file, split_steps, write_jsonl

SCHEMA_PATH = ROOT / "schemas" / "edu_pprm.schema.json"
MINIMAL_REPAIR_TYPES = {
    "no_intervention_needed",
    "ask_to_recompute_local_expression",
    "ask_to_reinterpret_given_quantity",
    "ask_to_rewrite_equation_or_expression",
    "ask_to_check_operation_or_formula",
    "ask_to_check_unit_conversion",
    "ask_to_justify_inference",
    "ask_to_compare_with_problem_condition",
    "ask_to_substitute_back",
    "ask_clarifying_question",
    "insufficient_information",
    None,
}
HINT_LEVELS = {"none", "low", "medium", "high", "forbidden_full_solution", None}
LEAKAGE_CONSTRAINTS = {
    "do_not_reveal_final_answer",
    "do_not_solve_next_step",
    "can_point_to_local_step_only",
    "can_name_error_type",
    "can_show_micro_example",
    None,
}
LABEL_SOURCES = {"converted", "auto", "teacher", "adjudicated", "excluded", None}
QUALITY_TIERS = {"raw", "silver", "gold", None}


def _steps(items: list[Any]) -> list[dict[str, Any]]:
    return [{"step_id": index + 1, "text": None if item is None else str(item)} for index, item in enumerate(items)]


def _solution_steps(text: str | None) -> list[dict[str, Any]]:
    return _steps(split_steps(text))


def _empty_pedagogical_labels() -> dict[str, Any]:
    return {
        "intervention_needed": None,
        "earliest_actionable_step": None,
        "minimal_repair_type": None,
        "repair_target": None,
        "hint_level": None,
        "leakage_constraint": None,
        "actionable_diff_reason": None,
    }


def _reserved() -> dict[str, None]:
    return {"budget_data": None, "distillation_data": None, "handwrite_data": None}


def convert_stepverify(row: dict[str, Any], index: int) -> dict[str, Any]:
    student_raw = row.get("student_solution_raw")
    student_steps = student_raw if isinstance(student_raw, list) else split_steps(student_raw)
    return {
        "sample_id": f"schema_stepverify_{index:04d}",
        "problem": {
            "problem_id": row.get("source_id"),
            "source": "stepverify",
            "source_split": "train",
            "problem_text": row.get("problem_text"),
            "reference_solution_steps": _solution_steps(row.get("reference_solution_raw")),
            "gold_answer": None,
            "topic": row.get("metadata", {}).get("topic"),
            "difficulty": None,
        },
        "student_trace": {
            "trace_id": row.get("source_id"),
            "trace_source": "stepverify",
            "student_steps": _steps(student_steps),
            "student_final_answer": str(student_steps[-1]) if student_steps else None,
            "is_correct": False,
        },
        "existing_labels": {
            "first_wrong_step": row.get("first_wrong_step_source"),
            "error_category": row.get("error_category_source"),
            "error_description": row.get("error_description_source"),
            "teacher_feedback": None,
        },
        "pedagogical_labels": _empty_pedagogical_labels(),
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


def convert_problem_bank(row: dict[str, Any], index: int, source: str) -> dict[str, Any]:
    return {
        "sample_id": f"schema_{source}_{index:04d}",
        "problem": {
            "problem_id": row.get("problem_id"),
            "source": source,
            "source_split": row.get("source_split"),
            "problem_text": row.get("problem_text"),
            "reference_solution_steps": _steps(row.get("gold_solution_steps", [])),
            "gold_answer": row.get("gold_answer"),
            "topic": row.get("topic"),
            "difficulty": row.get("difficulty"),
        },
        "student_trace": {
            "trace_id": None,
            "trace_source": "synthetic_placeholder",
            "student_steps": [],
            "student_final_answer": None,
            "is_correct": None,
        },
        "existing_labels": {
            "first_wrong_step": None,
            "error_category": None,
            "error_description": None,
            "teacher_feedback": None,
        },
        "pedagogical_labels": _empty_pedagogical_labels(),
        "label_metadata": {
            "quality_tier": "raw",
            "label_source": "auto",
            "annotator_ids": [],
            "adjudication_status": "none",
            "excluded_reason": "synthetic placeholder only; no student error trace yet",
            "confidence": None,
            "short_rationale": None,
            "model_name": None,
            "raw_label_response_id": None,
        },
        "reserved": _reserved(),
        "synthetic_metadata": None,
    }


def convert_mathedu_excluded(row: dict[str, Any], index: int, excluded_reason: str) -> dict[str, Any]:
    return {
        "sample_id": f"schema_mathedu_excluded_{index:04d}",
        "problem": {
            "problem_id": str(row.get("source_id") or row.get("id") or index),
            "source": "mathedu",
            "source_split": None,
            "problem_text": None,
            "reference_solution_steps": [],
            "gold_answer": None,
            "topic": None,
            "difficulty": None,
        },
        "student_trace": {
            "trace_id": str(row.get("source_id") or row.get("id") or index),
            "trace_source": "mathedu",
            "student_steps": _steps(split_steps(row.get("student_solution_raw"))),
            "student_final_answer": row.get("metadata", {}).get("student_answer"),
            "is_correct": None,
        },
        "existing_labels": {
            "first_wrong_step": None,
            "error_category": row.get("error_type"),
            "error_description": None,
            "teacher_feedback": row.get("teacher_feedback"),
        },
        "pedagogical_labels": _empty_pedagogical_labels(),
        "label_metadata": {
            "quality_tier": "raw",
            "label_source": "excluded",
            "annotator_ids": [],
            "adjudication_status": "none",
            "excluded_reason": excluded_reason,
            "confidence": None,
            "short_rationale": None,
            "model_name": None,
            "raw_label_response_id": None,
        },
        "reserved": _reserved(),
        "synthetic_metadata": None,
    }


def required_paths() -> list[tuple[str, ...]]:
    return [
        ("sample_id",),
        ("problem", "problem_id"),
        ("problem", "source"),
        ("problem", "source_split"),
        ("problem", "problem_text"),
        ("problem", "reference_solution_steps"),
        ("problem", "gold_answer"),
        ("problem", "topic"),
        ("problem", "difficulty"),
        ("student_trace", "trace_id"),
        ("student_trace", "trace_source"),
        ("student_trace", "student_steps"),
        ("student_trace", "student_final_answer"),
        ("student_trace", "is_correct"),
        ("existing_labels", "first_wrong_step"),
        ("existing_labels", "error_category"),
        ("existing_labels", "error_description"),
        ("existing_labels", "teacher_feedback"),
        ("pedagogical_labels", "intervention_needed"),
        ("pedagogical_labels", "earliest_actionable_step"),
        ("pedagogical_labels", "minimal_repair_type"),
        ("pedagogical_labels", "repair_target"),
        ("pedagogical_labels", "hint_level"),
        ("pedagogical_labels", "leakage_constraint"),
        ("pedagogical_labels", "actionable_diff_reason"),
        ("label_metadata", "quality_tier"),
        ("label_metadata", "label_source"),
        ("label_metadata", "annotator_ids"),
        ("label_metadata", "adjudication_status"),
        ("label_metadata", "excluded_reason"),
        ("label_metadata", "confidence"),
        ("label_metadata", "short_rationale"),
        ("label_metadata", "model_name"),
        ("label_metadata", "raw_label_response_id"),
        ("reserved", "budget_data"),
        ("reserved", "distillation_data"),
        ("reserved", "handwrite_data"),
        ("synthetic_metadata",),
    ]


def _get(sample: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = sample
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f"missing field: {'.'.join(path)}")
        value = value[key]
    return value


def validate_sample(sample: dict[str, Any]) -> None:
    for path in required_paths():
        _get(sample, path)
    reserved = sample["reserved"]
    if reserved != _reserved():
        raise ValueError("reserved fields must all be explicit null")
    labels = sample["pedagogical_labels"]
    if labels["intervention_needed"] not in {True, False, "uncertain", None}:
        raise ValueError("invalid intervention_needed")
    if labels["minimal_repair_type"] not in MINIMAL_REPAIR_TYPES:
        raise ValueError("invalid minimal_repair_type")
    if labels["hint_level"] not in HINT_LEVELS:
        raise ValueError("invalid hint_level")
    if labels["leakage_constraint"] not in LEAKAGE_CONSTRAINTS:
        raise ValueError("invalid leakage_constraint")
    metadata = sample["label_metadata"]
    if metadata["label_source"] not in LABEL_SOURCES:
        raise ValueError("invalid label_source")
    if metadata["quality_tier"] not in QUALITY_TIERS:
        raise ValueError("invalid quality_tier")


def assert_processbench_path(path: Path) -> None:
    text = str(path)
    if "processbench" in text and "data/external_eval" not in text:
        raise ValueError("ProcessBench must not enter train/interim paths")


def write_schema_examples() -> list[dict[str, Any]]:
    stepverify = read_jsonl_file(ROOT / "data" / "interim" / "stepverify.raw.jsonl")[:5]
    gsm8k = read_jsonl_file(ROOT / "data" / "interim" / "gsm8k.problem_bank.raw.jsonl")[:5]
    math_rows = read_jsonl_file(ROOT / "data" / "interim" / "math.problem_bank.raw.jsonl")[:5]
    mathedu = read_jsonl_file(ROOT / "data" / "interim" / "mathedu.raw.jsonl")[:5]
    excluded_reason = "MathEDU audit found 0% recoverable problem_text/question fields; excluded from Phase 3 pilot"
    examples = []
    examples.extend(convert_stepverify(row, index) for index, row in enumerate(stepverify))
    examples.extend(convert_problem_bank(row, index, "gsm8k") for index, row in enumerate(gsm8k))
    examples.extend(convert_problem_bank(row, index, "math") for index, row in enumerate(math_rows))
    examples.extend(convert_mathedu_excluded(row, index, excluded_reason) for index, row in enumerate(mathedu))
    for sample in examples:
        validate_sample(sample)
    write_jsonl(REPORT_DIR / "schema_conversion_examples.jsonl", examples)
    return examples


def validate_jsonl(path: Path) -> int:
    assert_processbench_path(path)
    count = 0
    for sample in read_jsonl_file(path):
        validate_sample(sample)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Edu-PPRM schema examples")
    parser.add_argument("--write-examples", action="store_true")
    parser.add_argument("--jsonl", type=Path)
    args = parser.parse_args()
    if args.write_examples:
        examples = write_schema_examples()
        print(f"wrote {len(examples)} schema conversion examples")
    if args.jsonl:
        count = validate_jsonl(args.jsonl)
        print(f"validated {count} rows from {args.jsonl}")
    if not args.write_examples and not args.jsonl:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
