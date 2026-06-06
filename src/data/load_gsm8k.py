from __future__ import annotations

from typing import Any

from src.data.common import (
    INTERIM_DIR,
    REPORT_DIR,
    default_arg_parser,
    extract_gsm8k_answer,
    fetch_hf_rows,
    refresh_problem_bank,
    split_steps,
    summarize_source,
    write_jsonl,
)

FIELDS = ["problem_text", "gold_answer", "gold_solution", "gold_solution_steps", "source_split"]


def convert(row: dict[str, Any], index: int) -> dict[str, Any]:
    solution, final = extract_gsm8k_answer(row.get("answer"))
    return {
        "source": "gsm8k",
        "problem_id": f"gsm8k_train_{index}",
        "source_split": "train",
        "problem_text": row.get("question"),
        "gold_answer": final,
        "gold_solution": solution,
        "gold_solution_steps": split_steps(solution),
        "metadata": {"raw_answer": row.get("answer")},
    }


def load(limit: int) -> list[dict[str, Any]]:
    raw = fetch_hf_rows("openai/gsm8k", "main", "train", limit)
    return [convert(row, index) for index, row in enumerate(raw)]


def main() -> int:
    parser = default_arg_parser("Load GSM8K problem-bank small sample")
    args = parser.parse_args()
    rows = load(args.limit)
    write_jsonl(INTERIM_DIR / "gsm8k.problem_bank.raw.jsonl", rows)
    refresh_problem_bank()
    summarize_source(
        source="gsm8k",
        rows=rows,
        fields=FIELDS,
        output_path=REPORT_DIR / "gsm8k_summary.json",
        examples_path=REPORT_DIR / "gsm8k_20_examples.jsonl",
        notes=["Uses train split only for synthetic problem bank pilot; test split is not used."],
        mappable_fields={},
        unmappable_fields={
            "first_wrong_step": "problem bank has no student error trace",
            "error_category": "problem bank has no student error trace",
            "error_description": "problem bank has no student error trace",
            "earliest_actionable_step": "not annotated",
            "minimal_repair_type": "not annotated",
            "hint_level": "not annotated",
            "leakage_constraint": "not annotated",
        },
    )
    print(f"wrote {len(rows)} gsm8k rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
