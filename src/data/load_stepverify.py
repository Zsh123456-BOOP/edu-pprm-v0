from __future__ import annotations

from typing import Any

from src.data.common import (
    INTERIM_DIR,
    REPORT_DIR,
    default_arg_parser,
    fetch_hf_rows,
    summarize_source,
    write_jsonl,
    write_missing_csv,
)

FIELDS = [
    "problem_text",
    "reference_solution_raw",
    "student_solution_raw",
    "first_wrong_step_source",
    "error_category_source",
    "error_description_source",
    "dialog_history",
]


def convert(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "source": "stepverify",
        "source_id": f"stepverify_train_{index}",
        "problem_text": row.get("problem"),
        "reference_solution_raw": row.get("reference_solution"),
        "student_solution_raw": row.get("student_incorrect_solution"),
        "first_wrong_step_source": row.get("incorrect_index"),
        "error_category_source": row.get("error_category"),
        "error_description_source": row.get("error_description"),
        "dialog_history": row.get("dialog_history"),
        "metadata": {
            "topic": row.get("topic"),
            "incorrect_step": row.get("incorrect_step"),
            "student_correct_response": row.get("student_correct_response"),
        },
    }


def load(limit: int) -> list[dict[str, Any]]:
    raw = fetch_hf_rows("eth-nlped/stepverify", "default", "train", limit)
    return [convert(row, index) for index, row in enumerate(raw)]


def main() -> int:
    parser = default_arg_parser("Load StepVerify small-sample raw format")
    args = parser.parse_args()
    rows = load(args.limit)
    write_jsonl(INTERIM_DIR / "stepverify.raw.jsonl", rows)
    write_missing_csv(REPORT_DIR / "stepverify_missing_fields.csv", rows, FIELDS)
    summarize_source(
        source="stepverify",
        rows=rows,
        fields=FIELDS,
        output_path=REPORT_DIR / "stepverify_summary.json",
        examples_path=REPORT_DIR / "stepverify_20_examples.jsonl",
        notes=["StepVerify maps directly to first-error baseline fields, not new repair labels."],
        mappable_fields={
            "first_wrong_step": "incorrect_index",
            "error_category": "error_category",
            "error_description": "error_description",
        },
        unmappable_fields={
            "earliest_actionable_step": "not annotated",
            "minimal_repair_type": "not annotated",
            "hint_level": "not annotated",
            "leakage_constraint": "not annotated",
        },
    )
    print(f"wrote {len(rows)} stepverify rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
