# Edu-PPRM-v0

This repository is for Direction 1 only: a text-only pedagogical process
verification pilot.

The goal is to test whether tutor-facing intervention labels add value beyond
existing first-error detection:

- `first_wrong_step`
- `earliest_actionable_step`
- `intervention_needed`
- `minimal_repair_type`
- `hint_level`
- `leakage_constraint`

## Scope Guard

Current scope:

- text-only Edu-PPRM-v0 data source registry and pilot data inspection
- small-sample source loaders for field coverage checks
- no large-scale dataset construction before Review Gate 1

Explicitly out of scope for this phase:

- no handwritten image data in the main pipeline
- no VLM work
- no direction 2 budget sweep
- no direction 3 scaffold distillation
- no full model training
- no claim that first-error detection alone is the contribution

The unified schema reserves `handwrite_data`, `budget_data`, and
`distillation_data` as nullable placeholders. Phase 0/1 scripts must not depend
on them.

## Quick Start

```bash
python -m src.data.dataset_registry --check
python -m src.data.load_stepverify --limit 20
python -m src.data.load_mathedu --limit 20
python -m src.data.load_gsm8k --limit 20
python -m src.data.load_math --limit 20
python -m src.data.load_prm800k --limit 20
python -m src.data.load_processbench --limit 20
pytest
```

## Review Gate 1

Stop after Phase 1 and review:

- source summary JSON files
- 20 examples per source
- field coverage
- fields that map to existing first-error labels
- fields that cannot directly map to pedagogical repair labels
