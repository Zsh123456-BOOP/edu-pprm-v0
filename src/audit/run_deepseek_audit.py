from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from src.audit.common import AUDIT_DIR, BLIND_PATH, DEEPSEEK_LABELS_PATH, REPORT_DIR, ROOT, validate_audit_label
from src.data.common import read_jsonl_file, write_json, write_jsonl
from src.llm.deepseek_client import DeepSeekClient, load_config


def load_local_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists() or os.environ.get("DEEPSEEK_API_KEY"):
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DEEPSEEK_API_KEY="):
            os.environ["DEEPSEEK_API_KEY"] = line.split("=", 1)[1].strip()


def prompt_context() -> str:
    guideline = (ROOT / "docs" / "annotation_guideline.md").read_text(encoding="utf-8")
    taxonomy = (ROOT / "configs" / "label_taxonomy.yaml").read_text(encoding="utf-8")
    return f"ANNOTATION GUIDELINE\n{guideline}\n\nLABEL TAXONOMY\n{taxonomy}"


def build_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "sample_id": row["sample_id"],
        "problem": row["problem"],
        "student_trace": row["student_trace"],
        "reference_solution_steps": row.get("reference_solution_steps", []),
        "gold_answer": row.get("gold_answer"),
        "source": row.get("source"),
    }
    return [
        {
            "role": "system",
            "content": (
                "You are a proxy audit annotator for math tutoring traces. Return JSON only. "
                "Do not infer from sample_id. Do not assume expected labels exist. "
                "These are proxy audit labels, not human labels."
            ),
        },
        {
            "role": "user",
            "content": (
                prompt_context()
                + "\n\nAnnotation order: first check problem/trace completeness, then first_wrong_step, "
                "intervention_needed, earliest_actionable_step, minimal_repair_type, hint_level, leakage_constraint, confidence, rationale.\n"
                "Return exactly these keys: sample_id, annotator, first_wrong_step, earliest_actionable_step, intervention_needed, "
                "minimal_repair_type, repair_target, hint_level, leakage_constraint, confidence, rationale. "
                "Use annotator='deepseek_proxy'. intervention_needed must be true, false, or uncertain. "
                "repair_target must be a string, using an empty string if there is no target. "
                "confidence must be a numeric value from 0 to 1, not a percent string.\n\nBLIND_SAMPLE\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        },
    ]


def normalize_label(parsed: dict[str, Any], sample_id: str) -> dict[str, Any]:
    label = dict(parsed)
    label["sample_id"] = sample_id
    label["annotator"] = "deepseek_proxy"
    if label.get("repair_target") is None:
        label["repair_target"] = ""
    elif not isinstance(label.get("repair_target"), str):
        label["repair_target"] = str(label.get("repair_target"))
    confidence = label.get("confidence")
    if isinstance(confidence, str):
        cleaned = confidence.strip().lower().rstrip("%")
        word_map = {
            "very high": 0.9,
            "high": 0.85,
            "medium": 0.65,
            "moderate": 0.65,
            "low": 0.45,
            "very low": 0.25,
        }
        if cleaned in word_map:
            label["confidence"] = word_map[cleaned]
        else:
            try:
                value = float(cleaned)
                label["confidence"] = value / 100 if value > 1 else value
            except ValueError:
                pass
    intervention = label.get("intervention_needed")
    if isinstance(intervention, str):
        value = intervention.strip().lower()
        if value in {"true", "yes"}:
            label["intervention_needed"] = True
        elif value in {"false", "no"}:
            label["intervention_needed"] = False
        elif value == "uncertain":
            label["intervention_needed"] = "uncertain"
    for key in ["first_wrong_step", "earliest_actionable_step"]:
        if isinstance(label.get(key), str):
            value = label[key].strip().lower()
            label[key] = None if value in {"", "null", "none", "unknown"} else int(value)
    return label


def label_one(row: dict[str, Any], model: str) -> dict[str, Any]:
    config = load_config(model=model, cache_suffix=f"audit_60_{model}")
    config["temperature"] = 0.0
    config["max_tokens"] = 1800
    config["timeout_seconds"] = 180
    config["max_retries"] = 3
    client = DeepSeekClient(config=config)
    started = time.monotonic()
    result = client.chat_json(build_messages(row), sample_id=f"audit_60_{row['sample_id']}", temperature=0.0, max_tokens=1800)
    parsed = normalize_label(result["parsed"], row["sample_id"])
    errors = validate_audit_label(parsed, expected_annotator="deepseek_proxy")
    if errors:
        raise ValueError("; ".join(errors))
    parsed["_latency_seconds"] = round(time.monotonic() - started, 3)
    return parsed


def write_dry_run(rows: list[dict[str, Any]], model: str, output: Path) -> None:
    config = load_config(model=model, cache_suffix=f"audit_60_{model}")
    client = DeepSeekClient(config=config, dry_run=True)
    payloads = []
    for row in rows:
        payloads.append(client.chat_json(build_messages(row), sample_id=f"audit_60_{row['sample_id']}"))
    write_jsonl(AUDIT_DIR / "deepseek_audit_60.dryrun_prompts.jsonl", payloads)
    write_json(REPORT_DIR / "deepseek_audit_60_summary.json", {
        "status": "pending",
        "reason": "DEEPSEEK_API_KEY is not set; dry-run prompts generated and no DeepSeek labels fabricated.",
        "dryrun_prompt_count": len(payloads),
        "dryrun_prompt_path": "data/audit/deepseek_audit_60.dryrun_prompts.jsonl",
        "output_path": str(output),
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DeepSeek full-prompt blind audit")
    parser.add_argument("--input", default=str(BLIND_PATH))
    parser.add_argument("--output", default=str(DEEPSEEK_LABELS_PATH))
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--full-prompt", action="store_true")
    parser.add_argument("--retry-failures", action="store_true")
    args = parser.parse_args()
    if not args.full_prompt:
        raise SystemExit("--full-prompt is required for the main proxy audit")
    load_local_env()
    rows = read_jsonl_file(Path(args.input))
    output = Path(args.output)
    if not os.environ.get("DEEPSEEK_API_KEY"):
        write_dry_run(rows, args.model, output)
        print(json.dumps({"status": "pending", "dryrun_prompt_count": len(rows)}, indent=2))
        return 0
    current_ids = {row["sample_id"] for row in rows}
    existing_labels = {row["sample_id"]: row for row in read_jsonl_file(output) if row.get("sample_id") in current_ids}
    failure_path = REPORT_DIR / "deepseek_audit_60_failures.jsonl"
    existing_failures = {row["sample_id"]: row for row in read_jsonl_file(failure_path) if row.get("sample_id") in current_ids}
    if args.retry_failures:
        existing_failures = {}
    labels: list[dict[str, Any]] = list(existing_labels.values())
    failures: list[dict[str, Any]] = list(existing_failures.values())
    rows_to_run = [
        row for row in rows
        if row["sample_id"] not in existing_labels and row["sample_id"] not in existing_failures
    ]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(label_one, row, args.model): row for row in rows_to_run}
        for future in as_completed(futures):
            row = futures[future]
            try:
                label = future.result()
                label.pop("_latency_seconds", None)
                existing_labels[label["sample_id"]] = label
                existing_failures.pop(label["sample_id"], None)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                if "timed out" in error.lower() or "timeout" in error.lower():
                    failure_type = "timeout"
                elif "no JSON object" in error:
                    failure_type = "no_json"
                elif "invalid" in error or "must be" in error:
                    failure_type = "schema_error"
                else:
                    failure_type = "invalid_label"
                existing_failures[row["sample_id"]] = {"sample_id": row["sample_id"], "failure_type": failure_type, "error": error}
            labels = sorted(existing_labels.values(), key=lambda item: item["sample_id"])
            failures = sorted(existing_failures.values(), key=lambda item: item["sample_id"])
            write_jsonl(output, labels)
            write_jsonl(failure_path, failures)
    write_jsonl(output, labels)
    write_jsonl(failure_path, failures)
    summary = {
        "status": "completed" if not failures else "completed_with_failures",
        "input_count": len(rows),
        "output_count": len(labels),
        "failure_count": len(failures),
        "pending_count": len(rows) - len(labels) - len(failures),
        "model": args.model,
        "workers": args.workers,
        "prompt": "full",
        "repair_distribution": dict(Counter(label["minimal_repair_type"] for label in labels)),
    }
    write_json(REPORT_DIR / "deepseek_audit_60_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
