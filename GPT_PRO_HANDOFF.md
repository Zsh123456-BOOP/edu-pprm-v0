# Edu-PPRM-v0 GPT Pro Handoff

Last updated: 2026-06-09

This file is the persistent handoff/worklog for GPT Pro review. Keep it updated whenever the Edu-PPRM-v0 pipeline, generated datasets, reports, prompts, or evaluation conclusions change.

## Current State

Direction 1 is still in data/pilot validation. Do not move to model training yet.

Recent committed work:

- `87ce16b` Initialize Edu-PPRM phase 0 and 1
- `ff999f1` Complete Phase 2 schema taxonomy annotation guidelines
- `bf85927` Build auto-silver pilot with DeepSeek labels
- `8f7e023` Add real DeepSeek small-batch validation
- `3dae086` Compare DeepSeek model quality on small batch
- `025f99f` Generate and evaluate DeepSeek synthetic 240

The latest important commit is `025f99f`, which adds the DeepSeek-pro synthetic 240 generation, verification, relabeling, and evaluation artifacts.

## What Was Done

1. Built a DeepSeek-pro synthetic generator for 240 math traces.
2. Forced balanced synthetic type coverage across 13 error/boundary types.
3. Stored hidden expected labels in `synthetic_metadata.expected_*`.
4. Ran a DeepSeek-pro strict verifier to test whether generated traces really match the requested synthetic type.
5. Ran DeepSeek-pro relabeling without exposing expected labels to the label prompt.
6. Evaluated DeepSeek outputs against hidden expected labels.
7. Committed generated datasets, examples, summaries, reports, and scripts.

No MathEDU, ProcessBench, PRM800K, handwrite data, full dataset construction, or model training was used in this run.

## How It Was Done

Generation script:

```bash
python3 -m src.synthetic.deepseek_generate_synthetic_240 \
  --count 240 \
  --model deepseek-v4-pro \
  --workers 6 \
  --fill-existing
```

Strict trace verification:

```bash
python3 -m src.synthetic.deepseek_verify_synthetic_240 \
  --model deepseek-v4-pro \
  --workers 6
```

DeepSeek relabeling:

```bash
python3 -m src.labels.label_deepseek_synthetic_240 \
  --model deepseek-v4-pro \
  --workers 6
```

Evaluation:

```bash
python3 -m src.eval.eval_deepseek_synthetic_240 \
  --input data/pilot/deepseek_synthetic_240.autolabeled.jsonl

python3 -m src.eval.eval_deepseek_synthetic_240 \
  --input data/pilot/deepseek_synthetic_240.autolabeled.jsonl \
  --tag full

python3 -m src.eval.eval_deepseek_synthetic_240 \
  --input data/pilot/deepseek_synthetic_240.verified.autolabeled.jsonl \
  --tag verified
```

Validation:

```bash
python3 -m compileall -q src
python3 -m src.data.validate_schema --jsonl data/pilot/deepseek_synthetic_240.raw.jsonl
python3 -m src.data.validate_schema --jsonl data/pilot/deepseek_synthetic_240.autolabeled.jsonl
python3 -m src.data.validate_schema --jsonl data/pilot/deepseek_synthetic_240.verified.autolabeled.jsonl
```

`pytest` is unavailable in the current local Python environment: `No module named pytest`.

## Generated Dataset Files Committed

Core generated datasets:

- `data/pilot/deepseek_synthetic_240.raw.jsonl`
- `data/pilot/deepseek_synthetic_240.autolabeled.jsonl`
- `data/pilot/deepseek_synthetic_240.verified.raw.jsonl`
- `data/pilot/deepseek_synthetic_240.verified.autolabeled.jsonl`

Examples and summaries:

- `data/reports/deepseek_synthetic_240_40_examples.jsonl`
- `data/reports/deepseek_synthetic_240_generation_summary.json`
- `data/reports/deepseek_synthetic_240_llm_verification_summary.json`
- `data/reports/deepseek_synthetic_240_label_summary.json`
- `data/reports/deepseek_synthetic_240_eval_summary.json`
- `data/reports/deepseek_synthetic_240_eval_summary_full.json`
- `data/reports/deepseek_synthetic_240_eval_summary_verified.json`
- `data/reports/deepseek_synthetic_240_experiment_summary.json`

Human-readable reports:

- `reports/deepseek_synthetic_240_experiment.md`
- `reports/deepseek_synthetic_240_eval.md`
- `reports/deepseek_synthetic_240_eval_full.md`
- `reports/deepseek_synthetic_240_eval_verified.md`

DeepSeek request/response cache directories are intentionally ignored and not committed:

- `data/cache/deepseek/generate_synth240_*`
- `data/cache/deepseek/label_synth240_*`
- `data/cache/deepseek/verify_synth240_*`

