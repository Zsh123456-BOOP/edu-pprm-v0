from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data.common import ROOT


def load_prompt_context() -> str:
    guideline = (ROOT / "docs" / "annotation_guideline.md").read_text(encoding="utf-8")
    taxonomy = (ROOT / "configs" / "label_taxonomy.yaml").read_text(encoding="utf-8")
    return f"ANNOTATION_GUIDELINE\\n{guideline}\\n\\nLABEL_TAXONOMY\\n{taxonomy}"


def sample_payload(sample: dict[str, Any], include_known: bool = True) -> dict[str, Any]:
    payload = {
        "sample_id": sample["sample_id"],
        "problem": sample["problem"],
        "student_trace": sample["student_trace"],
    }
    if include_known and sample["problem"]["source"] == "stepverify":
        payload["known_dataset_annotation"] = sample["existing_labels"]
    elif include_known and sample["problem"]["source"] not in {"gsm8k", "math"}:
        payload["known_dataset_annotation"] = sample["existing_labels"]
    return payload


def build_label_messages(sample: dict[str, Any]) -> list[dict[str, str]]:
    context = load_prompt_context()
    user_payload = sample_payload(sample, include_known=True)
    return [
        {
            "role": "system",
            "content": (
                "You label math student traces for Edu-PPRM. Return JSON only. "
                "Do not include markdown or prose outside JSON. Independently judge first_wrong_step before pedagogical labels."
            ),
        },
        {
            "role": "user",
            "content": (
                context
                + "\\n\\nReturn exactly this JSON object with keys: "
                + json.dumps(
                    {
                        "first_wrong_step": "integer or null",
                        "earliest_actionable_step": "integer or null",
                        "intervention_needed": "true | false | uncertain",
                        "minimal_repair_type": "one taxonomy value",
                        "repair_target": "string or null",
                        "hint_level": "one taxonomy value",
                        "leakage_constraint": "one taxonomy value",
                        "actionable_diff_reason": "string or null",
                        "confidence": "number 0..1",
                        "short_rationale": "short string",
                    },
                    ensure_ascii=False,
                )
                + "\\n\\nSAMPLE\\n"
                + json.dumps(user_payload, ensure_ascii=False)
            ),
        },
    ]


def build_compact_label_messages(sample: dict[str, Any]) -> list[dict[str, str]]:
    allowed = {
        "minimal_repair_type": [
            "no_intervention_needed",
            "ask_to_recompute_local_expression",
            "ask_to_reinterpret_given_quantity",
            "ask_to_rewrite_equation_or_expression",
            "ask_to_check_operation_or_formula",
            "ask_to_check_unit_conversion",
            "ask_to_justify_inference",
            "ask_to_compare_with_problem_condition",
            "ask_to_substitute_back",
            "ask_clarifying_question",
            "insufficient_information",
        ],
        "hint_level": ["none", "low", "medium", "high", "forbidden_full_solution"],
        "leakage_constraint": [
            "do_not_reveal_final_answer",
            "do_not_solve_next_step",
            "can_point_to_local_step_only",
            "can_name_error_type",
            "can_show_micro_example",
        ],
    }
    payload = {
        "sample_id": sample["sample_id"],
        "problem": sample["problem"],
        "student_trace": sample["student_trace"],
        "known_dataset_annotation": sample["existing_labels"] if sample["problem"]["source"] == "stepverify" else None,
        "allowed_labels": allowed,
    }
    return [
        {
            "role": "system",
            "content": "Return JSON only. Label a math student trace. Do not reveal final answers.",
        },
        {
            "role": "user",
            "content": (
                "Definitions: first_wrong_step is the first mathematically wrong step. "
                "earliest_actionable_step is the earliest step where a tutor should intervene and may differ. "
                "If self-corrected use intervention_needed=false. If too sparse use uncertain and insufficient_information. "
                "Return keys: first_wrong_step, earliest_actionable_step, intervention_needed, minimal_repair_type, "
                "repair_target, hint_level, leakage_constraint, actionable_diff_reason, confidence, short_rationale.\n"
                + json.dumps(payload, ensure_ascii=False)
            ),
        },
    ]
