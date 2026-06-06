from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, ROOT, read_jsonl_file, write_json


FIELDS = [
    ("first_wrong_step", ("existing_labels", "first_wrong_step"), ("synthetic_metadata", "expected_first_wrong_step")),
    ("earliest_actionable_step", ("pedagogical_labels", "earliest_actionable_step"), ("synthetic_metadata", "expected_earliest_actionable_step")),
    ("intervention_needed", ("pedagogical_labels", "intervention_needed"), ("synthetic_metadata", "expected_intervention_needed")),
    ("minimal_repair_type", ("pedagogical_labels", "minimal_repair_type"), ("synthetic_metadata", "expected_minimal_repair_type")),
    ("hint_level", ("pedagogical_labels", "hint_level"), ("synthetic_metadata", "expected_hint_level")),
    ("leakage_constraint", ("pedagogical_labels", "leakage_constraint"), ("synthetic_metadata", "expected_leakage_constraint")),
]


def get(row: dict[str, Any], path: tuple[str, str]) -> Any:
    return row[path[0]][path[1]]


def macro_f1(preds: list[Any], golds: list[Any]) -> float:
    labels = sorted({str(item) for item in preds + golds})
    scores = []
    for label in labels:
        tp = sum(str(p) == label and str(g) == label for p, g in zip(preds, golds))
        fp = sum(str(p) == label and str(g) != label for p, g in zip(preds, golds))
        fn = sum(str(p) != label and str(g) == label for p, g in zip(preds, golds))
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def evaluate(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = read_jsonl_file(path)
    detail_rows = []
    metrics = {"count": len(rows)}
    for name, pred_path, gold_path in FIELDS:
        checks = []
        preds = []
        golds = []
        for row in rows:
            pred = get(row, pred_path)
            gold = get(row, gold_path)
            checks.append(pred == gold)
            preds.append(pred)
            golds.append(gold)
        metrics[f"{name}_acc"] = round(sum(checks) / len(checks), 4) if checks else 0
        metrics[f"{name}_macro_f1"] = macro_f1(preds, golds)
    per_type: dict[str, dict[str, Any]] = {}
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        stype = row["synthetic_metadata"]["synthetic_type"]
        per_type.setdefault(stype, {"count": 0, "minimal_repair_type_correct": 0, "first_wrong_step_correct": 0})
        per_type[stype]["count"] += 1
        per_type[stype]["minimal_repair_type_correct"] += int(
            row["pedagogical_labels"]["minimal_repair_type"] == row["synthetic_metadata"]["expected_minimal_repair_type"]
        )
        per_type[stype]["first_wrong_step_correct"] += int(
            row["existing_labels"]["first_wrong_step"] == row["synthetic_metadata"]["expected_first_wrong_step"]
        )
        confusion[row["synthetic_metadata"]["expected_minimal_repair_type"]][row["pedagogical_labels"]["minimal_repair_type"]] += 1
        detail_rows.append(
            {
                "sample_id": row["sample_id"],
                "synthetic_type": stype,
                "expected_minimal_repair_type": row["synthetic_metadata"]["expected_minimal_repair_type"],
                "pred_minimal_repair_type": row["pedagogical_labels"]["minimal_repair_type"],
                "expected_first_wrong_step": row["synthetic_metadata"]["expected_first_wrong_step"],
                "pred_first_wrong_step": row["existing_labels"]["first_wrong_step"],
                "correct_repair": int(row["pedagogical_labels"]["minimal_repair_type"] == row["synthetic_metadata"]["expected_minimal_repair_type"]),
            }
        )
    for stype, stats in per_type.items():
        stats["minimal_repair_type_acc"] = round(stats["minimal_repair_type_correct"] / stats["count"], 4)
        stats["first_wrong_step_acc"] = round(stats["first_wrong_step_correct"] / stats["count"], 4)
    diff_ratio = sum(
        row["existing_labels"]["first_wrong_step"] != row["pedagogical_labels"]["earliest_actionable_step"]
        for row in rows
    ) / len(rows) if rows else 0
    false_uncertain = sum(
        row["pedagogical_labels"]["intervention_needed"] in {False, "uncertain"}
        for row in rows
    ) / len(rows) if rows else 0
    repair_dist = Counter(row["pedagogical_labels"]["minimal_repair_type"] for row in rows)
    max_repair = max(repair_dist.values()) / len(rows) if rows else 1
    report = {
        "metrics": metrics,
        "per_synthetic_type": per_type,
        "minimal_repair_type_confusion": {gold: dict(preds) for gold, preds in confusion.items()},
        "first_wrong_step_not_equal_earliest_actionable_step_ratio": round(diff_ratio, 4),
        "intervention_needed_false_uncertain_ratio": round(false_uncertain, 4),
        "minimal_repair_type_distribution": dict(repair_dist),
        "max_single_repair_type_ratio": round(max_repair, 4),
        "go_no_go": {
            "minimal_repair_type_macro_f1>=0.45": metrics["minimal_repair_type_macro_f1"] >= 0.45,
            "first_wrong_step_diff_ratio>=0.10": diff_ratio >= 0.10,
            "false_uncertain_ratio>=0.08": false_uncertain >= 0.08,
            "no_single_repair_type>0.70": max_repair <= 0.70,
        },
    }
    return report, detail_rows


def write_outputs(report: dict[str, Any], detail_rows: list[dict[str, Any]], tag: str) -> None:
    suffix = f"_{tag}" if tag else ""
    write_json(REPORT_DIR / f"deepseek_synthetic_240_eval_summary{suffix}.json", report)
    with (REPORT_DIR / f"deepseek_synthetic_240_eval_detail{suffix}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0]) if detail_rows else ["sample_id"])
        writer.writeheader()
        writer.writerows(detail_rows)
    title = "DeepSeek Synthetic 240 Evaluation" if not tag else f"DeepSeek Synthetic 240 Evaluation ({tag})"
    lines = [f"# {title}", "", json.dumps(report, ensure_ascii=False, indent=2)]
    (ROOT / "reports" / f"deepseek_synthetic_240_eval{suffix}.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate DeepSeek synthetic 240 labels against hidden expected labels")
    parser.add_argument("--input", type=Path, default=PILOT_DIR / "deepseek_synthetic_240.autolabeled.jsonl")
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    report, detail_rows = evaluate(args.input)
    write_outputs(report, detail_rows, args.tag)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
