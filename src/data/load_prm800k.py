from __future__ import annotations

from typing import Any

from src.data.common import INTERIM_DIR, REPORT_DIR, default_arg_parser, read_jsonl_url_prefix, summarize_source, write_jsonl

URL = "https://media.githubusercontent.com/media/openai/prm800k/main/prm800k/data/phase1_train.jsonl"
FIELDS = ["problem_text", "solution_steps", "step_correctness", "source_split"]


def _step_correctness(label: Any) -> str | None:
    if label is None:
        return None
    if isinstance(label, dict):
        if "rating" in label:
            return str(label["rating"])
        if "human_completion" in label:
            return str(label["human_completion"])
    return str(label)


def convert(row: dict[str, Any], index: int) -> dict[str, Any]:
    label = row.get("label")
    label_steps = label.get("steps", []) if isinstance(label, dict) else []
    solution_steps = []
    ratings = []
    for step in label_steps:
        if not isinstance(step, dict):
            continue
        chosen = step.get("chosen_completion")
        completions = step.get("completions") or []
        completion = completions[chosen] if isinstance(chosen, int) and chosen < len(completions) else (completions[0] if completions else {})
        if isinstance(completion, dict):
            solution_steps.append(completion.get("text"))
            ratings.append(completion.get("rating"))
    return {
        "source": "prm800k",
        "source_id": f"prm800k_phase1_train_{index}",
        "source_split": "phase1_train",
        "problem_text": (row.get("question") or {}).get("problem") if isinstance(row.get("question"), dict) else row.get("question"),
        "solution_steps": solution_steps,
        "step_correctness": ratings,
        "metadata": {
            "raw_keys": sorted(row.keys()),
            "ground_truth_answer": (row.get("question") or {}).get("ground_truth_answer") if isinstance(row.get("question"), dict) else None,
            "finish_reason": label.get("finish_reason") if isinstance(label, dict) else None,
        },
    }


def load(limit: int) -> list[dict[str, Any]]:
    raw = read_jsonl_url_prefix(URL, limit)
    return [convert(row, index) for index, row in enumerate(raw)]


def main() -> int:
    parser = default_arg_parser("Load PRM800K baseline/pretrain small sample")
    args = parser.parse_args()
    rows = load(args.limit)
    write_jsonl(INTERIM_DIR / "prm800k.step_correctness.raw.jsonl", rows)
    summarize_source(
        source="prm800k",
        rows=rows,
        fields=FIELDS,
        output_path=REPORT_DIR / "prm800k_summary.json",
        examples_path=REPORT_DIR / "prm800k_20_examples.jsonl",
        notes=["PRM800K is generic PRM supervision; do not treat it as pedagogical repair labels."],
        mappable_fields={},
        unmappable_fields={
            "first_wrong_step": "step correctness is not the same as first wrong step label",
            "error_category": "not annotated",
            "error_description": "not annotated",
            "earliest_actionable_step": "not annotated",
            "minimal_repair_type": "not annotated",
            "hint_level": "not annotated",
            "leakage_constraint": "not annotated",
        },
    )
    print(f"wrote {len(rows)} prm800k rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
