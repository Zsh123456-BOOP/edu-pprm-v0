from __future__ import annotations

from typing import Any

from src.data.validate_schema import HINT_LEVELS, LEAKAGE_CONSTRAINTS, MINIMAL_REPAIR_TYPES

REQUIRED_DEEPSEEK_LABEL_KEYS = {
    "first_wrong_step",
    "earliest_actionable_step",
    "intervention_needed",
    "minimal_repair_type",
    "repair_target",
    "hint_level",
    "leakage_constraint",
    "actionable_diff_reason",
    "confidence",
    "short_rationale",
}


def validate_deepseek_label(label: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_DEEPSEEK_LABEL_KEYS - set(label)
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")
        return errors
    if label["intervention_needed"] not in {True, False, "uncertain"}:
        errors.append("invalid intervention_needed")
    if label["minimal_repair_type"] not in (MINIMAL_REPAIR_TYPES - {None}):
        errors.append("invalid minimal_repair_type")
    if label["hint_level"] not in (HINT_LEVELS - {None}):
        errors.append("invalid hint_level")
    if label["leakage_constraint"] not in (LEAKAGE_CONSTRAINTS - {None}):
        errors.append("invalid leakage_constraint")
    confidence = label.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("confidence must be number in [0, 1]")
    for key in ["first_wrong_step", "earliest_actionable_step"]:
        if label[key] is not None and not isinstance(label[key], int):
            errors.append(f"{key} must be integer or null")
    return errors
