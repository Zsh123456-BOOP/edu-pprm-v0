# DeepSeek Pro Synthetic 240 Experiment

## Scope

This run used `deepseek-v4-pro` to generate 240 synthetic math traces, then used `deepseek-v4-pro` again to relabel them without exposing hidden `synthetic_metadata.expected_*` fields.

No MathEDU, ProcessBench, PRM800K, handwrite data, training, or full dataset construction was used.

## Generation Coverage

- Total generated traces: 240
- Source mix: GSM8K 164, MATH 76
- Synthetic type coverage: 13 types
- Minimum samples per type: 18
- Distribution: arithmetic/sign/wrong_operation/misread/unit/equation_setup each 19; the other 7 types each 18
- Basic generation failures after fill: 0

This means the generated set is balanced by synthetic error type. It is not random sampling; the generator targets fixed counts per type and fills failed slots until the distribution is complete.

## Strict Trace Verification

An independent DeepSeek-pro verifier checked whether each generated trace actually matches the requested synthetic type and expected pedagogical setup.

- Verified pass: 159 / 240
- Verified fail: 81 / 240
- Pass rate: 66.25%

Hardest types by fail count:

- `final_answer_correct_process_wrong`: 13 failures
- `hint_would_leak_answer`: 13 failures
- `equation_setup_error`: 10 failures
- `sign_error`: 9 failures

This is the main bottleneck. The generator can produce balanced labels, but about one third of traces are not reliable enough under strict checking.

## Relabeling Quality

DeepSeek-pro then labeled all 240 traces without seeing expected labels.

- Parse rate: 1.0
- Schema validation pass rate: 1.0
- Label failures: 0

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

## What This Tests

This does not merely test whether a model says "there is an error." The hidden expected labels test whether the model can recover:

- where the first mathematical error is;
- when intervention should happen;
- whether intervention is needed at all;
- what minimal repair type is appropriate;
- how strong the hint should be;
- what leakage constraint applies.

The model performs reasonably on some types such as no-error and self-correction repair decisions, but struggles with equation setup, sparse insufficient traces, final-answer edge cases, and leakage-sensitive short-answer cases.

## Go / No-Go

Current go rules are not met:

- `minimal_repair_type_macro_f1 >= 0.45`: failed
- `first_wrong_step != earliest_actionable_step >= 10%`: failed
- `false/uncertain intervention >= 8%`: passed
- no single repair type over 70%: passed

Recommendation: do not train and do not scale silver data yet. The next useful step is to refine the generation/verifier prompts for the hard types, or run a small human spot-check on the 159 verified traces before investing in larger generation.

## Validation

- `python3 -m compileall -q src`: passed
- `python3 -m src.data.validate_schema --jsonl data/pilot/deepseek_synthetic_240.raw.jsonl`: passed, 240 rows
- `python3 -m src.data.validate_schema --jsonl data/pilot/deepseek_synthetic_240.autolabeled.jsonl`: passed, 240 rows
- `python3 -m src.data.validate_schema --jsonl data/pilot/deepseek_synthetic_240.verified.autolabeled.jsonl`: passed, 159 rows
- Secret scan for the provided DeepSeek key and bearer patterns: passed
- `python3 -m pytest`: unavailable, `No module named pytest`

## Outputs

- `data/pilot/deepseek_synthetic_240.raw.jsonl`
- `data/pilot/deepseek_synthetic_240.autolabeled.jsonl`
- `data/pilot/deepseek_synthetic_240.verified.raw.jsonl`
- `data/pilot/deepseek_synthetic_240.verified.autolabeled.jsonl`
- `data/reports/deepseek_synthetic_240_generation_summary.json`
- `data/reports/deepseek_synthetic_240_llm_verification_summary.json`
- `data/reports/deepseek_synthetic_240_label_summary.json`
- `data/reports/deepseek_synthetic_240_eval_summary.json`
- `data/reports/deepseek_synthetic_240_eval_summary_verified.json`
- `data/reports/deepseek_synthetic_240_experiment_summary.json`
