# Proxy Audit Agreement 60

These labels are proxy labels, not human gold labels. Metrics compare `codex_manual_proxy` against `deepseek_proxy`; the `heuristic_proxy` baseline is excluded from the main agreement metrics.

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
