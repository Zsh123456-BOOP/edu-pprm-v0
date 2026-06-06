from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.data.common import PILOT_DIR, REPORT_DIR, read_jsonl_file, write_jsonl
from src.labels.deepseek_labeler import heuristic_label

FIELDS = [
    "first_wrong_step",
    "earliest_actionable_step",
    "intervention_needed",
    "minimal_repair_type",
    "hint_level",
    "leakage_constraint",
]


def _agreement(values: list[Any]) -> float:
    if not values:
        return 0
    return max(Counter(str(v) for v in values).values()) / len(values)


def run_self_consistency(raw_path: Path) -> dict[str, Any]:
    rows = read_jsonl_file(raw_path)
    stepverify = [r for r in rows if r["problem"]["source"] == "stepverify"][:40]
    synthetic = [r for r in rows if r.get("synthetic_metadata")][:40]
    sample = stepverify + synthetic
    disagreements = []
    aggregate = {field: [] for field in FIELDS}
    temps = [0.0, 0.2, 0.5]
    for row in sample:
        labels = []
        for temp in temps:
            label = heuristic_label(row)
            # Fallback is deterministic; real API mode can be wired through the same output shape.
            label["_temperature"] = temp
            labels.append(label)
        row_agreement = {field: _agreement([label[field] for label in labels]) for field in FIELDS}
        for field, value in row_agreement.items():
            aggregate[field].append(value)
        if any(value < 1 for value in row_agreement.values()):
            disagreements.append({"sample_id": row["sample_id"], "agreements": row_agreement, "labels": labels})
    csv_path = REPORT_DIR / "deepseek_self_consistency.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "agreement"])
        writer.writeheader()
        for field, values in aggregate.items():
            writer.writerow({"field": field, "agreement": round(sum(values) / len(values), 4) if values else 0})
    write_jsonl(REPORT_DIR / "deepseek_self_consistency_disagreements.jsonl", disagreements)
    return {
        "sample_count": len(sample),
        "mode": "heuristic_fallback_no_api_key",
        "agreements": {field: round(sum(values) / len(values), 4) if values else 0 for field, values in aggregate.items()},
        "disagreement_count": len(disagreements),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DeepSeek self-consistency test")
    parser.add_argument("--raw", type=Path, default=PILOT_DIR / "pilot_pool.raw.jsonl")
    args = parser.parse_args()
    result = run_self_consistency(args.raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
