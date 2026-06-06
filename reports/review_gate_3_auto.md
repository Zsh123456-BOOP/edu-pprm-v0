# Review Gate 3 Auto-Silver Pilot

Pilot total: 240
Sources: `{'stepverify': 120, 'gsm8k': 80, 'math': 40}`

Synthetic types: `{'arithmetic_error': 11, 'sign_error': 10, 'wrong_operation': 9, 'misread_given_quantity': 9, 'unit_conversion_error': 9, 'equation_setup_error': 9, 'substitution_error': 9, 'no_error_correct_trace': 9, 'self_corrected_error': 9, 'sparse_insufficient_trace': 9, 'final_answer_correct_process_wrong': 9, 'final_answer_wrong_prefix_correct': 9, 'hint_would_leak_answer': 9}`

## DeepSeek Status

- Configured model: `deepseek-v4-pro`
- API smoke: passed
- Full API labeling: interrupted before first pilot label completed; current pilot labels are heuristic fallback outputs.
- JSON parse rate: 1.0
- Schema pass rate: 1.0

## Metrics

StepVerify: `{'count': 120, 'first_wrong_step_acc': 1.0, 'off_by_one_acc': 1.0, 'null_error_rate': 0.0, 'overclaim_rate': 0.0}`

Synthetic: `{'count': 120, 'first_wrong_step_acc': 1.0, 'earliest_actionable_step_acc': 1.0, 'hint_level_acc': 1.0, 'leakage_constraint_acc': 1.0, 'minimal_repair_type_macro_f1': 1.0, 'intervention_needed_f1': 1.0}`

first_wrong_step != earliest_actionable_step ratio: 0.0375
intervention false/uncertain ratio: 0.1500
minimal_repair_type distribution: `{'ask_to_recompute_local_expression': 47, 'ask_to_reinterpret_given_quantity': 106, 'ask_to_check_unit_conversion': 14, 'ask_to_check_operation_or_formula': 19, 'ask_to_rewrite_equation_or_expression': 9, 'no_intervention_needed': 18, 'insufficient_information': 18, 'ask_to_compare_with_problem_condition': 9}`

## Self Consistency

`{'first_wrong_step': 1.0, 'earliest_actionable_step': 1.0, 'intervention_needed': 1.0, 'minimal_repair_type': 1.0, 'hint_level': 1.0, 'leakage_constraint': 1.0}`

## Tutor T2 vs T3

`{'T2': {'targeted': 1.0, 'mathematically_correct': 1.0, 'actionable': 0.1, 'minimal': 0.95, 'non_leakage': 1.0, 'repair_consistent': 1.0, 'over_help': 0.0}, 'T3': {'targeted': 0.9333, 'mathematically_correct': 1.0, 'actionable': 0.5333, 'minimal': 1.0, 'non_leakage': 1.0, 'repair_consistent': 1.0, 'over_help': 0.0}}`

## Go/No-Go

`{'stepverify_first_wrong_step_acc>=0.55': True, 'synthetic_minimal_repair_type_macro_f1>=0.45': True, 'first_wrong_step_diff_ratio>=0.10': False, 'false_uncertain_ratio>=0.08': True, 'no_single_repair_type>0.70': True, 'real_deepseek_full_run_completed': False}`

Recommendation: do not proceed to training from this run. The pipeline is complete, but the full real DeepSeek label run did not complete and the first_wrong/actionable difference ratio is below the 10% criterion in fallback output.

Next: rerun full real API labeling with `DEEPSEEK_API_KEY` exported, or use a faster configured model for throughput, then do a small human spot-check before any verifier training.

## Validation

- `python3 -m compileall -q src`: passed
- `python3 -m src.labels.lint_boundary_cases`: passed
- `python3 -m src.data.validate_schema --jsonl data/pilot/pilot_pool.autolabeled.jsonl`: passed, 240 rows
- `python3 -m pytest`: unavailable, `No module named pytest`
