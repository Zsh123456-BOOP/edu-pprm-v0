from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SYNTHETIC_TYPES = [
    "arithmetic_error",
    "sign_error",
    "wrong_operation",
    "misread_given_quantity",
    "unit_conversion_error",
    "equation_setup_error",
    "substitution_error",
    "no_error_correct_trace",
    "self_corrected_error",
    "sparse_insufficient_trace",
    "final_answer_correct_process_wrong",
    "final_answer_wrong_prefix_correct",
    "hint_would_leak_answer",
]


@dataclass(frozen=True)
class Injection:
    synthetic_type: str
    student_steps: list[str]
    expected_first_wrong_step: int | None
    expected_earliest_actionable_step: int | None
    expected_intervention_needed: bool | str
    expected_minimal_repair_type: str
    expected_hint_level: str
    expected_leakage_constraint: str
    injected_error_step: int | None
    injected_error_type: str | None
    repair_target: str | None


def _base_steps(row: dict[str, Any]) -> list[str]:
    steps = [str(step) for step in row.get("gold_solution_steps", []) if step]
    if len(steps) >= 2:
        return steps[: min(4, len(steps))]
    solution = row.get("gold_solution")
    return [str(solution)] if solution else ["Work from the problem statement."]


def inject_trace(row: dict[str, Any], synthetic_type: str) -> Injection:
    steps = _base_steps(row)
    answer = row.get("gold_answer")
    first = steps[0] if steps else "Start from the given quantities."
    second = steps[1] if len(steps) > 1 else "Continue the computation."

    templates: dict[str, Injection] = {
        "arithmetic_error": Injection(
            synthetic_type,
            [first, "I compute the local expression incorrectly, so the intermediate value is off by 2.", *steps[1:]],
            2,
            2,
            True,
            "ask_to_recompute_local_expression",
            "low",
            "do_not_solve_next_step",
            2,
            "arithmetic_error",
            "local arithmetic expression",
        ),
        "sign_error": Injection(
            synthetic_type,
            [first, "When moving the term, I keep the same sign instead of changing it.", *steps[1:]],
            2,
            2,
            True,
            "ask_to_check_operation_or_formula",
            "medium",
            "can_name_error_type",
            2,
            "sign_error",
            "sign change in the transformed expression",
        ),
        "wrong_operation": Injection(
            synthetic_type,
            ["I use addition where the relation calls for multiplication.", second, *steps[2:]],
            1,
            1,
            True,
            "ask_to_check_operation_or_formula",
            "medium",
            "can_name_error_type",
            1,
            "wrong_operation",
            "operation chosen in step 1",
        ),
        "misread_given_quantity": Injection(
            synthetic_type,
            ["I treat one given quantity as if it described a different object.", second, *steps[2:]],
            1,
            1,
            True,
            "ask_to_reinterpret_given_quantity",
            "medium",
            "do_not_solve_next_step",
            1,
            "misread_given_quantity",
            "meaning of the given quantity",
        ),
        "unit_conversion_error": Injection(
            synthetic_type,
            ["I convert the units by using the wrong scale factor.", second, *steps[2:]],
            1,
            1,
            True,
            "ask_to_check_unit_conversion",
            "medium",
            "can_show_micro_example",
            1,
            "unit_conversion_error",
            "unit conversion factor",
        ),
        "equation_setup_error": Injection(
            synthetic_type,
            ["I write an equation that does not match the relationship in the problem.", second, *steps[2:]],
            1,
            1,
            True,
            "ask_to_rewrite_equation_or_expression",
            "medium",
            "do_not_solve_next_step",
            1,
            "equation_setup_error",
            "equation setup",
        ),
        "substitution_error": Injection(
            synthetic_type,
            [first, "I substitute the wrong given value into the otherwise relevant expression.", *steps[1:]],
            2,
            2,
            True,
            "ask_to_reinterpret_given_quantity",
            "low",
            "do_not_solve_next_step",
            2,
            "substitution_error",
            "substituted value",
        ),
        "no_error_correct_trace": Injection(
            synthetic_type,
            steps,
            None,
            None,
            False,
            "no_intervention_needed",
            "none",
            "do_not_reveal_final_answer",
            None,
            None,
            None,
        ),
        "self_corrected_error": Injection(
            synthetic_type,
            ["I first compute a local value incorrectly.", "Wait, that local computation was wrong; I recompute it correctly.", *steps[:2]],
            1,
            None,
            False,
            "no_intervention_needed",
            "none",
            "do_not_reveal_final_answer",
            1,
            "self_corrected_error",
            None,
        ),
        "sparse_insufficient_trace": Injection(
            synthetic_type,
            [f"Answer: {answer}" if answer is not None else "I know the answer."],
            None,
            None,
            "uncertain",
            "insufficient_information",
            "medium",
            "can_point_to_local_step_only",
            None,
            "sparse_insufficient_trace",
            None,
        ),
        "final_answer_correct_process_wrong": Injection(
            synthetic_type,
            ["I use an invalid intermediate computation.", f"However, I state the final answer as {answer}." if answer else "However, I state the remembered final answer."],
            1,
            1,
            True,
            "ask_to_recompute_local_expression",
            "medium",
            "do_not_solve_next_step",
            1,
            "final_answer_correct_process_wrong",
            "invalid intermediate computation",
        ),
        "final_answer_wrong_prefix_correct": Injection(
            synthetic_type,
            [*steps[:2], "I copy the final answer incorrectly at the end."],
            3 if len(steps[:2]) == 2 else 2,
            3 if len(steps[:2]) == 2 else 2,
            True,
            "ask_to_compare_with_problem_condition",
            "low",
            "do_not_reveal_final_answer",
            3 if len(steps[:2]) == 2 else 2,
            "final_answer_wrong_prefix_correct",
            "final answer transcription",
        ),
        "hint_would_leak_answer": Injection(
            synthetic_type,
            ["I choose a short final answer without showing work."],
            None,
            None,
            "uncertain",
            "insufficient_information",
            "forbidden_full_solution",
            "do_not_reveal_final_answer",
            None,
            "hint_would_leak_answer",
            None,
        ),
    }
    return templates[synthetic_type]
