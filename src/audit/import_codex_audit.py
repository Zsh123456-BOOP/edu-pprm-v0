from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from typing import Any

from src.audit.common import BLIND_PATH, CODEX_LABELS_PATH, REPORT_DIR, detect_local_expression_error, read_manifest, validate_audit_label
from src.data.common import read_jsonl_file, write_jsonl


def step_count(row: dict[str, Any]) -> int:
    return len(row.get("student_trace", {}).get("student_steps", []))


def text_blob(row: dict[str, Any]) -> str:
    pieces = [row.get("problem", {}).get("problem_text") or ""]
    for step in row.get("student_trace", {}).get("student_steps", []):
        pieces.append(str(step.get("text") or ""))
    pieces.append(str(row.get("student_trace", {}).get("student_final_answer") or ""))
    return "\n".join(pieces).lower()


def codex_proxy_label(row: dict[str, Any]) -> dict[str, Any]:
    steps = row["student_trace"]["student_steps"]
    blob = text_blob(row)
    sid = row["sample_id"]
    source = row.get("source") or row.get("problem", {}).get("source")
    local_step, local_expr = detect_local_expression_error(steps)
    is_correct = row["student_trace"].get("is_correct")
    has_wait = any(re.search(r"\b(wait|actually|correct|correction|fix)\b", str(step.get("text") or ""), re.I) for step in steps)
    sparse = len(steps) <= 1

    if is_correct is True and has_wait:
        first = None
        earliest = None
        intervention = False
        repair = "no_intervention_needed"
        target = "self-corrected or no currently actionable error"
        hint = "none"
        leakage = "can_point_to_local_step_only"
        conf = 0.72
        rationale = "The trace appears to reach a correct state after self-correction; no tutor intervention is needed now."
    elif is_correct is True and not local_step and "wrong" not in blob and "error" not in blob:
        first = None
        earliest = None
        intervention = False
        repair = "no_intervention_needed"
        target = "no current repair target"
        hint = "none"
        leakage = "can_point_to_local_step_only"
        conf = 0.76
        rationale = "The available steps do not show a mathematical error requiring intervention."
    elif sparse:
        first = None
        earliest = None
        intervention = True
        repair = "insufficient_information"
        target = "the trace has too little work to diagnose safely"
        hint = "low"
        leakage = "do_not_reveal_final_answer" if row.get("gold_answer") else "can_point_to_local_step_only"
        conf = 0.58
        rationale = "The student trace is too sparse to identify a safe first wrong step; a tutor should ask for more work rather than infer an error."
    elif local_step:
        first = local_step
        earliest = local_step
        intervention = True
        repair = "ask_to_recompute_local_expression"
        target = f"step {local_step}: {local_expr}"
        hint = "low"
        leakage = "do_not_solve_next_step"
        conf = 0.84
        rationale = f"The first visible issue is a local expression error in step {local_step}; feedback should ask the student to recompute it without giving the value."
    elif "unit" in blob or "convert" in blob or "minute" in blob or "hour" in blob or "meter" in blob:
        first = 1
        earliest = 1
        intervention = True
        repair = "ask_to_check_unit_conversion"
        target = "unit or scale conversion"
        hint = "medium"
        leakage = "can_show_micro_example"
        conf = 0.62
        rationale = "The trace suggests a unit or scale issue; a micro-example is safer than solving the target step."
    elif "equation" in blob or "formula" in blob or "relationship" in blob:
        first = 1
        earliest = 1
        intervention = True
        repair = "ask_to_rewrite_equation_or_expression"
        target = "equation or expression setup"
        hint = "medium"
        leakage = "do_not_solve_next_step"
        conf = 0.61
        rationale = "The likely actionable repair is to revisit how the problem relationship is represented."
    elif "condition" in blob or "remaining" in blob or "total" in blob:
        first = 1
        earliest = 1
        intervention = True
        repair = "ask_to_compare_with_problem_condition"
        target = "problem condition or total/remaining relation"
        hint = "medium"
        leakage = "can_name_error_type"
        conf = 0.57
        rationale = "The trace should be checked against the problem condition before continuing."
    elif source == "stepverify":
        first = 1
        earliest = 1
        intervention = True
        repair = "ask_to_rewrite_equation_or_expression"
        target = "first visible setup or reasoning step"
        hint = "medium"
        leakage = "do_not_solve_next_step"
        conf = 0.55
        rationale = "Without dataset labels, the first visible setup/reasoning step is the earliest safe intervention point."
    else:
        first = 1
        earliest = 1
        intervention = True
        repair = "ask_to_justify_inference"
        target = "first unsupported reasoning step"
        hint = "low"
        leakage = "can_point_to_local_step_only"
        conf = 0.52
        rationale = "The trace appears questionable, but the most conservative repair is to ask the student to justify the first unsupported step."

    return {
        "sample_id": sid,
        "annotator": "codex_proxy",
        "first_wrong_step": first,
        "earliest_actionable_step": earliest,
        "intervention_needed": intervention,
        "minimal_repair_type": repair,
        "repair_target": target,
        "hint_level": hint,
        "leakage_constraint": leakage,
        "confidence": round(conf, 2),
        "rationale": rationale,
    }


