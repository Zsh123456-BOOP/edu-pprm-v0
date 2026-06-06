from __future__ import annotations

from typing import Any

from src.data.common import EXTERNAL_EVAL_DIR, REPORT_DIR, default_arg_parser, fetch_hf_rows, summarize_source, write_jsonl

FIELDS = ["problem_text", "student_solution_raw", "first_wrong_step_source", "source_split", "final_answer_correct"]


def convert(row: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "source": "processbench",
        "source_id": row.get("id") or f"processbench_gsm8k_{index}",
        "source_split": "gsm8k",
        "problem_text": row.get("problem"),
        "student_solution_raw": row.get("steps"),
        "first_wrong_step_source": row.get("label"),
        "final_answer_correct": row.get("final_answer_correct"),
        "metadata": {"generator": row.get("generator")},
    }


def load(limit: int) -> list[dict[str, Any]]:
    raw = fetch_hf_rows("Qwen/ProcessBench", "default", "gsm8k", limit)
    return [convert(row, index) for index, row in enumerate(raw)]


def assert_external_only(path: str) -> None:
    if "external_eval" not in path:
        raise ValueError("ProcessBench must only be written under data/external_eval")


def main() -> int:
    parser = default_arg_parser("Load ProcessBench external-eval small sample")
    args = parser.parse_args()
    rows = load(args.limit)
    output_path = EXTERNAL_EVAL_DIR / "processbench.external_eval.raw.jsonl"
    assert_external_only(str(output_path))
    write_jsonl(output_path, rows)
    summarize_source(
        source="processbench",
        rows=rows,
        fields=FIELDS,
        output_path=REPORT_DIR / "processbench_summary.json",
        examples_path=REPORT_DIR / "processbench_20_examples.jsonl",
        notes=["External eval only; split guard prevents writing into train/interim outputs."],
        mappable_fields={"first_wrong_step": "label"},
        unmappable_fields={
            "error_category": "not annotated",
            "error_description": "not annotated",
            "earliest_actionable_step": "not annotated",
            "minimal_repair_type": "not annotated",
            "hint_level": "not annotated",
            "leakage_constraint": "not annotated",
        },
    )
    print(f"wrote {len(rows)} processbench rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
