from __future__ import annotations

from typing import Any

from src.data.common import INTERIM_DIR, REPORT_DIR, default_arg_parser, read_url_json, summarize_source, write_jsonl

URL = "https://raw.githubusercontent.com/NYCU-NLP-Lab/MathEDU/main/dataset/time_series_split/test.json"
FIELDS = [
    "problem_text",
    "student_solution_raw",
    "teacher_feedback",
    "correctness",
    "error_type",
    "teacher_advice",
    "has_step_level_info",
    "usable_bucket",
]


def _teacher_feedback(review: Any) -> str | None:
    if not review:
        return None
    if isinstance(review, str):
        return review
    if isinstance(review, dict):
        return "; ".join(f"{key}: {value}" for key, value in review.items() if value)
    return str(review)


def convert(row: dict[str, Any], index: int) -> dict[str, Any]:
    reason_en = row.get("the_reason_why_student_cant_solve_en")
    reason_ch = row.get("the_reason_why_student_cant_solve_ch")
    feedback = _teacher_feedback(row.get("teacher_review"))
    student_process = row.get("student_process")
    has_step = bool(student_process and ("\\\\" in student_process or "\n" in student_process))
    problem_text = row.get("problem") or row.get("question")
    usable_bucket = "step_level_candidate" if has_step and problem_text else "feedback_only_or_missing_problem"
    if not student_process:
        usable_bucket = "insufficient_fields"
    return {
        "source": "mathedu",
        "source_id": f"mathedu_{row.get('id', index)}",
        "problem_text": problem_text,
        "student_solution_raw": student_process,
        "teacher_feedback": feedback,
        "correctness": row.get("correct_or_not"),
        "error_type": reason_en or reason_ch,
        "teacher_advice": feedback or reason_en or reason_ch,
        "has_step_level_info": has_step,
        "usable_bucket": usable_bucket,
        "metadata": {
            "student_id": row.get("student_id"),
            "raw_id": row.get("id"),
            "student_answer": row.get("student_answer"),
            "reason_ch": reason_ch,
            "reason_en": reason_en,
            "teacher_review_raw": row.get("teacher_review"),
        },
    }


def load(limit: int) -> list[dict[str, Any]]:
    raw = read_url_json(URL)
    return [convert(row, index) for index, row in enumerate(raw[:limit])]


def main() -> int:
    parser = default_arg_parser("Load MathEDU small-sample raw format")
    args = parser.parse_args()
    rows = load(args.limit)
    write_jsonl(INTERIM_DIR / "mathedu.raw.jsonl", rows)
    summarize_source(
        source="mathedu",
        rows=rows,
        fields=FIELDS,
        output_path=REPORT_DIR / "mathedu_summary.json",
        examples_path=REPORT_DIR / "mathedu_20_examples.jsonl",
        notes=[
            "Public time_series_split sample has student process and correctness.",
            "The inspected JSON does not expose a reliable problem_text field in these rows.",
        ],
        mappable_fields={
            "teacher_feedback": "teacher_review / reason fields when present",
            "error_category": "the_reason_why_student_cant_solve_en/ch when present",
        },
        unmappable_fields={
            "first_wrong_step": "not step-index annotated",
            "earliest_actionable_step": "not annotated",
            "minimal_repair_type": "not annotated",
            "hint_level": "not annotated",
            "leakage_constraint": "not annotated",
        },
    )
    print(f"wrote {len(rows)} mathedu rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
