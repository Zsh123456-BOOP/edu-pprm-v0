from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_json, write_jsonl
from src.data.validate_schema import validate_sample
from src.labels.deepseek_labeler import apply_label
from src.labels.deepseek_prompts import build_label_messages
from src.labels.validate_deepseek_labels import validate_deepseek_label
from src.llm.deepseek_client import DeepSeekClient, load_config


def normalize_label(label: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(label)
    for key in ["first_wrong_step", "earliest_actionable_step"]:
        value = normalized.get(key)
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"", "null", "none", "n/a", "na"}:
                normalized[key] = None
            elif text.endswith(".0") and text[:-2].isdigit():
                normalized[key] = int(text[:-2])
            elif text.isdigit():
                normalized[key] = int(text)
    intervention = normalized.get("intervention_needed")
    if isinstance(intervention, str):
        text = intervention.strip().lower()
        if text in {"true", "yes", "1"}:
            normalized["intervention_needed"] = True
        elif text in {"false", "no", "0"}:
            normalized["intervention_needed"] = False
        elif text in {"uncertain", "unknown"}:
            normalized["intervention_needed"] = "uncertain"
    confidence = normalized.get("confidence")
    if isinstance(confidence, str):
        try:
            normalized["confidence"] = float(confidence)
        except ValueError:
            pass
    for key in ["repair_target", "actionable_diff_reason", "short_rationale"]:
        if isinstance(normalized.get(key), str) and normalized[key].strip().lower() in {"null", "none", "n/a", "na"}:
            normalized[key] = None if key != "short_rationale" else ""
    return normalized


def label_one(sample: dict[str, Any], model: str) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"label_synthetic_v2_{model}")
    # Keep the full guideline/taxonomy prompt, but disable DeepSeek thinking for
    # throughput and to avoid long-running retries on a 100+ row batch.
    config["thinking"] = {"type": "disabled"}
    config["reasoning_effort"] = None
    config["temperature"] = 0.0
    config["max_tokens"] = 1200
    config["timeout_seconds"] = 90
    config["max_retries"] = 2
    client = DeepSeekClient(config=config)
    started = time.monotonic()
    # build_label_messages intentionally hides synthetic_metadata.expected_* for gsm8k/math samples.
    result = client.chat_json(
        build_label_messages(sample),
        sample_id=f"label_synthetic_v2_{sample['sample_id']}",
        temperature=0.0,
        max_tokens=900,
    )
    label = normalize_label(result["parsed"])
    errors = validate_deepseek_label(label)
    if errors:
        raise ValueError("; ".join(errors))
    updated = apply_label(sample, label, result.get("model", model), result.get("raw", {}).get("id"))
    updated["label_metadata"]["label_latency_seconds"] = round(time.monotonic() - started, 3)
    validate_sample(updated)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek blind-label Phase 3.18 synthetic v2 traces")
    parser.add_argument("--input", type=Path, default=PILOT_DIR / "synthetic_v2_150.verified.raw.jsonl")
    parser.add_argument("--output", type=Path, default=PILOT_DIR / "synthetic_v2_150.autolabeled.jsonl")
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required; do not fabricate DeepSeek labels")
    samples = read_jsonl_file(args.input)
    outputs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {pool.submit(label_one, sample, args.model): sample for sample in samples}
        for future in as_completed(future_map):
            sample = future_map[future]
            try:
                outputs.append(future.result())
            except Exception as exc:
                failures.append({"sample_id": sample["sample_id"], "error": f"{type(exc).__name__}: {exc}"})
    outputs.sort(key=lambda row: row["sample_id"])
    failures.sort(key=lambda row: row["sample_id"])
    write_jsonl(args.output, outputs)
    write_jsonl(REPORT_DIR / "synthetic_v2_label_failures.jsonl", failures)
    repair_dist = Counter(row["pedagogical_labels"]["minimal_repair_type"] for row in outputs)
    summary = {
        "phase": "3.18",
        "input_count": len(samples),
        "output_count": len(outputs),
        "failure_count": len(failures),
        "model": args.model,
        "parse_rate": round(len(outputs) / len(samples), 4) if samples else 0,
        "schema_validation_pass_rate": round(len(outputs) / len(samples), 4) if samples else 0,
        "minimal_repair_type_distribution": dict(repair_dist),
        "intervention_needed_distribution": dict(Counter(str(row["pedagogical_labels"]["intervention_needed"]) for row in outputs)),
        "single_repair_type_over_70pct": (max(repair_dist.values()) / len(outputs) > 0.7) if outputs else True,
    }
    write_json(REPORT_DIR / "synthetic_v2_label_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if len(outputs) >= min(len(samples), 100) and not summary["single_repair_type_over_70pct"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
