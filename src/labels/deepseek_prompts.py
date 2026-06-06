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
