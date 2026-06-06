from __future__ import annotations

from typing import Any

from src.synthetic.inject_math_errors import SYNTHETIC_TYPES


def verify_synthetic_sample(sample: dict[str, Any]) -> tuple[str, str | None]:
    metadata = sample.get("synthetic_metadata") or {}
    if metadata.get("synthetic_type") not in SYNTHETIC_TYPES:
        return "failed", "unknown synthetic_type"
    if not sample.get("student_trace", {}).get("student_steps"):
        return "failed", "missing student steps"
    if metadata.get("synthetic_type") == "no_error_correct_trace" and metadata.get("expected_first_wrong_step") is not None:
        return "failed", "no_error_correct_trace has expected first wrong step"
    if metadata.get("synthetic_type") == "self_corrected_error":
        texts = " ".join((step.get("text") or "").lower() for step in sample["student_trace"]["student_steps"])
        if "wait" not in texts and "correct" not in texts:
            return "failed", "self_corrected_error lacks correction language"
    if metadata.get("synthetic_type") == "sparse_insufficient_trace" and len(sample["student_trace"]["student_steps"]) > 1:
        return "failed", "sparse_insufficient_trace has too many steps"
    return "passed", None
