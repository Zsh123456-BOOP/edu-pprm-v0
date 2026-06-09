# Heuristic Proxy Baseline Notes

These labels were produced from `data/audit/audit_60_blind.jsonl` only by a deterministic heuristic baseline. They are not the main Codex manual proxy labels, not human labels, and not gold labels.

## Difficult Distinctions

- `ask_to_rewrite_equation_or_expression` vs `ask_to_check_operation_or_formula` remains ambiguous when a trace states a wrong relationship in prose.
- `ask_to_compare_with_problem_condition` overlaps with quantity reinterpretation for word problems involving totals, remaining quantities, or constraints.
- `insufficient_information` is difficult when a one-step trace includes a final answer but no derivation.

## Earliest Actionable vs First Wrong

Observed first-pass cases with different values: 0.

The common reason for equality is that most synthetic traces show the first visible error at the same place where a tutor would intervene. This may indicate the synthetic traces underrepresent situations where early ambiguity is actionable before a mathematical error is explicit.

## Hint And Leakage Boundaries

- `low` vs `medium` depends on whether naming the error type would effectively solve the next step.
- `do_not_reveal_final_answer` is most relevant for short-answer traces where the local repair computes the answer directly.
- `can_show_micro_example` is useful for unit conversion but risky if the example mirrors the target numbers.

## Repair Distribution

{
  "ask_to_recompute_local_expression": 14,
  "no_intervention_needed": 27,
  "insufficient_information": 7,
  "ask_to_compare_with_problem_condition": 10,
  "ask_to_check_unit_conversion": 2,
  "ask_to_rewrite_equation_or_expression": 3,
  "ask_to_justify_inference": 5
}

## Suggested Taxonomy Changes

- Consider merging `ask_to_rewrite_equation_or_expression` and `ask_to_check_operation_or_formula` for early pilot analysis.
- Keep `uncertain` available for `intervention_needed`; sparse traces should not be forced into true/false.
- Keep leakage labels, but expect lower agreement until examples are sharpened.