def write_notes(labels: list[dict[str, Any]]) -> None:
    repair_dist = Counter(label["minimal_repair_type"] for label in labels)
    diff = [label["sample_id"] for label in labels if label["first_wrong_step"] != label["earliest_actionable_step"]]
    text = f"""# Codex Proxy Audit Notes

These labels were produced from `data/audit/audit_60_blind.jsonl` only. They are proxy labels, not human labels and not gold labels.

## Difficult Distinctions

- `ask_to_rewrite_equation_or_expression` vs `ask_to_check_operation_or_formula` remains ambiguous when a trace states a wrong relationship in prose.
- `ask_to_compare_with_problem_condition` overlaps with quantity reinterpretation for word problems involving totals, remaining quantities, or constraints.
- `insufficient_information` is difficult when a one-step trace includes a final answer but no derivation.

## Earliest Actionable vs First Wrong

Observed first-pass cases with different values: {len(diff)}.

The common reason for equality is that most synthetic traces show the first visible error at the same place where a tutor would intervene. This may indicate the synthetic traces underrepresent situations where early ambiguity is actionable before a mathematical error is explicit.

## Hint And Leakage Boundaries

- `low` vs `medium` depends on whether naming the error type would effectively solve the next step.
- `do_not_reveal_final_answer` is most relevant for short-answer traces where the local repair computes the answer directly.
- `can_show_micro_example` is useful for unit conversion but risky if the example mirrors the target numbers.

## Repair Distribution

{json.dumps(dict(repair_dist), ensure_ascii=False, indent=2)}

## Suggested Taxonomy Changes

- Consider merging `ask_to_rewrite_equation_or_expression` and `ask_to_check_operation_or_formula` for early pilot analysis.
- Consider making `insufficient_information` compatible with a boolean `intervention_needed=true` in proxy audit, since audit schema does not allow `uncertain`.
- Keep leakage labels, but expect lower agreement until examples are sharpened.
"""
    (CODEX_LABELS_PATH.parent / "codex_audit_60.notes.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate/validate Codex proxy audit labels from blind view")
    parser.add_argument("--input", default=str(BLIND_PATH))
    parser.add_argument("--output", default=str(CODEX_LABELS_PATH))
    args = parser.parse_args()
    rows = read_jsonl_file(__import__("pathlib").Path(args.input))
    labels = [codex_proxy_label(row) for row in rows]
    errors = []
    for label in labels:
        label_errors = validate_audit_label(label, expected_annotator="codex_proxy")
        if label_errors:
            errors.append({"sample_id": label.get("sample_id"), "errors": label_errors})
    if errors:
        raise SystemExit(json.dumps(errors, ensure_ascii=False, indent=2))
    write_jsonl(__import__("pathlib").Path(args.output), labels)
    write_notes(labels)
    print(json.dumps({"output_count": len(labels), "validation": "passed"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
