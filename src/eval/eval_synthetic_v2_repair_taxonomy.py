from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.audit.common import load_coarse_map
from src.data.common import PILOT_DIR, REPORT_DIR, ROOT, read_jsonl_file, write_json

WARNING = "WARNING: expected labels are synthetic intent labels, not gold labels."


def macro_f1(preds: list[Any], golds: list[Any]) -> float:
    labels = sorted({str(item) for item in preds + golds})
    if not labels:
        return 0.0
    scores = []
    for label in labels:
        tp = sum(str(p) == label and str(g) == label for p, g in zip(preds, golds))
        fp = sum(str(p) == label and str(g) != label for p, g in zip(preds, golds))
        fn = sum(str(p) != label and str(g) == label for p, g in zip(preds, golds))
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return round(sum(scores) / len(scores), 4)


def acc(pairs: list[tuple[Any, Any]]) -> float:
    return round(sum(a == b for a, b in pairs) / len(pairs), 4) if pairs else 0.0


def off_by_one(pairs: list[tuple[Any, Any]]) -> float:
    if not pairs:
        return 0.0
    ok = 0
    for pred, gold in pairs:
        ok += int(pred == gold or (isinstance(pred, int) and isinstance(gold, int) and abs(pred - gold) <= 1))
    return round(ok / len(pairs), 4)


def evaluate(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    coarse = load_coarse_map()
    detail = []
    fw_pairs = []
    intervention_pairs = []
    fine_pairs = []
    coarse_pairs = []
    hint_pairs = []
    leakage_pairs = []
    per_type: dict[str, dict[str, Any]] = {}
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        meta = row["synthetic_metadata"]
        labels = row["pedagogical_labels"]
        pred_first = row["existing_labels"]["first_wrong_step"]
        gold_first = meta.get("expected_first_wrong_step")
        pred_fine = labels["minimal_repair_type"]
        gold_fine = meta.get("expected_minimal_repair_type")
        pred_coarse = coarse.get(pred_fine)
        gold_coarse = meta.get("expected_minimal_repair_coarse_6") or coarse.get(gold_fine)
        stype = meta["synthetic_type"]
        fw_pairs.append((pred_first, gold_first))
        intervention_pairs.append((labels["intervention_needed"], meta.get("expected_intervention_needed")))
        fine_pairs.append((pred_fine, gold_fine))
        coarse_pairs.append((pred_coarse, gold_coarse))
        hint_pairs.append((labels["hint_level"], meta.get("expected_hint_level")))
        leakage_pairs.append((labels["leakage_constraint"], meta.get("expected_leakage_constraint")))
        confusion[str(gold_coarse)][str(pred_coarse)] += 1
        stats = per_type.setdefault(stype, {"count": 0, "first_wrong_off_by_one": 0, "coarse_repair_correct": 0, "intervention_correct": 0})
        stats["count"] += 1
        stats["first_wrong_off_by_one"] += int(
            pred_first == gold_first or (isinstance(pred_first, int) and isinstance(gold_first, int) and abs(pred_first - gold_first) <= 1)
        )
        stats["coarse_repair_correct"] += int(pred_coarse == gold_coarse)
        stats["intervention_correct"] += int(labels["intervention_needed"] == meta.get("expected_intervention_needed"))
        detail.append(
            {
                "sample_id": row["sample_id"],
                "synthetic_type": stype,
                "expected_first_wrong_step": gold_first,
                "pred_first_wrong_step": pred_first,
                "expected_intervention_needed": meta.get("expected_intervention_needed"),
                "pred_intervention_needed": labels["intervention_needed"],
                "expected_minimal_repair_type": gold_fine,
                "pred_minimal_repair_type": pred_fine,
                "expected_coarse": gold_coarse,
                "pred_coarse": pred_coarse,
                "coarse_correct": int(pred_coarse == gold_coarse),
            }
        )
    for stats in per_type.values():
        count = stats["count"]
        stats["first_wrong_off_by_one_acc"] = round(stats["first_wrong_off_by_one"] / count, 4)
        stats["coarse_repair_acc"] = round(stats["coarse_repair_correct"] / count, 4)
        stats["intervention_acc"] = round(stats["intervention_correct"] / count, 4)
    repair_dist = Counter(row["pedagogical_labels"]["minimal_repair_type"] for row in rows)
    diff_ratio = sum(
        row["existing_labels"]["first_wrong_step"] != row["pedagogical_labels"]["earliest_actionable_step"]
        for row in rows
    ) / len(rows) if rows else 0
    false_uncertain = sum(row["pedagogical_labels"]["intervention_needed"] in {False, "uncertain"} for row in rows) / len(rows) if rows else 0
    summary = {
        "phase": "3.18",
        "warning": WARNING,
        "count": len(rows),
        "first_wrong_step_exact_acc": acc(fw_pairs),
        "first_wrong_step_off_by_one_acc": off_by_one(fw_pairs),
        "intervention_needed_acc": acc(intervention_pairs),
        "minimal_repair_type_exact_acc": acc(fine_pairs),
        "minimal_repair_type_macro_f1": macro_f1([p for p, _ in fine_pairs], [g for _, g in fine_pairs]),
        "minimal_repair_coarse_6_acc": acc(coarse_pairs),
        "minimal_repair_coarse_6_macro_f1": macro_f1([p for p, _ in coarse_pairs], [g for _, g in coarse_pairs]),
        "hint_level_acc": acc(hint_pairs),
        "leakage_constraint_acc": acc(leakage_pairs),
        "first_wrong_step_not_equal_earliest_actionable_step_ratio": round(diff_ratio, 4),
        "intervention_needed_false_uncertain_ratio": round(false_uncertain, 4),
        "minimal_repair_type_distribution": dict(repair_dist),
        "minimal_repair_coarse_confusion": {gold: dict(preds) for gold, preds in confusion.items()},
        "per_synthetic_type": per_type,
        "go_no_go": {
            "count>=100": len(rows) >= 100,
            "first_wrong_step_off_by_one_acc>=0.80": off_by_one(fw_pairs) >= 0.80,
            "minimal_repair_coarse_6_acc>=0.70": acc(coarse_pairs) >= 0.70,
            "intervention_needed_acc>=0.80": acc(intervention_pairs) >= 0.80,
            "single_repair_type<=0.70": (max(repair_dist.values()) / len(rows) <= 0.70) if rows else False,
        },
    }
    return summary, detail


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Phase 3.18 synthetic v2 repair taxonomy labels")
    parser.add_argument("--input", type=Path, default=PILOT_DIR / "synthetic_v2_150.autolabeled.jsonl")
    args = parser.parse_args()
    rows = read_jsonl_file(args.input)
    summary, detail = evaluate(rows)
    write_json(REPORT_DIR / "synthetic_v2_repair_taxonomy_eval_summary.json", summary)
    with (REPORT_DIR / "synthetic_v2_repair_taxonomy_eval_detail.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detail[0]) if detail else ["sample_id"])
        writer.writeheader()
        writer.writerows(detail)
    report = [
        "# Phase 3.18 Synthetic v2 Repair Taxonomy Evaluation",
        "",
        WARNING,
        "",
        "These are automatic comparisons against synthetic intent labels. They are not human gold results.",
        "",
        "```json",
        json.dumps(summary, ensure_ascii=False, indent=2),
        "```",
    ]
    (ROOT / "reports" / "phase3_18_synthetic_v2.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
