# Phase 3.17 Human Review Instructions

This review pack is for checking whether a 6-class repair taxonomy is usable. It is not training data and not a gold-label release.

## Files For Reviewers

Use only:

- `data/manual/phase3_17_human_pack_24.blind.jsonl`
- `data/manual/phase3_17_human_template_24.csv`

Do not use:

- `data/manual/phase3_17_human_analysis_private.jsonl`
- `data/manual/phase3_17_human_manifest.json`
- any `expected_*` labels
- any DeepSeek labels
- any proxy adjudicated labels

## Fields To Fill

Required:

- `reviewer_id`: reviewer identifier.
- `first_wrong_step`: first mathematically wrong visible step, or blank if no visible wrong step.
- `intervention_needed`: one of `true`, `false`, `uncertain`.
- `minimal_repair_coarse_6`: one of:
  - `no_intervention`
  - `local_computation`
  - `quantity_or_condition`
  - `equation_or_formula`
  - `verification_check`
  - `insufficient_or_clarify`
- `hint_level_coarse_3`: one of:
  - `none`
  - `nudge`
  - `targeted_or_scaffolded`
- `trace_validity_for_intended_type`: one of:
  - `as_intended`
  - `visible_but_other_error`
  - `no_visible_error`
  - `insufficient_trace`
- `rationale`: short reason for the label.

Optional:

- `earliest_actionable_step_optional`: fill only if useful.
- `leakage_risk_binary`: `yes` or `no`.

## Label Rules

- Do not force an error if the visible trace is correct.
- If the student self-corrects before feedback is needed, use `intervention_needed=false`.
- If there is too little work to diagnose safely, use `intervention_needed=uncertain` and `minimal_repair_coarse_6=insufficient_or_clarify`.
- `trace_validity_for_intended_type` should judge whether the visible trace really contains the kind of issue the sample is supposed to test. Reviewers do not see the intended type; use the visible trace only.
- Keep feedback labels minimal. Do not mark a full solution as a normal hint.
