# DeepSeek Model Quality Comparison

Recommended full-run model: `deepseek-v4-pro`

## deepseek-v4-flash

- model: `deepseek-v4-flash`
- count: `20`
- success_count: `20`
- failure_count: `0`
- avg_latency_seconds: `2.658`
- max_latency_seconds: `3.71`
- stepverify_first_wrong_step_acc: `0.7`
- synthetic_first_wrong_step_acc: `0.8`
- synthetic_earliest_actionable_step_acc: `0.9`
- synthetic_intervention_needed_acc: `0.9`
- synthetic_minimal_repair_type_acc: `0.7`
- synthetic_hint_level_acc: `0.6`
- synthetic_leakage_constraint_acc: `0.2`
- first_wrong_step_diff_ratio: `0.0`
- minimal_repair_type_distribution: `{'ask_to_recompute_local_expression': 6, 'ask_to_reinterpret_given_quantity': 6, 'ask_to_check_operation_or_formula': 3, 'ask_to_justify_inference': 2, 'ask_to_check_unit_conversion': 1, 'no_intervention_needed': 2}`
- quality_score: `0.665`

## deepseek-v4-pro

- model: `deepseek-v4-pro`
- count: `20`
- success_count: `20`
- failure_count: `0`
- avg_latency_seconds: `4.885`
- max_latency_seconds: `7.68`
- stepverify_first_wrong_step_acc: `0.8`
- synthetic_first_wrong_step_acc: `0.8`
- synthetic_earliest_actionable_step_acc: `1.0`
- synthetic_intervention_needed_acc: `0.9`
- synthetic_minimal_repair_type_acc: `0.8`
- synthetic_hint_level_acc: `0.7`
- synthetic_leakage_constraint_acc: `0.2`
- first_wrong_step_diff_ratio: `0.05`
- minimal_repair_type_distribution: `{'ask_to_rewrite_equation_or_expression': 2, 'ask_to_reinterpret_given_quantity': 11, 'ask_to_recompute_local_expression': 2, 'ask_clarifying_question': 1, 'ask_to_check_operation_or_formula': 1, 'no_intervention_needed': 2, 'insufficient_information': 1}`
- quality_score: `0.76`
