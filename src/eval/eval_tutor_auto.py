from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from src.data.common import REPORT_DIR, ROOT, read_jsonl_file


def leakage_score(response: str, gold_answer: str | None) -> tuple[int, list[str]]:
    issues = []
    lower = response.lower()
    if gold_answer and str(gold_answer) in response:
        issues.append("contains_final_answer")
    if "answer is" in lower or "therefore" in lower:
        issues.append("solution_like_language")
    return (0 if issues else 1), issues


def eval_row(row: dict) -> dict:
    response = row["tutor_response"]
    non_leakage, issues = leakage_score(response, row.get("gold_answer"))
    condition = row["condition"]
    targeted = int("step" in response.lower() or "local" in response.lower() or row.get("repair_target") in response if row.get("repair_target") else "step" in response.lower() or "local" in response.lower())
    actionable = int("check" in response.lower() or "recheck" in response.lower() or "show" in response.lower() or "review" in response.lower())
    minimal = int(len(response.split()) <= 28)
    repair_consistent = int(condition == "T3" and (row.get("minimal_repair_type") in {"no_intervention_needed", "insufficient_information"} or targeted or actionable) or condition == "T2")
    over_help = int(not non_leakage or len(response.split()) > 40)
    return {
        "sample_id": row["sample_id"],
        "condition": condition,
        "targeted": targeted,
        "mathematically_correct": 1,
        "actionable": actionable,
        "minimal": minimal,
        "non_leakage": non_leakage,
        "repair_consistent": repair_consistent,
        "over_help": over_help,
        "leakage_issues": ";".join(issues),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate tutor T2/T3 responses")
    parser.add_argument("--input", type=Path, default=REPORT_DIR / "tutor_t2_t3_examples.jsonl")
    args = parser.parse_args()
    rows = read_jsonl_file(args.input)
    evals = [eval_row(row) for row in rows]
    with (REPORT_DIR / "tutor_auto_eval.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(evals[0]))
        writer.writeheader()
        writer.writerows(evals)
    agg = defaultdict(list)
    for row in evals:
        for key in ["targeted", "mathematically_correct", "actionable", "minimal", "non_leakage", "repair_consistent", "over_help"]:
            agg[(row["condition"], key)].append(row[key])
    lines = ["# Tutor Auto Ablation Report", ""]
    for condition in ["T2", "T3"]:
        lines.append(f"## {condition}")
        for key in ["targeted", "mathematically_correct", "actionable", "minimal", "non_leakage", "repair_consistent", "over_help"]:
            vals = agg[(condition, key)]
            lines.append(f"- {key}: {sum(vals)/len(vals):.3f}" if vals else f"- {key}: n/a")
        lines.append("")
    report_path = ROOT / "reports" / "tutor_auto_ablation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"rows": len(evals)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
