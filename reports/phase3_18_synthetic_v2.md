# Phase 3.18 Synthetic v2 Repair Taxonomy Evaluation

WARNING: expected labels are synthetic intent labels, not gold labels.

These are automatic comparisons against synthetic intent labels. They are not human gold results.

## Decision

Current automatic decision: **Pause for teacher spot-check. Do not train, do not
expand to 300-500 silver, and do not train a verifier.**

What passed:

- Generated 111 valid basic traces from a target of 150.
- Strict verifier retained 103 rows, clearing the minimum 100-row gate.
- DeepSeek blind labeling succeeded on 103/103 after type normalization.
- `first_wrong_step_off_by_one_acc = 0.8738`, above the 0.80 gate.
- `intervention_needed_acc = 0.8835`, above the 0.80 gate.
- No single repair class dominates the output distribution.

What failed:

- `minimal_repair_coarse_6_acc = 0.6505`, below the 0.70 gate.
- `leakage_constraint_acc = 0.1748`, confirming leakage should remain auxiliary.
- `first_wrong_step != earliest_actionable_step` is only 0.0485, so
  earliest-actionable remains boundary-only.

## Type-Level Read

Likely retain:

- `arithmetic_error`: strong local computation signal.
- `misread_given_quantity`: acceptable quantity/condition signal.
- `no_error_correct_trace`: stable no-intervention signal.
- `final_answer_wrong_prefix_correct`: useful boundary type.

Needs rewrite before scaling:

- `wrong_operation`, `equation_setup_error`, `unit_conversion_error`: first-error
  location is stable, but DeepSeek often maps these into quantity/condition
  rather than equation/formula.
- `substitution_error`: expected as verification_check, but DeepSeek did not
  recover that category in this batch.
- `sparse_insufficient_trace`: uncertainty behavior remains weak.

Stress-only:

- `hint_would_leak_answer`: useful for leakage/hint stress testing, not as core
  repair-taxonomy data.

## Teacher Spot-Check

Teacher-visible files:

- `docs/phase3_18_teacher_spotcheck_instructions.md`
- `data/manual/phase3_18_teacher_spotcheck_24.blind.jsonl`
- `data/manual/phase3_18_teacher_spotcheck_24.template.csv`
- `data/manual/phase3_18_teacher_spotcheck_24.template.jsonl`

Private file, do not send to teachers:

- `data/manual/phase3_18_teacher_spotcheck_24.private.jsonl`

The teacher spot-check should answer whether the 0.6505 coarse repair score is
caused mainly by synthetic intent labels being wrong, ambiguous 6-class
definitions, or DeepSeek blind labels being wrong.

## Verification

Passed:

- `python3 -m json.tool configs/synthetic_type_policy.yaml`
- `python3 -m compileall -q src`
- `python3 -m src.labels.lint_boundary_cases`
- `python3 -m src.data.validate_schema --jsonl data/pilot/synthetic_v2_150.autolabeled.jsonl`
- secret scan excluding `.env`, PDF files, and `data/cache/**`

Unavailable:

- `python3 -m pytest` failed because `pytest` is not installed in the local Python environment.

