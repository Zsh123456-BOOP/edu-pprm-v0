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
from src.synthetic.inject_math_errors import SYNTHETIC_TYPES, inject_trace
from src.synthetic.verify_synthetic_steps import verify_synthetic_sample


def expected_for(row: dict[str, Any], synthetic_type: str) -> dict[str, Any]:
    injection = inject_trace(row, synthetic_type)
    return {
        "synthetic_type": synthetic_type,
        "injected_error_step": injection.injected_error_step,
        "injected_error_type": injection.injected_error_type,
        "expected_first_wrong_step": injection.expected_first_wrong_step,
        "expected_earliest_actionable_step": injection.expected_earliest_actionable_step,
        "expected_intervention_needed": injection.expected_intervention_needed,
        "expected_minimal_repair_type": injection.expected_minimal_repair_type,
        "expected_hint_level": injection.expected_hint_level,
        "expected_leakage_constraint": injection.expected_leakage_constraint,
        "repair_target": injection.repair_target,
    }


def step_objects(texts: list[str]) -> list[dict[str, Any]]:
    return [{"step_id": index + 1, "text": text} for index, text in enumerate(texts)]


def generation_messages(row: dict[str, Any], synthetic_type: str) -> list[dict[str, str]]:
    rules = {
        "arithmetic_error": "Create exactly one local arithmetic error.",
        "sign_error": "Create exactly one sign handling error.",
        "wrong_operation": "Use the wrong operation once, such as adding when multiplying is needed.",
        "misread_given_quantity": "Misinterpret one given quantity once.",
        "unit_conversion_error": "Create one unit conversion or scale-factor error.",
        "equation_setup_error": "Set up one equation/expression that does not match the problem.",
        "substitution_error": "Use the wrong given value in one otherwise relevant expression.",
        "no_error_correct_trace": "Create a correct student trace with no error.",
        "self_corrected_error": "Show one wrong step followed by explicit self-correction.",
        "sparse_insufficient_trace": "Return exactly one student step only. It must be too little work to safely diagnose the error.",
        "final_answer_correct_process_wrong": "Make the process wrong but final answer correct by recall.",
        "final_answer_wrong_prefix_correct": "Keep the reasoning prefix correct, then copy/write the final answer wrong.",
        "hint_would_leak_answer": "Return exactly one short student step only. It must be a short-answer trace where direct tutor help would reveal the answer.",
    }
    payload = {
        "source": row["source"],
        "problem_id": row["problem_id"],
        "problem_text": row["problem_text"],
        "reference_solution_steps": row.get("gold_solution_steps", [])[:5],
        "gold_answer": row.get("gold_answer"),
        "synthetic_type": synthetic_type,
        "generation_rule": rules[synthetic_type],
    }
    return [
        {
            "role": "system",
            "content": (
                "Return JSON only. Generate a realistic student math trace for a pilot dataset. "
                "Do not include expected labels. Do not mention synthetic metadata. Keep the trace concise."
            ),
        },
        {
            "role": "user",
            "content": (
                "Return exactly this JSON object: {\"student_steps\": [\"...\"], "
                "\"student_final_answer\": \"string or null\", \"is_correct\": true/false/null, "
                "\"generation_note\": \"short note\"}. "
                "For sparse_insufficient_trace and hint_would_leak_answer, student_steps MUST have length exactly 1. "
                "For self_corrected_error, include the word Wait or correct in the student steps. "
                "Ensure the requested synthetic_type is visible in the student steps.\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        },
    ]


def build_sample(row: dict[str, Any], synthetic_type: str, index: int, generated: dict[str, Any], model: str) -> dict[str, Any]:
    expected = expected_for(row, synthetic_type)
    student_steps = generated.get("student_steps") if isinstance(generated.get("student_steps"), list) else []
    sample = {
        "sample_id": f"deepseek_synth240_{index:04d}",
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
            "trace_id": f"trace_deepseek_synth240_{index:04d}",
            "trace_source": "synthetic_llm",
            "student_steps": step_objects([str(step) for step in student_steps]),
            "student_final_answer": generated.get("student_final_answer"),
            "is_correct": generated.get("is_correct"),
        },
        "existing_labels": {
            "first_wrong_step": None,
            "error_category": expected["injected_error_type"],
            "error_description": generated.get("generation_note"),
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
            "raw_label_response_id": None,
        },
        "reserved": _reserved(),
        "synthetic_metadata": {
            **expected,
            "generation_method": f"deepseek_pro_generation_v1",
            "verification_status": "pending",
            "parent_problem_id": row.get("problem_id"),
            "generator_model": model,
        },
    }
    status, reason = verify_synthetic_sample(sample)
    if synthetic_type == "hint_would_leak_answer" and len(sample["student_trace"]["student_steps"]) > 2:
        status, reason = "failed", "hint_would_leak_answer must be a short trace"
    if synthetic_type != "sparse_insufficient_trace" and not sample["student_trace"]["student_steps"]:
        status, reason = "failed", "missing student steps"
    sample["synthetic_metadata"]["verification_status"] = status
    if reason:
        sample["synthetic_metadata"]["verification_error"] = reason
    return sample


def load_problem_rows(total: int) -> list[dict[str, Any]]:
    gsm = read_jsonl_file(ROOT / "data" / "interim" / "gsm8k.problem_bank.raw.jsonl")
    math_rows = read_jsonl_file(ROOT / "data" / "interim" / "math.problem_bank.raw.jsonl")
    if len(gsm) < total:
        gsm = load_gsm8k(max(total, 160))
    if len(math_rows) < total // 2:
        math_rows = load_math(max(total // 2, 80))
    rows: list[dict[str, Any]] = []
    for index in range(total):
        source_rows = gsm if index % 3 != 2 else math_rows
        rows.append(source_rows[index % len(source_rows)])
    return rows


def planned_items(total: int) -> list[tuple[int, dict[str, Any], str]]:
    rows = load_problem_rows(total)
    return [(index, rows[index], SYNTHETIC_TYPES[index % len(SYNTHETIC_TYPES)]) for index in range(total)]


def target_type_counts(total: int) -> dict[str, int]:
    base = total // len(SYNTHETIC_TYPES)
    remainder = total % len(SYNTHETIC_TYPES)
    return {
        synthetic_type: base + (1 if index < remainder else 0)
        for index, synthetic_type in enumerate(SYNTHETIC_TYPES)
    }


def fill_items(existing: list[dict[str, Any]], total: int) -> list[tuple[int, dict[str, Any], str]]:
    current = Counter(item["synthetic_metadata"]["synthetic_type"] for item in existing)
    targets = target_type_counts(total)
    rows = load_problem_rows(total * 2)
    start_index = 0
    if existing:
        start_index = max(int(item["sample_id"].rsplit("_", 1)[-1]) for item in existing) + 1
    items = []
    cursor = 0
    for synthetic_type, target in targets.items():
        missing = max(0, target - current.get(synthetic_type, 0))
        for _ in range(missing):
            index = start_index + len(items)
            items.append((index, rows[cursor % len(rows)], synthetic_type))
            cursor += 1
    return items


def generate_one(index: int, row: dict[str, Any], synthetic_type: str, model: str) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"generate_synth240_{model}")
    config["thinking"] = {"type": "disabled"}
    config["reasoning_effort"] = None
    config["temperature"] = 0.4
    config["max_tokens"] = 550
    config["timeout_seconds"] = 60
    client = DeepSeekClient(config=config)
    started = time.monotonic()
    result = client.chat_json(generation_messages(row, synthetic_type), sample_id=f"generate_synth240_{index:04d}", temperature=0.4, max_tokens=550)
    sample = build_sample(row, synthetic_type, index, result["parsed"], result.get("model", model))
    sample["synthetic_metadata"]["generation_latency_seconds"] = round(time.monotonic() - started, 3)
    sample["label_metadata"]["raw_label_response_id"] = result.get("raw", {}).get("id")
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 240 DeepSeek-pro synthetic traces")
    parser.add_argument("--count", type=int, default=240)
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--fill-existing", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required")
    existing = read_jsonl_file(PILOT_DIR / "deepseek_synthetic_240.raw.jsonl") if args.fill_existing else []
    samples: list[dict[str, Any]] = list(existing)
    failures: list[dict[str, Any]] = []
    items = fill_items(existing, args.count) if args.fill_existing else planned_items(args.count)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {
            pool.submit(generate_one, index, row, synthetic_type, args.model): (index, row, synthetic_type)
            for index, row, synthetic_type in items
        }
        for future in as_completed(future_map):
            index, row, synthetic_type = future_map[future]
            try:
                sample = future.result()
                if sample["synthetic_metadata"]["verification_status"] == "passed":
                    validate_sample(sample)
                    samples.append(sample)
                else:
                    failures.append(sample)
            except Exception as exc:
                failures.append(
                    {
                        "sample_id": f"deepseek_synth240_{index:04d}",
                        "problem_id": row.get("problem_id"),
                        "synthetic_type": synthetic_type,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    samples.sort(key=lambda item: item["sample_id"])
    failures.sort(key=lambda item: item.get("sample_id", ""))
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(PILOT_DIR / "deepseek_synthetic_240.raw.jsonl", samples)
    write_jsonl(REPORT_DIR / "deepseek_synthetic_240_generation_failures.jsonl", failures)
    write_jsonl(REPORT_DIR / "deepseek_synthetic_240_40_examples.jsonl", samples[:40])
    summary = {
        "requested_count": args.count,
        "passed_count": len(samples),
        "failure_count": len(failures),
        "model": args.model,
        "workers": args.workers,
        "synthetic_type_distribution": dict(Counter(item["synthetic_metadata"]["synthetic_type"] for item in samples)),
        "source_distribution": dict(Counter(item["problem"]["source"] for item in samples)),
        "min_per_type": min(Counter(item["synthetic_metadata"]["synthetic_type"] for item in samples).values()) if samples else 0,
    }
    write_json(REPORT_DIR / "deepseek_synthetic_240_generation_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if len(samples) == args.count and summary["min_per_type"] >= 18 else 1


if __name__ == "__main__":
    raise SystemExit(main())
