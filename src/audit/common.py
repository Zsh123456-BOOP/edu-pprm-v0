from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.data.common import DATA_DIR, REPORT_DIR, ROOT, load_json_yaml, read_jsonl_file, write_json, write_jsonl
from src.data.validate_schema import HINT_LEVELS, LEAKAGE_CONSTRAINTS, MINIMAL_REPAIR_TYPES

AUDIT_DIR = DATA_DIR / "audit"
AUDIT_V2_DIR = DATA_DIR / "audit_v2"
AUDIT_SCHEMA_PATH = ROOT / "schemas" / "audit_label.schema.json"
MANIFEST_PATH = AUDIT_DIR / "audit_60_manifest.json"
BLIND_PATH = AUDIT_DIR / "audit_60_blind.jsonl"
PRIVATE_PATH = AUDIT_DIR / "audit_60_analysis_private.jsonl"
CODEX_LABELS_PATH = AUDIT_DIR / "codex_manual_audit_60.labels.jsonl"
CODEX_TEMPLATE_PATH = AUDIT_DIR / "codex_manual_audit_60.template.jsonl"
HEURISTIC_LABELS_PATH = AUDIT_DIR / "heuristic_proxy_baseline.labels.jsonl"
DEEPSEEK_LABELS_PATH = AUDIT_DIR / "deepseek_audit_60.labels.jsonl"
ADJUDICATED_PATH = AUDIT_DIR / "proxy_adjudicated_60.jsonl"

AUDIT_REQUIRED_KEYS = {
    "sample_id",
    "annotator",
    "first_wrong_step",
    "earliest_actionable_step",
    "intervention_needed",
    "minimal_repair_type",
    "repair_target",
    "hint_level",
    "leakage_constraint",
    "confidence",
    "rationale",
}
FORBIDDEN_LABEL_KEYS = {
    "expected_first_wrong_step",
    "expected_earliest_actionable_step",
    "expected_intervention_needed",
    "expected_minimal_repair_type",
    "expected_hint_level",
    "expected_leakage_constraint",
    "synthetic_type",
    "injected_error_step",
    "injected_error_type",
}
FORBIDDEN_BLIND_TERMS = [
    "expected_",
    "synthetic_type",
    "injected_",
    "llm_verification",
    "strict_verifier_status",
    "strict_status",
    "error_category",
    "error_description",
]


def audit_label_allowed_values() -> dict[str, set[Any]]:
    return {
        "minimal_repair_type": MINIMAL_REPAIR_TYPES - {None},
        "hint_level": HINT_LEVELS - {None},
        "leakage_constraint": LEAKAGE_CONSTRAINTS - {None},
    }


