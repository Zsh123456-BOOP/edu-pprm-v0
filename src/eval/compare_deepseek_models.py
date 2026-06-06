from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, ROOT, read_jsonl_file, write_json


def _by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in rows}


def _acc(items: list[bool]) -> float:
    return round(sum(items) / len(items), 4) if items else 0.0


def evaluate_model(model: str) -> dict[str, Any]:
    raw = _by_id(read_jsonl_file(PILOT_DIR / "pilot_pool.raw.jsonl"))
    outputs = read_jsonl_file(REPORT_DIR / f"deepseek_small_batch_{model}_outputs.jsonl")
    summary = json.loads((REPORT_DIR / f"deepseek_small_batch_{model}_summary.json").read_text(encoding="utf-8"))
    step_checks = []
    synth_first = []
    synth_action = []
    synth_intervention = []
    synth_repair = []
    synth_hint = []
    synth_leakage = []
    diff_checks = []
    for item in outputs:
        sample = raw[item["sample_id"]]
        label = item["label"]
        if sample["problem"]["source"] == "stepverify":
            step_checks.append(label["first_wrong_step"] == sample["existing_labels"]["first_wrong_step"])
        meta = sample.get("synthetic_metadata")
        if meta:
            synth_first.append(label["first_wrong_step"] == meta["expected_first_wrong_step"])
            synth_action.append(label["earliest_actionable_step"] == meta["expected_earliest_actionable_step"])
            synth_intervention.append(label["intervention_needed"] == meta["expected_intervention_needed"])
            synth_repair.append(label["minimal_repair_type"] == meta["expected_minimal_repair_type"])
            synth_hint.append(label["hint_level"] == meta["expected_hint_level"])
            synth_leakage.append(label["leakage_constraint"] == meta["expected_leakage_constraint"])
        diff_checks.append(label["first_wrong_step"] != label["earliest_actionable_step"])
    quality = {
        "model": model,
        "count": len(outputs),
        "success_count": summary["success_count"],
        "failure_count": summary["failure_count"],
        "avg_latency_seconds": summary["avg_latency_seconds"],
        "max_latency_seconds": summary["max_latency_seconds"],
        "stepverify_first_wrong_step_acc": _acc(step_checks),
        "synthetic_first_wrong_step_acc": _acc(synth_first),
        "synthetic_earliest_actionable_step_acc": _acc(synth_action),
        "synthetic_intervention_needed_acc": _acc(synth_intervention),
        "synthetic_minimal_repair_type_acc": _acc(synth_repair),
        "synthetic_hint_level_acc": _acc(synth_hint),
        "synthetic_leakage_constraint_acc": _acc(synth_leakage),
        "first_wrong_step_diff_ratio": _acc(diff_checks),
        "minimal_repair_type_distribution": dict(Counter(item["label"]["minimal_repair_type"] for item in outputs)),
    }
    # Simple score prioritizes quality, then speed.
    quality["quality_score"] = round(
        0.25 * quality["stepverify_first_wrong_step_acc"]
        + 0.20 * quality["synthetic_minimal_repair_type_acc"]
        + 0.15 * quality["synthetic_earliest_actionable_step_acc"]
        + 0.15 * quality["synthetic_intervention_needed_acc"]
        + 0.10 * quality["synthetic_hint_level_acc"]
        + 0.10 * quality["synthetic_leakage_constraint_acc"]
        + 0.05 * min(quality["first_wrong_step_diff_ratio"] / 0.10, 1.0),
        4,
    )
    return quality


def main() -> int:
    models = ["deepseek-v4-flash", "deepseek-v4-pro"]
    results = [evaluate_model(model) for model in models]
    best_quality = max(results, key=lambda row: (row["quality_score"], -row["avg_latency_seconds"]))
    fastest = min(results, key=lambda row: row["avg_latency_seconds"] or 10**9)
    recommendation = best_quality["model"]
    if best_quality["quality_score"] == fastest["quality_score"]:
        recommendation = fastest["model"]
    report = {
        "models": results,
        "best_quality_model": best_quality["model"],
        "fastest_model": fastest["model"],
        "recommended_full_run_model": recommendation,
        "decision_reason": (
            "Choose the higher quality_score; if tied, choose lower latency. "
            "This comparison uses the same 20 samples: 10 StepVerify and 10 synthetic."
        ),
    }
    write_json(REPORT_DIR / "deepseek_model_quality_comparison.json", report)
    lines = ["# DeepSeek Model Quality Comparison", "", f"Recommended full-run model: `{recommendation}`", ""]
    for row in results:
        lines.append(f"## {row['model']}")
        lines.append("")
        for key, value in row.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    (ROOT / "reports" / "deepseek_model_quality_comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
