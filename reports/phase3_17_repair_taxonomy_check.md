# Phase 3.17 Repair Taxonomy Check

These are human review results, not training data and not silver labels.

```json
{
  "status": "completed",
  "core_count": 16,
  "deepseek_compared_count": 16,
  "missing_deepseek_sample_ids": [],
  "first_wrong_step_off_by_one_agreement": 0.9375,
  "intervention_needed_agreement": 0.9375,
  "minimal_repair_coarse_6_agreement": 0.9375,
  "hint_level_coarse_3_agreement": 0.75,
  "go_no_go": {
    "calibration_pass_rate>=7/8": true,
    "first_wrong_step_off_by_one_agreement>=0.80": true,
    "intervention_needed_agreement>=0.80": true,
    "minimal_repair_coarse_6_agreement>=0.70": true,
    "retained_types_trace_validity>=0.70": true
  }
}
```