## Key Results

Generation:

- Total generated traces: 240
- Synthetic types: 13
- Minimum samples per type: 18
- Type distribution: 6 types with 19 samples, 7 types with 18 samples
- Source distribution: GSM8K 164, MATH 76

Strict DeepSeek-pro verification:

- Pass: 159 / 240
- Fail: 81 / 240
- Pass rate: 66.25%

Hardest generated types:

- `final_answer_correct_process_wrong`: 13 failures
- `hint_would_leak_answer`: 13 failures
- `equation_setup_error`: 10 failures
- `sign_error`: 9 failures

DeepSeek-pro relabeling:

- Output: 240 / 240
- Parse rate: 1.0
- Schema validation pass rate: 1.0

Full 240 evaluation:

- `first_wrong_step_acc`: 0.2917
- `earliest_actionable_step_acc`: 0.3250
- `intervention_needed_acc`: 0.5333
- `minimal_repair_type_acc`: 0.4083
- `minimal_repair_type_macro_f1`: 0.2789
- `hint_level_acc`: 0.3167
- `leakage_constraint_acc`: 0.3000
- `first_wrong_step != earliest_actionable_step`: 0.0708

Verified 159 evaluation:

- `first_wrong_step_acc`: 0.3208
- `earliest_actionable_step_acc`: 0.3962
- `intervention_needed_acc`: 0.7925
- `minimal_repair_type_acc`: 0.5849
- `minimal_repair_type_macro_f1`: 0.3533
- `hint_level_acc`: 0.4717
- `leakage_constraint_acc`: 0.3208
- `first_wrong_step != earliest_actionable_step`: 0.0503

## Current Interpretation

This experiment does not yet justify training.

Two Go conditions failed:

- `minimal_repair_type_macro_f1 >= 0.45`
- `first_wrong_step != earliest_actionable_step >= 10%`

Two feasibility checks passed:

- `intervention_needed=false/uncertain >= 8%`
- no single `minimal_repair_type` exceeds 70%

The main evidence is that DeepSeek-pro can produce and parse structured labels, but the synthetic generation quality and pedagogical label separability are not strong enough yet.

## Recommended Next Step For GPT Pro

Ask GPT Pro to review the current pipeline and decide between these options:

1. Refine synthetic generation before any training.
   - Focus on `final_answer_correct_process_wrong`, `hint_would_leak_answer`, `equation_setup_error`, and `sparse_insufficient_trace`.
   - Make the verifier stricter but less dependent on another LLM's vague judgment.
   - Add deterministic rule checks for short-trace, self-correction, no-error, and one-main-error constraints.

2. Add a small human spot-check before scaling.
   - Sample around 50 traces from the verified 159 subset.
   - Check whether hidden expected labels are actually pedagogically correct.
   - Especially inspect cases where DeepSeek relabeling disagrees with expected labels.

3. Reframe the next pilot metric.
   - The current `first_wrong_step != earliest_actionable_step` ratio is low.
   - GPT Pro should decide whether this is a real task weakness or a synthetic prompt problem.
   - If the labels rarely differ, the project may need to focus on repair taxonomy quality rather than claiming a new intervention-timing signal.

Current recommendation: do not train yet. First improve data validity and label definitions, then rerun the 240-trace experiment.

## Suggested GPT Pro Review Questions

Use this concise prompt:

```text
Review the Edu-PPRM-v0 Direction 1 pilot after commit 025f99f.

Key files:
- GPT_PRO_HANDOFF.md
- reports/deepseek_synthetic_240_experiment.md
- data/reports/deepseek_synthetic_240_experiment_summary.json
- data/pilot/deepseek_synthetic_240.raw.jsonl
- data/pilot/deepseek_synthetic_240.autolabeled.jsonl
- data/pilot/deepseek_synthetic_240.verified.raw.jsonl
- data/pilot/deepseek_synthetic_240.verified.autolabeled.jsonl
- src/synthetic/deepseek_generate_synthetic_240.py
- src/synthetic/deepseek_verify_synthetic_240.py
- src/labels/label_deepseek_synthetic_240.py
- src/eval/eval_deepseek_synthetic_240.py

Please answer:
1. Is the current failure mainly a synthetic generation problem, taxonomy problem, prompt problem, or task-definition problem?
2. Which synthetic types should be fixed first?
3. Should we add human spot-check before more DeepSeek generation?
4. What exact next experiment should be run before any model training?
5. What Go/No-Go thresholds should be revised, if any?
```

## Maintenance Rule

Whenever future work changes the pipeline, data, reports, metrics, or conclusion:

1. Update this file in the same commit.
2. Add the new commit hash and date.
3. Record what changed, how it was run, where outputs are, and what conclusion changed.
4. Do not include API keys, raw credentials, or hidden local cache contents.