```json
{
  "phase": "3.18",
  "warning": "WARNING: expected labels are synthetic intent labels, not gold labels.",
  "count": 103,
  "first_wrong_step_exact_acc": 0.8447,
  "first_wrong_step_off_by_one_acc": 0.8738,
  "intervention_needed_acc": 0.8835,
  "minimal_repair_type_exact_acc": 0.5825,
  "minimal_repair_type_macro_f1": 0.3914,
  "minimal_repair_coarse_6_acc": 0.6505,
  "minimal_repair_coarse_6_macro_f1": 0.5594,
  "hint_level_acc": 0.7379,
  "leakage_constraint_acc": 0.1748,
  "first_wrong_step_not_equal_earliest_actionable_step_ratio": 0.0485,
  "intervention_needed_false_uncertain_ratio": 0.301,
  "minimal_repair_type_distribution": {
    "ask_to_recompute_local_expression": 22,
    "no_intervention_needed": 29,
    "ask_to_reinterpret_given_quantity": 20,
    "ask_to_check_operation_or_formula": 6,
    "ask_to_compare_with_problem_condition": 17,
    "ask_to_check_unit_conversion": 3,
    "insufficient_information": 2,
    "ask_clarifying_question": 4
  },
  "minimal_repair_coarse_confusion": {
    "local_computation": {
      "local_computation": 12,
      "no_intervention": 1
    },
    "equation_or_formula": {
      "local_computation": 4,
      "quantity_or_condition": 13,
      "equation_or_formula": 9
    },
    "quantity_or_condition": {
      "quantity_or_condition": 16,
      "no_intervention": 1,
      "local_computation": 3
    },
    "verification_check": {
      "quantity_or_condition": 5,
      "local_computation": 3
    },
    "no_intervention": {
      "no_intervention": 24,
      "quantity_or_condition": 1
    },
    "insufficient_or_clarify": {
      "insufficient_or_clarify": 6,
      "quantity_or_condition": 2,
      "no_intervention": 3
    }
  },
  "per_synthetic_type": {
    "arithmetic_error": {
      "count": 13,
      "first_wrong_off_by_one": 12,
      "coarse_repair_correct": 12,
      "intervention_correct": 12,
      "first_wrong_off_by_one_acc": 0.9231,
      "coarse_repair_acc": 0.9231,
      "intervention_acc": 0.9231
    },
    "wrong_operation": {
      "count": 9,
      "first_wrong_off_by_one": 9,
      "coarse_repair_correct": 4,
      "intervention_correct": 9,
      "first_wrong_off_by_one_acc": 1.0,
      "coarse_repair_acc": 0.4444,
      "intervention_acc": 1.0
    },
    "misread_given_quantity": {
      "count": 7,
      "first_wrong_off_by_one": 6,
      "coarse_repair_correct": 6,
      "intervention_correct": 6,
      "first_wrong_off_by_one_acc": 0.8571,
      "coarse_repair_acc": 0.8571,
      "intervention_acc": 0.8571
    },
    "equation_setup_error": {
      "count": 7,
      "first_wrong_off_by_one": 7,
      "coarse_repair_correct": 2,
      "intervention_correct": 7,
      "first_wrong_off_by_one_acc": 1.0,
      "coarse_repair_acc": 0.2857,
      "intervention_acc": 1.0
    },
    "unit_conversion_error": {
      "count": 10,
      "first_wrong_off_by_one": 10,
      "coarse_repair_correct": 3,
      "intervention_correct": 10,
      "first_wrong_off_by_one_acc": 1.0,
      "coarse_repair_acc": 0.3,
      "intervention_acc": 1.0
    },
    "substitution_error": {
      "count": 8,
      "first_wrong_off_by_one": 8,
      "coarse_repair_correct": 0,
      "intervention_correct": 8,
      "first_wrong_off_by_one_acc": 1.0,
      "coarse_repair_acc": 0.0,
      "intervention_acc": 1.0
    },
    "no_error_correct_trace": {
      "count": 15,
      "first_wrong_off_by_one": 15,
      "coarse_repair_correct": 15,
      "intervention_correct": 15,
      "first_wrong_off_by_one_acc": 1.0,
      "coarse_repair_acc": 1.0,
      "intervention_acc": 1.0
    },
    "self_corrected_error": {
      "count": 10,
      "first_wrong_off_by_one": 1,
      "coarse_repair_correct": 9,
      "intervention_correct": 9,
      "first_wrong_off_by_one_acc": 0.1,
      "coarse_repair_acc": 0.9,
      "intervention_acc": 0.9
    },
    "final_answer_wrong_prefix_correct": {
      "count": 13,
      "first_wrong_off_by_one": 13,
      "coarse_repair_correct": 10,
      "intervention_correct": 13,
      "first_wrong_off_by_one_acc": 1.0,
      "coarse_repair_acc": 0.7692,
      "intervention_acc": 1.0
    },
    "sparse_insufficient_trace": {
      "count": 8,
      "first_wrong_off_by_one": 6,
      "coarse_repair_correct": 3,
      "intervention_correct": 2,
      "first_wrong_off_by_one_acc": 0.75,
      "coarse_repair_acc": 0.375,
      "intervention_acc": 0.25
    },
    "hint_would_leak_answer": {
      "count": 3,
      "first_wrong_off_by_one": 3,
      "coarse_repair_correct": 3,
      "intervention_correct": 0,
      "first_wrong_off_by_one_acc": 1.0,
      "coarse_repair_acc": 1.0,
      "intervention_acc": 0.0
    }
  },
  "go_no_go": {
    "count>=100": true,
    "first_wrong_step_off_by_one_acc>=0.80": true,
    "minimal_repair_coarse_6_acc>=0.70": false,
    "intervention_needed_acc>=0.80": true,
    "single_repair_type<=0.70": true
  }
}
```
