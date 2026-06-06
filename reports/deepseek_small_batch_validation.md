# DeepSeek Small-Batch Throughput Validation

Samples: 20

Recommended full-run model: `deepseek-v4-pro`

## deepseek-v4-pro

- model: `deepseek-v4-pro`
- input_count: `20`
- success_count: `20`
- failure_count: `0`
- parse_rate: `1.0`
- schema_validation_pass_rate: `1.0`
- total_seconds: `97.704`
- avg_latency_seconds: `4.885`
- max_latency_seconds: `7.68`
- minimal_repair_type_distribution: `{'ask_to_rewrite_equation_or_expression': 2, 'ask_to_reinterpret_given_quantity': 11, 'ask_to_recompute_local_expression': 2, 'ask_clarifying_question': 1, 'ask_to_check_operation_or_formula': 1, 'no_intervention_needed': 2, 'insufficient_information': 1}`
- intervention_needed_distribution: `{'True': 17, 'False': 3}`
- compact_prompt: `True`


## Quality Comparison Update

同一批 20 条样本上，`deepseek-v4-pro` 质量分更高：0.76 vs flash 0.665。虽然 pro 平均延迟 4.885s，高于 flash 2.658s，但本任务优先标签质量，因此全量真实标注推荐 `deepseek-v4-pro`。

详细报告：`data/reports/deepseek_model_quality_comparison.json` 和 `reports/deepseek_model_quality_comparison.md`。
