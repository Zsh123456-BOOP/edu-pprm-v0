# Review Gate 2 Summary

## Decision

Recommendation: enter Phase 3 pilot after human review, but do not include MathEDU in the core pilot.

Phase 3 was not started and no pilot pool was built in this run.

## MathEDU Audit

- Report: `data/reports/mathedu_full_audit.json`
- Rows scanned: 28336
- Direct `problem_text`: 0 (0.0)
- Recoverable question fields: 0 (0.0)
- Student solution raw: 28336 (1.0)
- Teacher feedback/review: 6992 (0.2468)
- Error type/reason: 706 (0.0249)
- Step-level pilot candidates: 0
- Missing question but matchable ID: 28336
- Fully unrecoverable rows: 0

Recommendation: `exclude_from_phase3_pilot_keep_for_later_enhancement`.

Interpretation: MathEDU has real student processes and some teacher feedback, but 0% recoverable question/problem text in the audited local raw data. It should not enter the Phase 3 core pilot unless a reliable question recovery table is found.

## Paths

- Schema: `schemas/edu_pprm.schema.json`
- Validator: `src/data/validate_schema.py`
- Schema examples: `data/reports/schema_conversion_examples.jsonl`
- Taxonomy: `configs/label_taxonomy.yaml`
- Taxonomy readable doc: `docs/label_taxonomy_readable.md`
- Annotation guideline: `docs/annotation_guideline.md`
- Boundary cases: `data/reports/boundary_cases_20.jsonl`
- Pilot source policy: `docs/pilot_source_policy.md`

## Schema Conversion Examples

- StepVerify: 5
- GSM8K synthetic placeholders: 5
- MATH synthetic placeholders: 5
- MathEDU excluded examples: 5
- MathEDU eligible pilot examples: 0

All 20 schema conversion examples passed `validate_schema`.

## Label Complexity

Current taxonomy is not too fine-grained for a pilot. It is compact enough to test feasibility while still separating intervention, repair type, hint strength, and leakage constraint.

The most likely disagreement points are:

- `earliest_actionable_step`
- `minimal_repair_type`: reinterpret quantity vs rewrite equation/expression
- `hint_level`: low vs medium
- `intervention_needed`: false vs uncertain for self-correction or sparse traces
- `leakage_constraint`: do not solve next step vs point to local step only

## Validation

- `python3 -m compileall -q src`: passed
- `python3 -m src.data.validate_schema --jsonl data/reports/schema_conversion_examples.jsonl`: passed, 20 rows
- `python3 -m src.labels.taxonomy --check`: passed
- `python3 -m pytest`: unavailable, `No module named pytest`

## Recommendation

Proceed to Phase 3 pilot only after review approval, using:

- StepVerify core source: about 120 examples
- GSM8K synthetic: about 80 examples
- MATH synthetic: about 40 examples

Exclude from Phase 3 pilot gold:

- MathEDU, until question recovery is solved
- PRM800K, baseline/pretrain only
- ProcessBench, external eval only
