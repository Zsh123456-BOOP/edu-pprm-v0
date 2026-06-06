from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_json, write_jsonl
from src.llm.deepseek_client import DeepSeekClient, load_config


def verify_messages(sample: dict[str, Any]) -> list[dict[str, str]]:
    meta = sample["synthetic_metadata"]
    payload = {
        "sample_id": sample["sample_id"],
        "synthetic_type": meta["synthetic_type"],
        "expected_injected_error_type": meta["injected_error_type"],
        "problem": sample["problem"],
        "student_trace": sample["student_trace"],
    }
    return [
        {
            "role": "system",
            "content": "Return JSON only. You verify whether a synthetic math student trace truly matches its requested error type.",
        },
        {
            "role": "user",
            "content": (
                "Check strictly. Return keys: valid true/false, primary_error_count integer, "
                "synthetic_type_matches true/false, first_wrong_step integer/null, "
                "reason short string. Rules: no_error_correct_trace must have no math error; "
                "self_corrected_error must have an error and explicit correction; "
                "sparse_insufficient_trace must be too sparse to diagnose; "
                "hint_would_leak_answer must be a short trace where direct help would reveal the answer; "
                "standard error types must contain exactly one primary error of the requested type.\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        },
    ]


def verify_one(sample: dict[str, Any], model: str) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"verify_synth240_{model}")
    config["thinking"] = {"type": "disabled"}
    config["reasoning_effort"] = None
    config["temperature"] = 0.0
    config["max_tokens"] = 450
    config["timeout_seconds"] = 60
    result = DeepSeekClient(config=config).chat_json(verify_messages(sample), sample_id=f"verify_synth240_{sample['sample_id']}", temperature=0.0, max_tokens=450)
    parsed = result["parsed"]
    valid = bool(parsed.get("valid")) and bool(parsed.get("synthetic_type_matches"))
    if sample["synthetic_metadata"]["synthetic_type"] not in {"no_error_correct_trace", "self_corrected_error", "sparse_insufficient_trace", "hint_would_leak_answer"}:
        valid = valid and parsed.get("primary_error_count") == 1
    updated = json.loads(json.dumps(sample))
    updated["synthetic_metadata"]["llm_verification"] = parsed
    updated["synthetic_metadata"]["llm_verification_status"] = "passed" if valid else "failed"
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM verify DeepSeek synthetic 240 traces")
    parser.add_argument("--input", default=str(PILOT_DIR / "deepseek_synthetic_240.raw.jsonl"))
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required")
    samples = read_jsonl_file(__import__("pathlib").Path(args.input))
    verified: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {pool.submit(verify_one, sample, args.model): sample for sample in samples}
        for future in as_completed(future_map):
            sample = future_map[future]
            try:
                verified.append(future.result())
            except Exception as exc:
                failed = json.loads(json.dumps(sample))
                failed["synthetic_metadata"]["llm_verification_status"] = "failed"
                failed["synthetic_metadata"]["llm_verification_error"] = f"{type(exc).__name__}: {exc}"
                failures.append(failed)
    verified.sort(key=lambda item: item["sample_id"])
    all_rows = verified + failures
    passed = [row for row in all_rows if row["synthetic_metadata"].get("llm_verification_status") == "passed"]
    failed = [row for row in all_rows if row["synthetic_metadata"].get("llm_verification_status") != "passed"]
    write_jsonl(PILOT_DIR / "deepseek_synthetic_240.verified.raw.jsonl", passed)
    write_jsonl(REPORT_DIR / "deepseek_synthetic_240_llm_verification_failures.jsonl", failed)
    summary = {
        "input_count": len(samples),
        "verified_pass_count": len(passed),
        "verified_fail_count": len(failed),
        "model": args.model,
        "pass_rate": round(len(passed) / len(samples), 4) if samples else 0,
        "passed_type_distribution": dict(Counter(row["synthetic_metadata"]["synthetic_type"] for row in passed)),
        "failed_type_distribution": dict(Counter(row["synthetic_metadata"]["synthetic_type"] for row in failed)),
    }
    write_json(REPORT_DIR / "deepseek_synthetic_240_llm_verification_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
