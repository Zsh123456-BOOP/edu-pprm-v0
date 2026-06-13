from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, ROOT, read_jsonl_file, write_json, write_jsonl
from src.data.load_gsm8k import load as load_gsm8k
from src.data.load_math import load as load_math
from src.data.validate_schema import _reserved, validate_sample
from src.llm.deepseek_client import DeepSeekClient, load_config

WARNING = "expected labels are synthetic intent labels, not gold labels"

TYPE_PLAN_150 = {
    "arithmetic_error": 16,
    "wrong_operation": 14,
    "misread_given_quantity": 14,
    "equation_setup_error": 16,
    "unit_conversion_error": 14,
    "substitution_error": 14,
    "no_error_correct_trace": 16,
    "self_corrected_error": 14,
    "final_answer_wrong_prefix_correct": 14,
    "sparse_insufficient_trace": 14,
    "hint_would_leak_answer": 4,
}

TYPE_SPECS: dict[str, dict[str, Any]] = {
    "arithmetic_error": {
        "instruction": "Create one visible local arithmetic error, such as an incorrect sum, product, difference, or quotient.",
        "expected_minimal_repair_type": "ask_to_recompute_local_expression",
        "expected_hint_level": "low",
        "expected_leakage_constraint": "do_not_solve_next_step",
        "expected_intervention_needed": True,
        "coarse_repair": "local_computation",
        "primary_error_count": 1,
    },
    "wrong_operation": {
        "instruction": "Use the wrong operation once while using the right numbers, such as adding when multiplication is required.",
        "expected_minimal_repair_type": "ask_to_check_operation_or_formula",
        "expected_hint_level": "medium",
        "expected_leakage_constraint": "can_name_error_type",
        "expected_intervention_needed": True,
        "coarse_repair": "equation_or_formula",
        "primary_error_count": 1,
    },
    "misread_given_quantity": {
        "instruction": "Misread exactly one given quantity or condition in the problem, and make that misread visible in the student trace.",
        "expected_minimal_repair_type": "ask_to_reinterpret_given_quantity",
        "expected_hint_level": "medium",
        "expected_leakage_constraint": "can_point_to_local_step_only",
        "expected_intervention_needed": True,
        "coarse_repair": "quantity_or_condition",
        "primary_error_count": 1,
    },
    "equation_setup_error": {
        "instruction": "Set up exactly one equation or expression that visibly does not represent the problem condition.",
        "expected_minimal_repair_type": "ask_to_rewrite_equation_or_expression",
        "expected_hint_level": "medium",
        "expected_leakage_constraint": "can_name_error_type",
        "expected_intervention_needed": True,
        "coarse_repair": "equation_or_formula",
        "primary_error_count": 1,
    },
    "unit_conversion_error": {
        "instruction": "Create exactly one explicit unit conversion or scale-factor error. Show the unit and conversion direction.",
        "expected_minimal_repair_type": "ask_to_check_unit_conversion",
        "expected_hint_level": "medium",
        "expected_leakage_constraint": "can_show_micro_example",
        "expected_intervention_needed": True,
        "coarse_repair": "equation_or_formula",
        "primary_error_count": 1,
    },
    "substitution_error": {
        "instruction": "Use exactly one wrong value in an otherwise reasonable equation or expression.",
        "expected_minimal_repair_type": "ask_to_substitute_back",
        "expected_hint_level": "low",
        "expected_leakage_constraint": "can_point_to_local_step_only",
        "expected_intervention_needed": True,
        "coarse_repair": "verification_check",
        "primary_error_count": 1,
    },
    "no_error_correct_trace": {
        "instruction": "Create a concise correct student trace. Do not introduce any mathematical error.",
        "expected_first_wrong_step": None,
        "expected_earliest_actionable_step": None,
        "expected_minimal_repair_type": "no_intervention_needed",
        "expected_hint_level": "none",
        "expected_leakage_constraint": "can_point_to_local_step_only",
        "expected_intervention_needed": False,
        "coarse_repair": "no_intervention",
        "primary_error_count": 0,
    },
    "self_corrected_error": {
        "instruction": "Show exactly one visible wrong step, then explicitly self-correct it in a later step using words like 'Wait' or 'Correction'. The final trace should be correct.",
        "expected_earliest_actionable_step": None,
        "expected_minimal_repair_type": "no_intervention_needed",
        "expected_hint_level": "none",
        "expected_leakage_constraint": "can_point_to_local_step_only",
        "expected_intervention_needed": False,
        "coarse_repair": "no_intervention",
        "primary_error_count": 1,
    },
    "final_answer_wrong_prefix_correct": {
        "instruction": "Keep the reasoning prefix correct, then write/copy the final answer incorrectly in the last step.",
        "expected_minimal_repair_type": "ask_to_compare_with_problem_condition",
        "expected_hint_level": "low",
        "expected_leakage_constraint": "do_not_reveal_final_answer",
        "expected_intervention_needed": True,
        "coarse_repair": "quantity_or_condition",
        "primary_error_count": 1,
    },
    "sparse_insufficient_trace": {
        "instruction": "Return exactly one short student step that is too sparse to safely diagnose. It should not expose enough reasoning to identify a specific math error.",
        "expected_first_wrong_step": None,
        "expected_earliest_actionable_step": None,
        "expected_minimal_repair_type": "insufficient_information",
        "expected_hint_level": "medium",
        "expected_leakage_constraint": "do_not_reveal_final_answer",
        "expected_intervention_needed": "uncertain",
        "coarse_repair": "insufficient_or_clarify",
        "primary_error_count": 0,
    },
    "hint_would_leak_answer": {
        "instruction": "Return exactly one short student step for a short-answer problem where direct next-step help would likely reveal the answer.",
        "expected_first_wrong_step": None,
        "expected_earliest_actionable_step": None,
        "expected_minimal_repair_type": "insufficient_information",
        "expected_hint_level": "forbidden_full_solution",
        "expected_leakage_constraint": "do_not_reveal_final_answer",
        "expected_intervention_needed": "uncertain",
        "coarse_repair": "insufficient_or_clarify",
        "primary_error_count": 0,
    },
}


