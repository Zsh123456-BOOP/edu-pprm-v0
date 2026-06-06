from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, ROOT, read_jsonl_file, write_json, write_jsonl
from src.data.validate_schema import validate_sample
from src.labels.deepseek_labeler import apply_label
from src.labels.deepseek_prompts import build_compact_label_messages, build_label_messages
from src.labels.validate_deepseek_labels import validate_deepseek_label
from src.llm.deepseek_client import DeepSeekClient, load_config


def select_samples(limit: int) -> list[dict[str, Any]]:
    rows = read_jsonl_file(PILOT_DIR / "pilot_pool.raw.jsonl")
    stepverify = [row for row in rows if row["problem"]["source"] == "stepverify"][: limit // 2]
    synthetic = [row for row in rows if row.get("synthetic_metadata")][: limit - len(stepverify)]
    return stepverify + synthetic


def run_model(model: str, samples: list[dict[str, Any]], *, timeout_seconds: int, max_tokens: int, compact: bool) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"small_batch_{model}")
    config["timeout_seconds"] = timeout_seconds
    config["max_tokens"] = max_tokens
    # Throughput probe: disable thinking for small-batch labeling unless the model requires it.
    config["thinking"] = {"type": "disabled"}
    config["reasoning_effort"] = None
    client = DeepSeekClient(config=config, dry_run=False)
    outputs = []
    failures = []
    latencies = []
    start = time.monotonic()
    for sample in samples:
        t0 = time.monotonic()
        try:
            messages = build_compact_label_messages(sample) if compact else build_label_messages(sample)
            result = client.chat_json(messages, sample_id=f"smallbatch_{model}_{sample['sample_id']}", max_tokens=max_tokens)
            latency = time.monotonic() - t0
            label = result["parsed"]
            errors = validate_deepseek_label(label)
            if errors:
                raise ValueError("; ".join(errors))
            updated = apply_label(sample, label, result.get("model", model), result.get("raw", {}).get("id"))
            validate_sample(updated)
            outputs.append({"sample_id": sample["sample_id"], "latency_seconds": round(latency, 3), "label": label, "model_response": result.get("model", model)})
            latencies.append(latency)
        except Exception as exc:
            failures.append({"sample_id": sample["sample_id"], "error": f"{type(exc).__name__}: {exc}", "elapsed_seconds": round(time.monotonic() - t0, 3)})
    total = time.monotonic() - start
    summary = {
        "model": model,
        "input_count": len(samples),
        "success_count": len(outputs),
        "failure_count": len(failures),
        "parse_rate": round(len(outputs) / len(samples), 4) if samples else 0,
        "schema_validation_pass_rate": round(len(outputs) / len(samples), 4) if samples else 0,
        "total_seconds": round(total, 3),
        "avg_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "max_latency_seconds": round(max(latencies), 3) if latencies else None,
        "minimal_repair_type_distribution": dict(Counter(item["label"]["minimal_repair_type"] for item in outputs)),
        "intervention_needed_distribution": dict(Counter(str(item["label"]["intervention_needed"]) for item in outputs)),
        "compact_prompt": compact,
    }
    write_jsonl(REPORT_DIR / f"deepseek_small_batch_{model}_outputs.jsonl", outputs)
    write_jsonl(REPORT_DIR / f"deepseek_small_batch_{model}_failures.jsonl", failures)
    write_json(REPORT_DIR / f"deepseek_small_batch_{model}_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real DeepSeek small-batch throughput validation")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--models", nargs="+", default=["deepseek-v4-pro", "deepseek-v4-flash"])
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--full-prompt", action="store_true", help="use full guideline prompt instead of compact throughput prompt")
    args = parser.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for real small-batch validation")
    samples = select_samples(args.limit)
    summaries = [run_model(model, samples, timeout_seconds=args.timeout_seconds, max_tokens=args.max_tokens, compact=not args.full_prompt) for model in args.models]
    recommendation = "no_model_ready"
    successful = [item for item in summaries if item["success_count"] == len(samples)]
    if successful:
        recommendation = min(successful, key=lambda item: item["avg_latency_seconds"] or 10**9)["model"]
    report = {
        "sample_count": len(samples),
        "models": summaries,
        "recommended_full_run_model": recommendation,
        "api_key_logged": False,
        "notes": [
            "This is a real API small-batch throughput probe.",
            "It does not overwrite pilot_pool.autolabeled.jsonl.",
        ],
    }
    write_json(REPORT_DIR / "deepseek_small_batch_comparison.json", report)
    lines = ["# DeepSeek Small-Batch Throughput Validation", "", f"Samples: {len(samples)}", "", f"Recommended full-run model: `{recommendation}`", ""]
    for summary in summaries:
        lines.append(f"## {summary['model']}")
        lines.append("")
        for key, value in summary.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    (ROOT / "reports" / "deepseek_small_batch_validation.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