def validate_audit_label(label: dict[str, Any], *, expected_annotator: str | None = None) -> list[str]:
    errors: list[str] = []
    keys = set(label)
    missing = AUDIT_REQUIRED_KEYS - keys
    extra = keys - AUDIT_REQUIRED_KEYS
    forbidden = keys & FORBIDDEN_LABEL_KEYS
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")
    if extra:
        errors.append(f"extra keys: {sorted(extra)}")
    if forbidden:
        errors.append(f"forbidden keys: {sorted(forbidden)}")
    if errors:
        return errors
    if expected_annotator and label["annotator"] != expected_annotator:
        errors.append(f"annotator must be {expected_annotator}")
    if not isinstance(label["sample_id"], str) or not label["sample_id"]:
        errors.append("sample_id must be non-empty string")
    if not isinstance(label["annotator"], str) or not label["annotator"]:
        errors.append("annotator must be non-empty string")
    for key in ["first_wrong_step", "earliest_actionable_step"]:
        if label[key] is not None and (not isinstance(label[key], int) or label[key] <= 0):
            errors.append(f"{key} must be positive integer or null")
    if label["intervention_needed"] not in {True, False, "uncertain"}:
        errors.append("intervention_needed must be true, false, or uncertain")
    allowed = audit_label_allowed_values()
    for key, values in allowed.items():
        if label[key] not in values:
            errors.append(f"invalid {key}: {label[key]}")
    if label["repair_target"] is not None and not isinstance(label["repair_target"], str):
        errors.append("repair_target must be string or null")
    if not isinstance(label["rationale"], str) or not label["rationale"].strip():
        errors.append("rationale must be non-empty string")
    confidence = label["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("confidence must be number in [0, 1]")
    return errors


def read_manifest() -> list[dict[str, Any]]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return payload["items"]


def metric_sample_ids() -> set[str]:
    return {item["sample_id"] for item in read_manifest() if item.get("included_in_metrics")}


def rows_by_id(path: Path) -> dict[str, dict[str, Any]]:
    return {row["sample_id"]: row for row in read_jsonl_file(path)}


def load_coarse_map() -> dict[str, str]:
    payload = load_json_yaml(ROOT / "configs" / "minimal_repair_coarse_map.yaml")
    mapping: dict[str, str] = {}
    for coarse, labels in payload["coarse_categories"].items():
        for label in labels:
            mapping[label] = coarse
    return mapping


def compare_expected(row: dict[str, Any], label_row: dict[str, Any]) -> dict[str, bool]:
    meta = row.get("synthetic_metadata") or {}
    return {
        "first_wrong_step": label_row.get("existing_labels", {}).get("first_wrong_step") == meta.get("expected_first_wrong_step"),
        "earliest_actionable_step": label_row.get("pedagogical_labels", {}).get("earliest_actionable_step") == meta.get("expected_earliest_actionable_step"),
        "intervention_needed": label_row.get("pedagogical_labels", {}).get("intervention_needed") == meta.get("expected_intervention_needed"),
        "minimal_repair_type": label_row.get("pedagogical_labels", {}).get("minimal_repair_type") == meta.get("expected_minimal_repair_type"),
        "hint_level": label_row.get("pedagogical_labels", {}).get("hint_level") == meta.get("expected_hint_level"),
        "leakage_constraint": label_row.get("pedagogical_labels", {}).get("leakage_constraint") == meta.get("expected_leakage_constraint"),
    }


def all_expected_match(row: dict[str, Any], label_row: dict[str, Any]) -> bool:
    return all(compare_expected(row, label_row).values())


def expected_labels_from_private(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "first_wrong_step": row.get("expected_first_wrong_step"),
        "earliest_actionable_step": row.get("expected_earliest_actionable_step"),
        "intervention_needed": row.get("expected_intervention_needed"),
        "minimal_repair_type": row.get("expected_minimal_repair_type"),
        "hint_level": row.get("expected_hint_level"),
        "leakage_constraint": row.get("expected_leakage_constraint"),
    }


def audit_fields(label: dict[str, Any], *, prefix: str = "") -> dict[str, Any]:
    mapping = {
        "first_wrong_step": label.get(f"{prefix}first_wrong_step"),
        "earliest_actionable_step": label.get(f"{prefix}earliest_actionable_step"),
        "intervention_needed": label.get(f"{prefix}intervention_needed"),
        "minimal_repair_type": label.get(f"{prefix}minimal_repair_type"),
        "hint_level": label.get(f"{prefix}hint_level"),
        "leakage_constraint": label.get(f"{prefix}leakage_constraint"),
    }
    return mapping


def agreement_rate(pairs: list[tuple[Any, Any]]) -> float | None:
    if not pairs:
        return None
    return round(sum(a == b for a, b in pairs) / len(pairs), 4)


def off_by_one_rate(pairs: list[tuple[Any, Any]]) -> float | None:
    if not pairs:
        return None
    ok = 0
    for a, b in pairs:
        if a == b:
            ok += 1
        elif isinstance(a, int) and isinstance(b, int) and abs(a - b) <= 1:
            ok += 1
    return round(ok / len(pairs), 4)


def leak_scan_blind_rows(rows: list[dict[str, Any]]) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    found = [term for term in FORBIDDEN_BLIND_TERMS if term in text]
    if found:
        raise ValueError(f"blind audit leakage terms found: {found}")


EXPR_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*([+\-*/x×])\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)")


def detect_local_expression_error(steps: list[dict[str, Any]]) -> tuple[int | None, str | None]:
    for step in steps:
        text = str(step.get("text") or "")
        for match in EXPR_RE.finditer(text):
            left = float(match.group(1))
            op = match.group(2)
            right = float(match.group(3))
            got = float(match.group(4))
            try:
                if op == "+":
                    expected = left + right
                elif op == "-":
                    expected = left - right
                elif op in {"*", "x", "×"}:
                    expected = left * right
                else:
                    if right == 0:
                        continue
                    expected = left / right
            except Exception:
                continue
            if not math.isclose(expected, got, rel_tol=1e-9, abs_tol=1e-9):
                return step.get("step_id"), match.group(0)
    return None, None


def make_markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return ""
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join([header, sep, *body])


def write_pending_report(summary_path: Path, report_path: Path, title: str, reason: str) -> dict[str, Any]:
    payload = {"status": "pending", "reason": reason}
    write_json(summary_path, payload)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(f"# {title}\n\nStatus: pending\n\nReason: {reason}\n", encoding="utf-8")
    return payload
