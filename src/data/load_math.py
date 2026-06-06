from __future__ import annotations

from itertools import islice
from math import ceil
from typing import Any

from src.data.common import (
    INTERIM_DIR,
    REPORT_DIR,
    default_arg_parser,
    fetch_hf_rows,
    refresh_problem_bank,
    split_steps,
    summarize_source,
    write_jsonl,
)

CONFIGS = ["algebra", "counting_and_probability", "geometry", "intermediate_algebra", "number_theory", "prealgebra", "precalculus"]
FIELDS = ["problem_text", "gold_answer", "gold_solution", "gold_solution_steps", "source_split", "topic", "difficulty"]


def extract_boxed(solution: str | None) -> str | None:
    if not solution:
        return None
    marker = "\\boxed{"
    start = solution.rfind(marker)
    if start == -1:
        return None
    start += len(marker)
    depth = 1
    chars = []
    for char in solution[start:]:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return "".join(chars).strip()
        chars.append(char)
    return None


def convert(row: dict[str, Any], index: int, config: str) -> dict[str, Any]:
    solution = row.get("solution")
    return {
        "source": "math",
        "problem_id": f"math_{config}_train_{index}",
        "source_split": "train",
        "problem_text": row.get("problem"),
        "gold_answer": extract_boxed(solution),
        "gold_solution": solution,
        "gold_solution_steps": split_steps(solution),
        "topic": row.get("type") or config,
        "difficulty": row.get("level"),
        "metadata": {"config": config},
    }


def load(limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    per_config = max(1, ceil(limit / len(CONFIGS)))
    for config in CONFIGS:
        if len(rows) >= limit:
            break
        raw = fetch_hf_rows("EleutherAI/hendrycks_math", config, "train", per_config)
        rows.extend(convert(row, index, config) for index, row in enumerate(raw))
    return list(islice(rows, limit))


def main() -> int:
    parser = default_arg_parser("Load MATH problem-bank small sample")
    args = parser.parse_args()
    rows = load(args.limit)
    write_jsonl(INTERIM_DIR / "math.problem_bank.raw.jsonl", rows)
    refresh_problem_bank()
    summarize_source(
        source="math",
        rows=rows,
        fields=FIELDS,
        output_path=REPORT_DIR / "math_summary.json",
        examples_path=REPORT_DIR / "math_20_examples.jsonl",
        notes=["Uses train split only and samples across MATH subject configs."],
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
    print(f"wrote {len(rows)} math rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
