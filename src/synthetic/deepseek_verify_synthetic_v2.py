from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_json, write_jsonl
from src.data.validate_schema import validate_sample
from src.llm.deepseek_client import DeepSeekClient, load_config

WARNING = "expected labels are synthetic intent labels, not gold labels"


def verify_messages(sample: dict[str, Any]) -> list[dict[str, str]]:
    meta = sample["synthetic_metadata"]
    payload = {
        "sample_id": sample["sample_id"],
        "synthetic_type": meta["synthetic_type"],
        "expected_primary_error_count": meta.get("expected_primary_error_count"),
        "expected_first_wrong_step": meta.get("expected_first_wrong_step"),
        "expected_minimal_repair_coarse_6": meta.get("expected_minimal_repair_coarse_6"),
        "problem": sample["problem"],
        "student_trace": sample["student_trace"],
    }
    return [
        {
            "role": "system",
            "content": (
                "Return JSON only. You are a strict verifier for synthetic math student traces. "
                "Judge the visible student trace, not the generator's intention."
            ),
        },
        {
            "role": "user",
            "content": (
                "Return exactly: {\"valid\": true/false, \"primary_error_count\": integer, "
                "\"synthetic_type_matches\": true/false, \"first_wrong_step\": integer/null, "
                "\"minimal_repair_coarse_6\": \"one of no_intervention, local_computation, "
                "quantity_or_condition, equation_or_formula, verification_check, insufficient_or_clarify\", "
                "\"reason\": \"short\"}.\n"
                "Rules: standard error samples need exactly one visible main error; no_error_correct_trace needs no visible error; "
                "self_corrected_error needs a visible wrong step and explicit later correction; sparse_insufficient_trace must be too sparse; "
                "hint_would_leak_answer must be a one-step short-answer/help-seeking trace.\n\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        },
    ]


def verify_one(sample: dict[str, Any], model: str) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"verify_synthetic_v2_{model}")
    config["thinking"] = {"type": "disabled"}
    config["reasoning_effort"] = None
    config["temperature"] = 0.0
    config["max_tokens"] = 650
    config["timeout_seconds"] = 120
    result = DeepSeekClient(config=config).chat_json(
        verify_messages(sample),
        sample_id=f"verify_synthetic_v2_{sample['sample_id']}",
        temperature=0.0,
        max_tokens=650,
    )
    parsed = result["parsed"]
    meta = sample["synthetic_metadata"]
    valid = bool(parsed.get("valid")) and bool(parsed.get("synthetic_type_matches"))
    if meta["synthetic_type"] not in {"no_error_correct_trace", "sparse_insufficient_trace", "hint_would_leak_answer"}:
        valid = valid and parsed.get("primary_error_count") == meta.get("expected_primary_error_count")
    if meta["synthetic_type"] == "no_error_correct_trace":
        valid = valid and parsed.get("primary_error_count") == 0
    if meta["expected_first_wrong_step"] is not None:
        valid = valid and parsed.get("first_wrong_step") == meta["expected_first_wrong_step"]
    updated = json.loads(json.dumps(sample))
    updated["synthetic_metadata"]["strict_verifier"] = parsed
    updated["synthetic_metadata"]["strict_verifier_status"] = "passed" if valid else "failed"
    updated["synthetic_metadata"]["verification_status"] = "strict_passed" if valid else "strict_failed"
    validate_sample(updated)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Strictly verify Phase 3.18 synthetic v2 traces")
    parser.add_argument("--input", type=Path, default=PILOT_DIR / "synthetic_v2_150.raw.jsonl")
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required; do not fabricate verifier outputs")
    samples = read_jsonl_file(args.input)
    outputs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {pool.submit(verify_one, sample, args.model): sample for sample in samples}
        for future in as_completed(future_map):
            sample = future_map[future]
            try:
                outputs.append(future.result())
            except Exception as exc:
                failed = json.loads(json.dumps(sample))
                failed["synthetic_metadata"]["strict_verifier_status"] = "failed"
                failed["synthetic_metadata"]["strict_verifier_error"] = f"{type(exc).__name__}: {exc}"
                failures.append(failed)
    outputs.extend(failures)
    outputs.sort(key=lambda row: row["sample_id"])
    passed = [row for row in outputs if row["synthetic_metadata"].get("strict_verifier_status") == "passed"]
    failed = [row for row in outputs if row["synthetic_metadata"].get("strict_verifier_status") != "passed"]
    write_jsonl(PILOT_DIR / "synthetic_v2_150.verified.raw.jsonl", passed)
    write_jsonl(REPORT_DIR / "synthetic_v2_strict_verification_failures.jsonl", failed)
    summary = {
        "phase": "3.18",
        "warning": WARNING,
        "input_count": len(samples),
        "verified_pass_count": len(passed),
        "verified_fail_count": len(failed),
        "pass_rate": round(len(passed) / len(samples), 4) if samples else 0,
        "go_minimum_100_verified": len(passed) >= 100,
        "passed_type_distribution": dict(Counter(row["synthetic_metadata"]["synthetic_type"] for row in passed)),
        "failed_type_distribution": dict(Counter(row["synthetic_metadata"]["synthetic_type"] for row in failed)),
    }
    write_json(REPORT_DIR / "synthetic_v2_strict_verification_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["go_minimum_100_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
