from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.data.common import REPORT_DIR, ROOT, write_json

REQUIRED_FIELDS = {
    "first_wrong_step",
    "earliest_actionable_step",
    "intervention_needed",
    "minimal_repair_type",
    "hint_level",
    "leakage_constraint",
    "reason",
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def lint_case(case: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(case)
    if missing:
        errors.append(f"case {index} missing fields: {sorted(missing)}")
        return errors
    reason = str(case.get("reason", "")).lower()
    if "mathematically correct" in reason and case.get("first_wrong_step") is not None:
        errors.append(f"case {index} says mathematically correct but first_wrong_step is not null")
    if case.get("intervention_needed") is False:
        if case.get("minimal_repair_type") != "no_intervention_needed":
            errors.append(f"case {index} intervention false requires no_intervention_needed")
        if case.get("earliest_actionable_step") is not None:
            errors.append(f"case {index} intervention false requires null earliest_actionable_step")
    if case.get("intervention_needed") == "uncertain" and case.get("minimal_repair_type") not in {
        "insufficient_information",
        "ask_clarifying_question",
    }:
        errors.append(f"case {index} uncertain requires insufficient_information or ask_clarifying_question")
    if case.get("minimal_repair_type") == "no_intervention_needed" and case.get("hint_level") != "none":
        errors.append(f"case {index} no_intervention_needed requires hint_level none")
    if case.get("earliest_actionable_step") is not None and case.get("intervention_needed") is False:
        errors.append(f"case {index} non-null earliest_actionable_step cannot have intervention false")
    return errors


def lint_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    errors = []
    for index, case in enumerate(cases, 1):
        errors.extend(lint_case(case, index))
    return {
        "case_count": len(cases),
        "passed": not errors,
        "error_count": len(errors),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Edu-PPRM annotation boundary cases")
    parser.add_argument("--path", type=Path, default=ROOT / "data" / "reports" / "boundary_cases_20.jsonl")
    args = parser.parse_args()
    report = lint_cases(load_cases(args.path))
    write_json(REPORT_DIR / "boundary_lint_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
