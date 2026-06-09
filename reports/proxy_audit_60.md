# Proxy Audit 60

These labels are proxy adjudicated labels, not human gold labels.

## 1. Audit Motivation

The audit tests whether synthetic intent labels and strict verifier status are reliable enough before any silver scaling, verifier training, or model training.

## 2. Data Leakage Prevention

First-pass Codex and DeepSeek proxy annotators read only `data/audit/audit_60_blind.jsonl`, the guideline, and taxonomy. Expected labels and synthetic types are held in `audit_60_analysis_private.jsonl` and used only in this final validity audit.

## 3. Audit Batch Composition

The manifest contains 60 metric samples plus 8 calibration boundary cases.

## 4. Codex Annotation Protocol

Codex manual proxy first pass used the blind view only and wrote `data/audit/codex_manual_audit_60.labels.jsonl`.
The deterministic `heuristic_proxy` baseline is retained separately at `data/audit/heuristic_proxy_baseline.labels.jsonl` and is not the main result.

## 5. DeepSeek Annotation Protocol

DeepSeek audit uses full prompt only. If API is unavailable, dry-run prompts are generated and no labels are fabricated.

```json
{
  "status": "completed_with_failures",
  "input_count": 68,
  "output_count": 65,
  "failure_count": 3,
  "pending_count": 0,
  "model": "deepseek-v4-pro",
  "workers": 1,
  "prompt": "full",
  "repair_distribution": {
    "no_intervention_needed": 41,
    "ask_to_reinterpret_given_quantity": 8,
    "ask_to_recompute_local_expression": 7,
    "ask_to_compare_with_problem_condition": 3,
    "ask_to_check_operation_or_formula": 3,
    "ask_to_substitute_back": 1,
    "insufficient_information": 2
  },
  "note": "No labels were fabricated for failed samples; remaining missing rows are recorded as failures."
}
```

## 6. Agreement Results

```json
{
  "status": "completed",
  "metric_sample_count": 60,
  "compared_count": 57,
  "first_wrong_step_exact_agreement": 0.7544,
  "first_wrong_step_off_by_one_agreement": 0.7895,
  "earliest_actionable_step_exact_agreement": 0.7544,
  "intervention_needed_agreement": 0.7193,
  "minimal_repair_type_exact_agreement": 0.5789,
  "minimal_repair_type_coarse_agreement": 0.6316,
  "hint_level_agreement": 0.6316,
  "leakage_constraint_agreement": 0.2632,
  "mean_confidence_gap": 0.2577,
  "disagreement_count": 131,
  "note": "If 11-class agreement is low but 6-class agreement is much higher, this suggests the taxonomy may be too fine-grained rather than the task being invalid."
}
```

## 7. Disagreement Adjudication Results

```json
{
  "status": "completed",
  "count": 60,
  "decision_distribution": {
    "hybrid": 34,
    "neither_uncertain": 16,
    "codex_preferred": 10
  },
  "note": "proxy_adjudicated_60.jsonl is proxy adjudicated labels only, not human gold labels."
}
```

## 8. Expected-label Validity Results

```json
{
  "status": "completed",
  "synthetic_metric_count": 50,
  "expected_vs_codex_acc": 0.5267,
  "expected_vs_deepseek_acc": 0.5,
  "expected_vs_adjudicated_acc": 0.5067,
  "strict_pass_precision_against_adjudicated": 0.8,
  "strict_fail_bad_rate": 0.7,
  "expected_label_valid_full": 0.04,
  "expected_label_valid_partial_only": 0.56,
  "expected_label_valid_partial_or_full": 0.6,
  "expected_label_valid_false": 0.4,
  "first_wrong_step_diff_ratio": 0.0,
  "minimal_repair_type_coarse_agreement_expected_vs_adjudicated": 0.5,
  "uncertain_rate": 0.3333,
  "synthetic_types_with_invalid_cases": {
    "sign_error": 4,
    "equation_setup_error": 4,
    "no_error_correct_trace": 3,
    "arithmetic_error": 1,
    "final_answer_correct_process_wrong": 4,
    "misread_given_quantity": 1,
    "final_answer_wrong_prefix_correct": 2,
    "unit_conversion_error": 1
  },
  "go_no_go": {
    "deepseek_audit_success": "65/68",
    "deepseek_audit_success>=60/68": true,
    "codex_manual_vs_deepseek_first_wrong_off_by_one>=0.80": false,
    "minimal_repair_type_coarse_agreement>=0.70": false,
    "intervention_needed_agreement_including_uncertain>=0.75": false,
    "expected_vs_adjudicated_partial_or_full>=0.70": false,
    "strict_pass_precision>=0.70": true,
    "leakage_agreement_report_only": 0.2632,
    "first_wrong_vs_earliest_diff_report_only": 0.0,
    "recommendation": "continue_taxonomy_validation_only_no_training_no_silver_scaling"
  }
}
```

## 9. Taxonomy Failure Modes

Likely failure modes are over-fine repair labels, unclear leakage boundaries, and sparse traces where first wrong step is not identifiable.

## 10. Go / No-Go Decision

No training or silver scaling is allowed unless the proxy audit Go standards pass. Current recommendation is stored in `expected_label_validity_60.json`.

## 11. Recommended Next Step

If thresholds fail, refine generation, verifier, or taxonomy before scaling. The next stable subproblem is validating `first_wrong_step -> minimal_repair_type / hint_level / leakage_constraint`; `earliest_actionable_step` is retained as a boundary-case metric rather than the main Go criterion.

## Validation

- Audit command chain completed.
- `python3 -m compileall -q src`: passed.
- `python3 -m src.labels.taxonomy --check`: passed.
- Blind leakage scan: passed.
- Secret scan excluding `.env`: passed.
- `python3 -m pytest`: unavailable, `No module named pytest`.
