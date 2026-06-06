from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_json


def _map_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in rows}


def _same(a: Any, b: Any) -> bool:
    return a == b


def _off_by_one(a: Any, b: Any) -> bool:
    return isinstance(a, int) and isinstance(b, int) and abs(a - b) <= 1


def _f1_by_label(preds: list[Any], golds: list[Any]) -> tuple[float, dict[str, float]]:
    labels = sorted({str(x) for x in preds + golds})
    scores = {}
    for label in labels:
        tp = sum(str(p) == label and str(g) == label for p, g in zip(preds, golds))
        fp = sum(str(p) == label and str(g) != label for p, g in zip(preds, golds))
        fn = sum(str(p) != label and str(g) == label for p, g in zip(preds, golds))
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        scores[label] = 2 * precision * recall / (precision + recall) if precision + recall else 0
    return (sum(scores.values()) / len(scores) if scores else 0, scores)


def evaluate(raw_path: Path, labeled_path: Path) -> dict[str, Any]:
    raw = _map_by_id(read_jsonl_file(raw_path))
    labeled = read_jsonl_file(labeled_path)
    step_rows = []
    synth_rows = []
    for row in labeled:
        source = row["problem"]["source"]
        if source == "stepverify":
            gold = raw[row["sample_id"]]["existing_labels"]["first_wrong_step"]
            pred = row["existing_labels"]["first_wrong_step"]
            step_rows.append(
                {
                    "sample_id": row["sample_id"],
                    "gold_first_wrong_step": gold,
                    "pred_first_wrong_step": pred,
                    "exact": int(_same(pred, gold)),
                    "off_by_one": int(_off_by_one(pred, gold)),
                    "pred_null": int(pred is None),
                    "overclaim": int(gold is None and pred is not None),
                }
            )
        elif row.get("synthetic_metadata"):
            meta = row["synthetic_metadata"]
            synth_rows.append(
                {
                    "sample_id": row["sample_id"],
                    "source": source,
                    "synthetic_type": meta["synthetic_type"],
                    "first_wrong_step_exact": int(_same(row["existing_labels"]["first_wrong_step"], meta["expected_first_wrong_step"])),
                    "earliest_actionable_step_exact": int(_same(row["pedagogical_labels"]["earliest_actionable_step"], meta["expected_earliest_actionable_step"])),
                    "intervention_needed_pred": row["pedagogical_labels"]["intervention_needed"],
                    "intervention_needed_gold": meta["expected_intervention_needed"],
                    "minimal_repair_type_pred": row["pedagogical_labels"]["minimal_repair_type"],
                    "minimal_repair_type_gold": meta["expected_minimal_repair_type"],
                    "hint_level_exact": int(_same(row["pedagogical_labels"]["hint_level"], meta["expected_hint_level"])),
                    "leakage_constraint_exact": int(_same(row["pedagogical_labels"]["leakage_constraint"], meta["expected_leakage_constraint"])),
                }
            )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORT_DIR / "deepseek_stepverify_eval.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(step_rows[0]) if step_rows else ["sample_id"])
        writer.writeheader()
        writer.writerows(step_rows)
    with (REPORT_DIR / "deepseek_synthetic_eval.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(synth_rows[0]) if synth_rows else ["sample_id"])
        writer.writeheader()
        writer.writerows(synth_rows)
    step_metrics = {
        "count": len(step_rows),
        "first_wrong_step_acc": round(sum(r["exact"] for r in step_rows) / len(step_rows), 4) if step_rows else 0,
        "off_by_one_acc": round(sum(r["off_by_one"] for r in step_rows) / len(step_rows), 4) if step_rows else 0,
        "null_error_rate": round(sum(r["pred_null"] for r in step_rows) / len(step_rows), 4) if step_rows else 0,
        "overclaim_rate": round(sum(r["overclaim"] for r in step_rows) / len(step_rows), 4) if step_rows else 0,
    }
    intervention_macro_f1, _ = _f1_by_label(
        [r["intervention_needed_pred"] for r in synth_rows],
        [r["intervention_needed_gold"] for r in synth_rows],
    )
    repair_macro_f1, repair_f1 = _f1_by_label(
        [r["minimal_repair_type_pred"] for r in synth_rows],
        [r["minimal_repair_type_gold"] for r in synth_rows],
    )
    synth_metrics = {
        "count": len(synth_rows),
        "first_wrong_step_acc": round(sum(r["first_wrong_step_exact"] for r in synth_rows) / len(synth_rows), 4) if synth_rows else 0,
        "earliest_actionable_step_acc": round(sum(r["earliest_actionable_step_exact"] for r in synth_rows) / len(synth_rows), 4) if synth_rows else 0,
        "intervention_needed_f1": round(intervention_macro_f1, 4),
        "minimal_repair_type_macro_f1": round(repair_macro_f1, 4),
        "minimal_repair_type_f1_by_label": repair_f1,
        "hint_level_acc": round(sum(r["hint_level_exact"] for r in synth_rows) / len(synth_rows), 4) if synth_rows else 0,
        "leakage_constraint_acc": round(sum(r["leakage_constraint_exact"] for r in synth_rows) / len(synth_rows), 4) if synth_rows else 0,
    }
    diff_count = sum(
        row["existing_labels"]["first_wrong_step"] != row["pedagogical_labels"]["earliest_actionable_step"]
        for row in labeled
    )
    distribution = {
        "count": len(labeled),
        "first_wrong_step_not_equal_earliest_actionable_step_ratio": round(diff_count / len(labeled), 4) if labeled else 0,
        "intervention_needed_distribution": dict(Counter(str(row["pedagogical_labels"]["intervention_needed"]) for row in labeled)),
        "minimal_repair_type_distribution": dict(Counter(row["pedagogical_labels"]["minimal_repair_type"] for row in labeled)),
        "hint_level_distribution": dict(Counter(row["pedagogical_labels"]["hint_level"] for row in labeled)),
        "leakage_constraint_distribution": dict(Counter(row["pedagogical_labels"]["leakage_constraint"] for row in labeled)),
        "confidence_distribution": {
            "avg": round(sum(row["label_metadata"].get("confidence") or 0 for row in labeled) / len(labeled), 4) if labeled else 0
        },
        "source_wise": {},
        "synthetic_type_wise": {},
    }
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in labeled:
        by_source[row["problem"]["source"]].append(row)
        if row.get("synthetic_metadata"):
            by_type[row["synthetic_metadata"]["synthetic_type"]].append(row)
    for key, rows in by_source.items():
        distribution["source_wise"][key] = dict(Counter(r["pedagogical_labels"]["minimal_repair_type"] for r in rows))
    for key, rows in by_type.items():
        distribution["synthetic_type_wise"][key] = dict(Counter(r["pedagogical_labels"]["minimal_repair_type"] for r in rows))
    write_json(REPORT_DIR / "deepseek_label_distribution.json", distribution)
    return {"stepverify": step_metrics, "synthetic": synth_metrics, "distribution": distribution}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate DeepSeek auto-silver labels")
    parser.add_argument("--raw", type=Path, default=PILOT_DIR / "pilot_pool.raw.jsonl")
    parser.add_argument("--labeled", type=Path, default=PILOT_DIR / "pilot_pool.autolabeled.jsonl")
    args = parser.parse_args()
    metrics = evaluate(args.raw, args.labeled)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