def step_objects(texts: list[Any]) -> list[dict[str, Any]]:
    return [{"step_id": index + 1, "text": str(text)} for index, text in enumerate(texts)]


def load_problem_rows(total: int) -> list[dict[str, Any]]:
    gsm_path = ROOT / "data" / "interim" / "gsm8k.problem_bank.raw.jsonl"
    math_path = ROOT / "data" / "interim" / "math.problem_bank.raw.jsonl"
    gsm = read_jsonl_file(gsm_path)
    math_rows = read_jsonl_file(math_path)
    if len(gsm) < total:
        gsm = load_gsm8k(max(total, 180))
        write_jsonl(gsm_path, gsm)
    if len(math_rows) < total // 3:
        math_rows = load_math(max(total // 3, 70))
        write_jsonl(math_path, math_rows)
    rows: list[dict[str, Any]] = []
    for index in range(total):
        source_rows = math_rows if index % 4 == 3 else gsm
        rows.append(source_rows[index % len(source_rows)])
    return rows


def planned_items(count: int) -> list[tuple[int, dict[str, Any], str]]:
    if count == 150:
        type_counts = TYPE_PLAN_150
    else:
        keys = list(TYPE_PLAN_150)
        base = count // len(keys)
        rem = count % len(keys)
        type_counts = {key: base + (1 if index < rem else 0) for index, key in enumerate(keys)}
    rows = load_problem_rows(count)
    items: list[tuple[int, dict[str, Any], str]] = []
    row_index = 0
    sample_index = 1
    for synthetic_type, type_count in type_counts.items():
        for _ in range(type_count):
            items.append((sample_index, rows[row_index % len(rows)], synthetic_type))
            sample_index += 1
            row_index += 1
    return items


def generation_messages(row: dict[str, Any], synthetic_type: str, index: int) -> list[dict[str, str]]:
    spec = TYPE_SPECS[synthetic_type]
    payload = {
        "sample_id": f"synthetic_v2_{index:04d}",
        "problem_id": row.get("problem_id"),
        "source": row.get("source"),
        "problem_text": row.get("problem_text"),
        "reference_solution_steps": row.get("gold_solution_steps", [])[:6],
        "gold_answer": row.get("gold_answer"),
        "synthetic_type": synthetic_type,
        "generation_instruction": spec["instruction"],
        "required_expected_repair": spec["expected_minimal_repair_type"],
        "required_expected_intervention_needed": spec["expected_intervention_needed"],
    }
    return [
        {
            "role": "system",
            "content": (
                "Return JSON only. You generate synthetic math student traces for a research pilot. "
                "The trace must be realistic and concise. Do not create multiple independent main errors. "
                "Do not mention hidden labels or synthetic metadata inside the student steps."
            ),
        },
        {
            "role": "user",
            "content": (
                "Generate one student trace. Return exactly this JSON object:\n"
                "{\n"
                '  "student_steps": ["..."],\n'
                '  "student_final_answer": "string or null",\n'
                '  "is_correct": true/false/null,\n'
                '  "first_wrong_step": integer or null,\n'
                '  "repair_target": "short phrase or null",\n'
                '  "error_description": "short phrase",\n'
                '  "generation_note": "short phrase explaining why the requested type is visible"\n'
                "}\n"
                "Rules:\n"
                "- For no_error_correct_trace: first_wrong_step must be null and is_correct true.\n"
                "- For self_corrected_error: first_wrong_step must be the temporary wrong step, but is_correct should be true if final trace is corrected.\n"
                "- For sparse_insufficient_trace and hint_would_leak_answer: student_steps must have length exactly 1 and first_wrong_step must be null.\n"
                "- For final_answer_wrong_prefix_correct: first_wrong_step must be the last answer step.\n"
                "- For standard error types: first_wrong_step must be the one visible primary error step.\n"
                "- Keep steps numbered implicitly by list order; do not prefix each string with 'Step 1:'.\n\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        },
    ]


def expected_metadata(synthetic_type: str, generated: dict[str, Any]) -> dict[str, Any]:
    spec = TYPE_SPECS[synthetic_type]
    first_wrong = spec.get("expected_first_wrong_step", generated.get("first_wrong_step"))
    earliest = spec.get("expected_earliest_actionable_step", first_wrong)
    if spec["expected_intervention_needed"] in {False, "uncertain"}:
        earliest = spec.get("expected_earliest_actionable_step")
    return {
        "synthetic_type": synthetic_type,
        "injected_error_step": first_wrong,
        "injected_error_type": synthetic_type,
        "expected_first_wrong_step": first_wrong,
        "expected_earliest_actionable_step": earliest,
        "expected_intervention_needed": spec["expected_intervention_needed"],
        "expected_minimal_repair_type": spec["expected_minimal_repair_type"],
        "expected_minimal_repair_coarse_6": spec["coarse_repair"],
        "expected_hint_level": spec["expected_hint_level"],
        "expected_leakage_constraint": spec["expected_leakage_constraint"],
        "expected_primary_error_count": spec["primary_error_count"],
        "repair_target": generated.get("repair_target"),
    }


def basic_generation_errors(synthetic_type: str, generated: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    steps = generated.get("student_steps")
    if not isinstance(steps, list) or not all(isinstance(step, str) and step.strip() for step in steps):
        errors.append("student_steps must be a non-empty list of strings")
        return errors
    if synthetic_type in {"sparse_insufficient_trace", "hint_would_leak_answer"} and len(steps) != 1:
        errors.append(f"{synthetic_type} must have exactly one step")
    if synthetic_type not in {"no_error_correct_trace", "sparse_insufficient_trace", "hint_would_leak_answer"}:
        first_wrong = generated.get("first_wrong_step")
        if not isinstance(first_wrong, int) or first_wrong < 1 or first_wrong > len(steps):
            errors.append("first_wrong_step must identify a visible student step")
    if synthetic_type == "no_error_correct_trace" and generated.get("first_wrong_step") is not None:
        errors.append("no_error_correct_trace must not mark a wrong step")
    if synthetic_type == "self_corrected_error" and not any(("wait" in step.lower() or "correct" in step.lower()) for step in steps):
        errors.append("self_corrected_error must explicitly self-correct")
    return errors


def build_sample(row: dict[str, Any], synthetic_type: str, index: int, generated: dict[str, Any], model: str, response_id: str | None) -> dict[str, Any]:
    errors = basic_generation_errors(synthetic_type, generated)
    if errors:
        raise ValueError("; ".join(errors))
    expected = expected_metadata(synthetic_type, generated)
    steps = [str(step).strip() for step in generated["student_steps"]]
    sample_id = f"synthetic_v2_{index:04d}"
    sample = {
        "sample_id": sample_id,
        "problem": {
            "problem_id": row.get("problem_id"),
            "source": row.get("source"),
            "source_split": row.get("source_split"),
            "problem_text": row.get("problem_text"),
            "reference_solution_steps": step_objects(row.get("gold_solution_steps", [])),
            "gold_answer": row.get("gold_answer"),
            "topic": row.get("topic"),
            "difficulty": row.get("difficulty"),
        },
        "student_trace": {
            "trace_id": f"trace_{sample_id}",
            "trace_source": "synthetic_llm_v2",
            "student_steps": step_objects(steps),
            "student_final_answer": generated.get("student_final_answer"),
            "is_correct": generated.get("is_correct"),
        },
        "existing_labels": {
            "first_wrong_step": None,
            "error_category": synthetic_type,
            "error_description": generated.get("error_description"),
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
            "model_name": model,
            "raw_label_response_id": response_id,
        },
        "reserved": _reserved(),
        "synthetic_metadata": {
            **expected,
            "generation_method": "deepseek_pro_synthetic_v2",
            "verification_status": "basic_passed",
            "parent_problem_id": row.get("problem_id"),
            "generator_model": model,
            "generation_note": generated.get("generation_note"),
            "warning": WARNING,
        },
    }
    validate_sample(sample)
    return sample


def generate_one(index: int, row: dict[str, Any], synthetic_type: str, model: str) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"generate_synthetic_v2_{model}")
    config["thinking"] = {"type": "disabled"}
    config["reasoning_effort"] = None
    config["temperature"] = 0.35
    config["max_tokens"] = 900
    config["timeout_seconds"] = 120
    client = DeepSeekClient(config=config)
    started = time.monotonic()
    result = client.chat_json(
        generation_messages(row, synthetic_type, index),
        sample_id=f"generate_synthetic_v2_{index:04d}",
        temperature=0.35,
        max_tokens=900,
    )
    sample = build_sample(row, synthetic_type, index, result["parsed"], result.get("model", model), result.get("raw", {}).get("id"))
    sample["synthetic_metadata"]["generation_latency_seconds"] = round(time.monotonic() - started, 3)
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 3.18 synthetic v2 traces with DeepSeek")
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required; do not fabricate synthetic v2 outputs")
    items = planned_items(args.count)
    outputs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {
            pool.submit(generate_one, index, row, synthetic_type, args.model): (index, row, synthetic_type)
            for index, row, synthetic_type in items
        }
        for future in as_completed(future_map):
            index, row, synthetic_type = future_map[future]
            try:
                outputs.append(future.result())
            except Exception as exc:
                failures.append(
                    {
                        "sample_id": f"synthetic_v2_{index:04d}",
                        "problem_id": row.get("problem_id"),
                        "synthetic_type": synthetic_type,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    outputs.sort(key=lambda row: row["sample_id"])
    failures.sort(key=lambda row: row["sample_id"])
    write_jsonl(PILOT_DIR / "synthetic_v2_150.raw.jsonl", outputs)
    write_jsonl(REPORT_DIR / "synthetic_v2_generation_failures.jsonl", failures)
    write_jsonl(REPORT_DIR / "synthetic_v2_30_examples.jsonl", outputs[:30])
    summary = {
        "phase": "3.18",
        "warning": WARNING,
        "target_count": args.count,
        "output_count": len(outputs),
        "failure_count": len(failures),
        "model": args.model,
        "type_distribution": dict(Counter(row["synthetic_metadata"]["synthetic_type"] for row in outputs)),
        "source_distribution": dict(Counter(row["problem"]["source"] for row in outputs)),
        "expected_coarse_repair_distribution": dict(Counter(row["synthetic_metadata"]["expected_minimal_repair_coarse_6"] for row in outputs)),
    }
    write_json(REPORT_DIR / "synthetic_v2_generation_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if len(outputs) >= min(args.count, 100) else 1


if __name__ == "__main__":
    raise SystemExit(main())
