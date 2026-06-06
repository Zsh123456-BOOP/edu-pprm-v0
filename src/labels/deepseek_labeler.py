from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from src.data.common import CACHE_DIR, PILOT_DIR, REPORT_DIR, ROOT, append_jsonl, read_jsonl_file, write_json, write_jsonl
from src.data.validate_schema import validate_sample
from src.labels.deepseek_prompts import build_label_messages
from src.labels.validate_deepseek_labels import validate_deepseek_label
from src.llm.deepseek_client import DeepSeekClient, load_config


def heuristic_label(sample: dict[str, Any]) -> dict[str, Any]:
    meta = sample.get("synthetic_metadata")
    if meta:
        return {
            "first_wrong_step": meta.get("expected_first_wrong_step"),
            "earliest_actionable_step": meta.get("expected_earliest_actionable_step"),
            "intervention_needed": meta.get("expected_intervention_needed"),
            "minimal_repair_type": meta.get("expected_minimal_repair_type"),
            "repair_target": meta.get("repair_target"),
            "hint_level": meta.get("expected_hint_level"),
            "leakage_constraint": meta.get("expected_leakage_constraint"),
            "actionable_diff_reason": "Synthetic fallback uses deterministic known-label metadata because API was unavailable.",
            "confidence": 0.78,
            "short_rationale": "Known synthetic rule template.",
        }
    existing = sample["existing_labels"]
    category = (existing.get("error_category") or "").lower()
    first_wrong = existing.get("first_wrong_step")
    repair = "ask_to_recompute_local_expression"
    leakage = "do_not_solve_next_step"
    hint = "medium"
    if "unit" in category:
        repair = "ask_to_check_unit_conversion"
        leakage = "can_show_micro_example"
    elif "quantity" in category or "misunderstanding" in category or "factual" in category:
        repair = "ask_to_reinterpret_given_quantity"
    elif "calculation" in category:
        repair = "ask_to_recompute_local_expression"
        hint = "low"
    return {
        "first_wrong_step": first_wrong,
        "earliest_actionable_step": first_wrong,
        "intervention_needed": True if first_wrong is not None else "uncertain",
        "minimal_repair_type": repair if first_wrong is not None else "insufficient_information",
        "repair_target": f"student step {first_wrong}" if first_wrong is not None else None,
        "hint_level": hint if first_wrong is not None else "medium",
        "leakage_constraint": leakage,
        "actionable_diff_reason": "Fallback maps existing first-error source into a minimal repair guess.",
        "confidence": 0.62,
        "short_rationale": "Heuristic fallback; not a real DeepSeek API label.",
    }


def apply_label(sample: dict[str, Any], label: dict[str, Any], model_name: str, response_id: str | None) -> dict[str, Any]:
    updated = json.loads(json.dumps(sample))
    updated["existing_labels"]["first_wrong_step"] = label["first_wrong_step"]
    updated["pedagogical_labels"] = {
        "intervention_needed": label["intervention_needed"],
        "earliest_actionable_step": label["earliest_actionable_step"],
        "minimal_repair_type": label["minimal_repair_type"],
        "repair_target": label["repair_target"],
        "hint_level": label["hint_level"],
        "leakage_constraint": label["leakage_constraint"],
        "actionable_diff_reason": label["actionable_diff_reason"],
    }
    updated["label_metadata"].update(
        {
            "quality_tier": "silver",
            "label_source": "auto",
            "adjudication_status": "none",
            "confidence": float(label["confidence"]),
            "short_rationale": label["short_rationale"],
            "model_name": model_name,
            "raw_label_response_id": response_id,
            "excluded_reason": None,
        }
    )
    validate_sample(updated)
    return updated


def label_samples(samples: list[dict[str, Any]], *, use_api: bool, dry_run: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    config = load_config()
    client = DeepSeekClient(config=config, dry_run=dry_run)
    outputs = []
    failures = []
    parse_ok = 0
    valid_ok = 0
    api_available = use_api and bool(os.environ.get("DEEPSEEK_API_KEY"))
    cache_dir = ROOT / config.get("cache_dir", str(CACHE_DIR / "deepseek"))
    for sample in samples:
        messages = build_label_messages(sample)
        label: dict[str, Any]
        model_name = config["model"]
        response_id = None
        try:
            if api_available:
                result = client.chat_json(messages, sample_id=sample["sample_id"])
                label = result["parsed"]
                response_id = result.get("raw", {}).get("id")
                model_name = result.get("model", model_name)
            else:
                # Keep request payloads for audit even when falling back.
                payload = client.build_payload(messages, sample_id=sample["sample_id"])
                append_jsonl(cache_dir / "label_requests.jsonl", [{"sample_id": sample["sample_id"], "mode": "fallback_no_api_key", "payload": {k: v for k, v in payload.items() if not k.startswith("_")}}])
                label = heuristic_label(sample)
                append_jsonl(cache_dir / "label_responses.jsonl", [{"sample_id": sample["sample_id"], "mode": "heuristic_fallback", "parsed": label}])
                model_name = "heuristic_fallback_no_api_key"
            parse_ok += 1
            errors = validate_deepseek_label(label)
            if errors:
                raise ValueError("; ".join(errors))
            output = apply_label(sample, label, model_name, response_id)
            outputs.append(output)
            valid_ok += 1
        except Exception as exc:
            failures.append({"sample_id": sample["sample_id"], "error": f"{type(exc).__name__}: {exc}"})
    summary = {
        "input_count": len(samples),
        "output_count": len(outputs),
        "failure_count": len(failures),
        "api_available": api_available,
        "model": config["model"],
        "parse_rate": round(parse_ok / len(samples), 4) if samples else 0,
        "schema_validation_pass_rate": round(valid_ok / len(samples), 4) if samples else 0,
        "minimal_repair_type_distribution": dict(Counter(s["pedagogical_labels"]["minimal_repair_type"] for s in outputs)),
        "source_distribution": dict(Counter(s["problem"]["source"] for s in outputs)),
        "single_repair_type_over_70pct": (max(Counter(s["pedagogical_labels"]["minimal_repair_type"] for s in outputs).values()) / len(outputs) > 0.7) if outputs else True,
    }
    return outputs, failures, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate DeepSeek auto-silver labels")
    parser.add_argument("--input", type=Path, default=PILOT_DIR / "pilot_pool.raw.jsonl")
    parser.add_argument("--output", type=Path, default=PILOT_DIR / "pilot_pool.autolabeled.jsonl")
    parser.add_argument("--use-api", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    samples = read_jsonl_file(args.input)
    outputs, failures, summary = label_samples(samples, use_api=args.use_api, dry_run=args.dry_run)
    write_jsonl(args.output, outputs)
    write_jsonl(REPORT_DIR / "deepseek_label_failures.jsonl", failures)
    write_json(REPORT_DIR / "deepseek_label_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["parse_rate"] >= 0.95 and summary["schema_validation_pass_rate"] >= 0.95 and not summary["single_repair_type_over_70pct"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
