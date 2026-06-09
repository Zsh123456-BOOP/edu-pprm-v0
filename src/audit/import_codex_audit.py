from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.audit.common import BLIND_PATH, CODEX_LABELS_PATH, CODEX_TEMPLATE_PATH, validate_audit_label
from src.data.common import read_jsonl_file, write_jsonl

TEMPLATE_PATH = CODEX_TEMPLATE_PATH
MANUAL_LABELS_PATH = CODEX_LABELS_PATH


def template_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": row["sample_id"],
        "annotator": "codex_manual_proxy",
        "first_wrong_step": None,
        "earliest_actionable_step": None,
        "intervention_needed": "uncertain",
        "minimal_repair_type": "insufficient_information",
        "repair_target": None,
        "hint_level": "low",
        "leakage_constraint": "do_not_reveal_final_answer",
        "confidence": 0.0,
        "rationale": "",
    }


def validate_labels(path: Path, expected_annotator: str) -> list[dict[str, Any]]:
    labels = read_jsonl_file(path)
    errors = []
    for label in labels:
        label_errors = validate_audit_label(label, expected_annotator=expected_annotator)
        if label_errors:
            errors.append({"sample_id": label.get("sample_id"), "errors": label_errors})
    if errors:
        raise SystemExit(json.dumps(errors, ensure_ascii=False, indent=2))
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or validate Codex manual proxy audit labels")
    parser.add_argument("--blind", default=str(BLIND_PATH))
    parser.add_argument("--template", default=str(TEMPLATE_PATH))
    parser.add_argument("--labels", default=str(MANUAL_LABELS_PATH))
    parser.add_argument("--write-template", action="store_true")
    args = parser.parse_args()
    blind = read_jsonl_file(Path(args.blind))
    if args.write_template or not Path(args.template).exists():
        write_jsonl(Path(args.template), [template_row(row) for row in blind])
    labels_path = Path(args.labels)
    if labels_path.exists():
        labels = validate_labels(labels_path, "codex_manual_proxy")
        print(json.dumps({"template": args.template, "labels": args.labels, "label_count": len(labels), "validation": "passed"}, indent=2))
    else:
        print(json.dumps({"template": args.template, "labels": args.labels, "label_count": 0, "validation": "pending_manual_labels"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
