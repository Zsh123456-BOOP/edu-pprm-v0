# Proxy Audit 60

These labels are proxy adjudicated labels, not human gold labels.

## 1. Audit Motivation

The audit tests whether synthetic intent labels and strict verifier status are reliable enough before any silver scaling, verifier training, or model training.

## 2. Data Leakage Prevention

First-pass Codex and DeepSeek proxy annotators read only `data/audit/audit_60_blind.jsonl`, the guideline, and taxonomy. Expected labels and synthetic types are held in `audit_60_analysis_private.jsonl` and used only in this final validity audit.

## 3. Audit Batch Composition

The manifest contains 60 metric samples plus 8 calibration boundary cases.

## 4. Codex Annotation Protocol

Codex first pass used the blind view only and wrote `data/audit/codex_audit_60.labels.jsonl`.

## 5. DeepSeek Annotation Protocol

DeepSeek audit uses full prompt only. If API is unavailable, dry-run prompts are generated and no labels are fabricated.

```json
{
  "status": "completed_with_failures",
  "input_count": 68,
  "output_count": 41,
  "failure_count": 27,
  "pending_count": 0,
  "model": "deepseek-v4-pro",
  "workers": 4,
  "prompt": "full",
  "repair_distribution": {
    "ask_to_recompute_local_expression": 5,
    "no_intervention_needed": 33,
    "ask_to_reinterpret_given_quantity": 2,
    "ask_to_check_operation_or_formula": 1
  }
}
```

## 6. Agreement Results

```json
{
  "status": "completed",
  "metric_sample_count": 60,
  "compared_count": 41,
  "first_wrong_step_exact_agreement": 0.6829,
  "first_wrong_step_off_by_one_agreement": 0.7073,
  "earliest_actionable_step_exact_agreement": 0.6829,
  "intervention_needed_agreement": 0.7805,
  "minimal_repair_type_exact_agreement": 0.6341,
  "minimal_repair_type_coarse_agreement": 0.6585,
  "hint_level_agreement": 0.7073,
  "leakage_constraint_agreement": 0.0976,
  "mean_confidence_gap": 0.25,
  "disagreement_count": 99,
  "note": "If 11-class agreement is low but 6-class agreement is much higher, this suggests the taxonomy may be too fine-grained rather than the task being invalid."
}
```

## 7. Disagreement Adjudication Results

```json
{
  "status": "completed",
  "count": 60,
  "decision_distribution": {
    "hybrid": 26,
    "codex_preferred": 19,
    "deepseek_preferred": 15
  },
  "note": "proxy_adjudicated_60.jsonl is proxy adjudicated labels only, not human gold labels."
}
```

## 8. Expected-label Validity Results

```json
{
  "status": "completed",
  "synthetic_metric_count": 50,
  "expected_vs_codex_acc": 0.3367,
  "expected_vs_deepseek_acc": 0.4472,
  "expected_vs_adjudicated_acc": 0.4267,
  "strict_pass_precision_against_adjudicated": 0.5667,
  "strict_fail_actual_bad_rate": 1.0,
  "expected_label_valid_true": 0.24,
  "expected_label_valid_partial": 0.34,
  "expected_label_valid_false": 0.66,
  "first_wrong_step_not_equal_earliest_actionable_step_after_adjudication": 0.0,
  "synthetic_types_with_invalid_cases": {
    "sign_error": 6,
    "wrong_operation": 2,
    "misread_given_quantity": 3,
    "unit_conversion_error": 3,
    "equation_setup_error": 4,
    "substitution_error": 3,
    "final_answer_correct_process_wrong": 5,
    "final_answer_wrong_prefix_correct": 3,
    "arithmetic_error": 3,
    "sparse_insufficient_trace": 1
  },
  "go_no_go": {
    "expected_vs_adjudicated_full_validity>=0.65": false,
    "expected_vs_adjudicated_partial_validity>=0.85": false,
    "first_wrong_step_diff_ratio>=0.08": false,
    "no_go_expected_full_validity<0.50": true,
    "no_go_first_wrong_step_diff<0.03": true,
    "recommendation": "do_not_train_until_proxy_audit_passes"
  }
}
```

## 9. Taxonomy Failure Modes

Likely failure modes are over-fine repair labels, unclear leakage boundaries, and sparse traces where first wrong step is not identifiable.

## 10. Go / No-Go Decision

No training or silver scaling is allowed unless the proxy audit Go standards pass. Current recommendation is stored in `expected_label_validity_60.json`.

## 11. Recommended Next Step

If pending, run the DeepSeek full-prompt audit with a valid API key. If completed and thresholds fail, refine generation, verifier, or taxonomy before scaling.

## Validation

- Audit command chain completed.
- `python3 -m compileall -q src`: passed.
- `python3 -m src.labels.taxonomy --check`: passed.
- Blind leakage scan: passed.
- Secret scan excluding `.env`: passed.
- `python3 -m pytest`: unavailable, `No module named pytest`.
