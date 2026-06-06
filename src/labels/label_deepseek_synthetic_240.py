from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, write_json, write_jsonl
from src.data.common import read_jsonl_file
from src.data.validate_schema import validate_sample
from src.labels.deepseek_labeler import apply_label
from src.labels.deepseek_prompts import build_compact_label_messages, build_label_messages
from src.labels.validate_deepseek_labels import validate_deepseek_label
from src.llm.deepseek_client import DeepSeekClient, load_config


def label_one(sample: dict[str, Any], model: str, compact: bool) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"label_synth240_{model}")
    if compact:
        config["thinking"] = {"type": "disabled"}
        config["reasoning_effort"] = None
    config["temperature"] = 0.0
    config["max_tokens"] = 650
    config["timeout_seconds"] = 60
    client = DeepSeekClient(config=config)
    started = time.monotonic()
    messages = build_compact_label_messages(sample) if compact else build_label_messages(sample)
    result = client.chat_json(messages, sample_id=f"label_synth240_{sample['sample_id']}", temperature=0.0, max_tokens=650)
    label = result["parsed"]
    errors = validate_deepseek_label(label)
    if errors:
        raise ValueError("; ".join(errors))
    updated = apply_label(sample, label, result.get("model", model), result.get("raw", {}).get("id"))
    updated["label_metadata"]["label_latency_seconds"] = round(time.monotonic() - started, 3)
    validate_sample(updated)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Label DeepSeek-generated synthetic 240 with DeepSeek")
    parser.add_argument("--input", default=str(PILOT_DIR / "deepseek_synthetic_240.raw.jsonl"))
    parser.add_argument("--output", default=str(PILOT_DIR / "deepseek_synthetic_240.autolabeled.jsonl"))
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--full-prompt", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required")
    samples = read_jsonl_file(__import__("pathlib").Path(args.input))
    outputs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {
            pool.submit(label_one, sample, args.model, not args.full_prompt): sample
            for sample in samples
        }
        for future in as_completed(future_map):
            sample = future_map[future]
            try:
                outputs.append(future.result())
            except Exception as exc:
                failures.append({"sample_id": sample["sample_id"], "error": f"{type(exc).__name__}: {exc}"})
    outputs.sort(key=lambda item: item["sample_id"])
    failures.sort(key=lambda item: item["sample_id"])
    write_jsonl(__import__("pathlib").Path(args.output), outputs)
    write_jsonl(REPORT_DIR / "deepseek_synthetic_240_label_failures.jsonl", failures)
    summary = {
        "input_count": len(samples),
        "output_count": len(outputs),
        "failure_count": len(failures),
        "model": args.model,
        "workers": args.workers,
        "compact_prompt": not args.full_prompt,
        "parse_rate": round(len(outputs) / len(samples), 4) if samples else 0,
        "schema_validation_pass_rate": round(len(outputs) / len(samples), 4) if samples else 0,
        "minimal_repair_type_distribution": dict(Counter(item["pedagogical_labels"]["minimal_repair_type"] for item in outputs)),
        "intervention_needed_distribution": dict(Counter(str(item["pedagogical_labels"]["intervention_needed"]) for item in outputs)),
    }
    write_json(REPORT_DIR / "deepseek_synthetic_240_label_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["parse_rate"] >= 0.95 and summary["schema_validation_pass_rate"] >= 0.95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
