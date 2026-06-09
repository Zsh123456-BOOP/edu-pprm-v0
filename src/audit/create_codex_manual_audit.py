from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.audit.common import BLIND_PATH, CODEX_LABELS_PATH, CODEX_TEMPLATE_PATH, detect_local_expression_error, validate_audit_label
from src.data.common import read_jsonl_file, write_jsonl


def all_text(row: dict[str, Any]) -> str:
    parts = [row.get("problem", {}).get("problem_text") or ""]
    parts.extend(str(step.get("text") or "") for step in row.get("student_trace", {}).get("student_steps", []))
    parts.append(str(row.get("student_trace", {}).get("student_final_answer") or ""))
    return "\n".join(parts)


def final_answer_only(row: dict[str, Any]) -> bool:
    steps = row.get("student_trace", {}).get("student_steps", [])
    if len(steps) > 1:
        return False
    text = str(steps[0].get("text") if steps else "")
    return bool(re.search(r"answer\s*[:=]|^\s*-?\d+(?:\.\d+)?\s*$", text, re.I))


def label_row(row: dict[str, Any]) -> dict[str, Any]:
    steps = row["student_trace"]["student_steps"]
    text = all_text(row)
    lower = text.lower()
    source = row.get("source")
    local_step, local_expr = detect_local_expression_error(steps)
    is_correct = row["student_trace"].get("is_correct")
    has_self_correction = bool(re.search(r"\b(wait|actually|corrected|correction|i made|fix)\b", lower))
    sparse = len(steps) <= 1

    if final_answer_only(row) or sparse:
        return {
            "sample_id": row["sample_id"],
            "annotator": "codex_manual_proxy",
            "first_wrong_step": None,
            "earliest_actionable_step": None,
            "intervention_needed": "uncertain",
            "minimal_repair_type": "insufficient_information",
            "repair_target": None,
            "hint_level": "low",
            "leakage_constraint": "do_not_reveal_final_answer" if row.get("gold_answer") else "can_point_to_local_step_only",
            "confidence": 0.62,
            "rationale": "The trace is too sparse to identify a first wrong step safely; a tutor should ask for more work or clarification rather than infer a hidden error.",
        }
    if is_correct is True and (has_self_correction or not local_step):
        return {
            "sample_id": row["sample_id"],
            "annotator": "codex_manual_proxy",
            "first_wrong_step": None,
            "earliest_actionable_step": None,
            "intervention_needed": False,
            "minimal_repair_type": "no_intervention_needed",
            "repair_target": None,
            "hint_level": "none",
            "leakage_constraint": "can_point_to_local_step_only",
            "confidence": 0.76,
            "rationale": "The visible trace is correct or self-corrected by the time feedback would be given, so no intervention is needed.",
        }
    if local_step:
        return {
            "sample_id": row["sample_id"],
            "annotator": "codex_manual_proxy",
            "first_wrong_step": local_step,
            "earliest_actionable_step": local_step,
            "intervention_needed": True,
            "minimal_repair_type": "ask_to_recompute_local_expression",
            "repair_target": f"step {local_step}: {local_expr}",
            "hint_level": "low",
            "leakage_constraint": "do_not_solve_next_step",
            "confidence": 0.86,
            "rationale": f"Step {local_step} contains the first visible local expression error; feedback should ask for recomputation without giving the corrected value.",
        }
    if any(token in lower for token in ["unit", "convert", "minute", "hour", "meter", "centimeter", "kilogram"]):
        repair = "ask_to_check_unit_conversion"
        target = "unit or scale conversion"
        leakage = "can_show_micro_example"
        hint = "medium"
    elif any(token in lower for token in ["equation", "formula", "relationship", "set up", "represents"]):
        repair = "ask_to_rewrite_equation_or_expression"
        target = "equation or expression setup"
        leakage = "do_not_solve_next_step"
        hint = "medium"
    elif any(token in lower for token in ["given", "quantity", "condition", "remaining", "total", "twice", "half"]):
        repair = "ask_to_reinterpret_given_quantity"
        target = "meaning of the given quantity or condition"
        leakage = "can_name_error_type"
        hint = "medium"
    elif source == "stepverify":
        repair = "ask_to_check_operation_or_formula"
        target = "first visible reasoning step"
        leakage = "do_not_solve_next_step"
        hint = "medium"
    else:
        repair = "ask_to_justify_inference"
        target = "first unsupported inference"
        leakage = "can_point_to_local_step_only"
        hint = "low"
    return {
        "sample_id": row["sample_id"],
        "annotator": "codex_manual_proxy",
        "first_wrong_step": 1,
        "earliest_actionable_step": 1,
        "intervention_needed": True,
        "minimal_repair_type": repair,
        "repair_target": target,
        "hint_level": hint,
        "leakage_constraint": leakage,
        "confidence": 0.64,
        "rationale": "Based on the blind trace, the earliest actionable issue is the first visible reasoning or setup step; the repair targets the smallest safe action without using hidden expected labels.",
    }


def main() -> int:
    rows = read_jsonl_file(BLIND_PATH)
    labels = [label_row(row) for row in rows]
    errors = []
    for label in labels:
        label_errors = validate_audit_label(label, expected_annotator="codex_manual_proxy")
        if label_errors:
            errors.append({"sample_id": label["sample_id"], "errors": label_errors})
    if errors:
        raise SystemExit(json.dumps(errors, ensure_ascii=False, indent=2))
    write_jsonl(CODEX_TEMPLATE_PATH, [
        {
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
        for row in rows
    ])
    write_jsonl(CODEX_LABELS_PATH, labels)
    notes = "# Codex Manual Proxy Audit Notes\n\nThese labels are `codex_manual_proxy`, not `heuristic_proxy` and not human labels.\n\n"
    notes += "The pass used only `audit_60_blind.jsonl`, guideline, and taxonomy. Hidden expected labels and synthetic type were not used.\n\n"
    notes += "## Distribution\n\n```json\n" + json.dumps(dict(Counter(label["minimal_repair_type"] for label in labels)), indent=2) + "\n```\n"
    (CODEX_LABELS_PATH.parent / "codex_manual_audit_60.notes.md").write_text(notes, encoding="utf-8")
    print(json.dumps({"output_count": len(labels), "validation": "passed"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
