from __future__ import annotations

import argparse
from pathlib import Path

from src.data.common import REPORT_DIR, read_jsonl_file, write_jsonl


def generate_response(item: dict) -> str:
    condition = item["condition"]
    if condition == "T3":
        if item.get("intervention_needed") is False:
            return "Your reasoning looks consistent. Keep going and check your final wording."
        if item.get("intervention_needed") == "uncertain":
            return "Can you show the step before this answer so I can see how you got it?"
        repair = item.get("minimal_repair_type")
        target = item.get("repair_target") or f"step {item.get('earliest_actionable_step')}"
        if repair == "ask_to_recompute_local_expression":
            return f"Please recheck {target}; focus only on that local computation."
        if repair == "ask_to_reinterpret_given_quantity":
            return f"Look again at what the given quantity means in {target}; do not compute the next step yet."
        if repair == "ask_to_check_unit_conversion":
            return f"Check the unit conversion at {target} with a small analogous conversion first."
        return f"Review {target} and decide whether it matches the problem condition."
    if item.get("error_description"):
        return f"There is an issue near step {item.get('first_wrong_step')}: {item.get('error_description')} Try revising it."
    return f"Check your work near step {item.get('first_wrong_step')} and revise the next step."


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate tutor responses for T2/T3")
    parser.add_argument("--input", type=Path, default=REPORT_DIR / "tutor_auto_inputs.jsonl")
    args = parser.parse_args()
    rows = read_jsonl_file(args.input)
    outputs = []
    for row in rows:
        outputs.append({**row, "tutor_response": generate_response(row), "generation_mode": "heuristic_fallback_no_api_key"})
    write_jsonl(REPORT_DIR / "tutor_t2_t3_examples.jsonl", outputs)
    print(len(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
