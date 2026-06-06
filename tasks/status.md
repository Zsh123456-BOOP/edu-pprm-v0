# Edu-PPRM-v0 Task Status

## Phase 0

### Card 0.1 Initialize repository
- [x] 创建目录结构
- [x] 创建 pyproject.toml
- [x] 添加 README.md
- [x] 添加 tasks/status.md
- [x] 添加 tasks/review_checkpoints.md
- [x] 添加基础 pytest 配置

完成内容: 初始化 Git 仓库和 Edu-PPRM-v0 工程骨架，当前 README 明确只做方向 1 text-only pilot。
生成文件: README.md, pyproject.toml, .gitignore, tasks/status.md, tasks/review_checkpoints.md, src/ package dirs, data/ dirs, tests/。
运行命令: git init; mkdir -p ...; python3 -m compileall -q src tests。
主要统计结果: compileall 通过；pytest 配置已写入 pyproject.toml。
失败或不确定点: 本机未安装 pytest，`pytest` 和 `python3 -m pytest` 不能运行。
是否需要人工 review: 是，Review Gate 1 一并 review README、status 和目录结构。

### Card 0.2 明确禁止范围
- [x] 在 README 中写明：当前只做 text-only Edu-PPRM-v0
- [x] 在 schema 中预留 handwrite 字段，但默认 null
- [x] 在 schema 中预留 budget_data 字段，但默认 null
- [x] 在 schema 中预留 distillation_data 字段，但默认 null
- [x] 添加 tests/test_scope_guard.py，检查 pilot/full 数据不得依赖 handwrite 字段

完成内容: README 增加 scope guard；schema stub 只预留 nullable reserved fields；Phase 1 loader 不引用 handwrite/budget/distillation 字段。
生成文件: schemas/edu_pprm.schema.json, tests/test_scope_guard.py。
运行命令: python3 -m compileall -q src tests; stdlib smoke checks。
主要统计结果: reserved fields 默认 null；scope guard 静态检查通过。
失败或不确定点: pytest 未安装，测试文件尚未通过 pytest runner 执行。
是否需要人工 review: 是，确认 reserved placeholder 是否符合后续 Phase 2 schema 预期。

## Phase 1

### Card 1.1 数据源 registry
- [x] 创建 configs/data_sources.yaml
- [x] 创建 schemas/raw_dataset_registry.schema.json
- [x] 实现 src/data/dataset_registry.py
- [x] 为每个数据源登记：source_name、url_or_path、license、task_use、allowed_split、release_flag

完成内容: 建立 6 个数据源 registry，并添加 ProcessBench external_eval_only guard。
生成文件: configs/data_sources.yaml, schemas/raw_dataset_registry.schema.json, src/data/dataset_registry.py, data/reports/dataset_registry_summary.json。
运行命令: python3 -m src.data.dataset_registry --check。
主要统计结果: 6 个 source 登记；ProcessBench 仅 external_eval_only；registry check 通过。
失败或不确定点: stepverify、mathedu、processbench license 暂登记为 unknown_from_registry_check，需要人工或后续源页核验。
是否需要人工 review: 是，确认许可和用途边界。

### Card 1.2 StepVerify loader
- [x] 实现 src/data/load_stepverify.py
- [x] 读取原始字段
- [x] 映射 problem、reference_solution、student_solution、incorrect_index、error_category、error_description
- [x] 输出 data/interim/stepverify.raw.jsonl
- [x] 生成字段覆盖率报告

完成内容: 从 HF rows API 抽取 20 条 StepVerify 样本并转换为内部 raw format。
生成文件: src/data/load_stepverify.py, data/interim/stepverify.raw.jsonl, data/reports/stepverify_summary.json, data/reports/stepverify_20_examples.jsonl, data/reports/stepverify_missing_fields.csv。
运行命令: python3 -m src.data.load_stepverify --limit 20。
主要统计结果: 20/20 转换；problem/reference/student/incorrect_index/error_category/error_description/dialog_history 覆盖率均为 100%。
失败或不确定点: 只做 20 条 pilot 摸底，未验证全量 95% 转换率。
是否需要人工 review: 是，检查 first-error 字段是否足够作为 baseline。

### Card 1.3 MathEDU loader
- [x] 实现 src/data/load_mathedu.py
- [x] 映射 problem、student_solution、teacher_feedback、correctness、error_type、teacher_advice
- [x] 输出 data/interim/mathedu.raw.jsonl
- [x] 标记哪些样本有 step-level 信息，哪些只有整体反馈

完成内容: 从 MathEDU GitHub time_series_split/test.json 抽取 20 条，映射学生过程、correctness、teacher review/reason 字段并打 usable_bucket。
生成文件: src/data/load_mathedu.py, data/interim/mathedu.raw.jsonl, data/reports/mathedu_summary.json, data/reports/mathedu_20_examples.jsonl。
运行命令: python3 -m src.data.load_mathedu --limit 20。
主要统计结果: 20/20 student_solution_raw 和 correctness 覆盖；problem_text 0/20；teacher_feedback/error_type/teacher_advice 3/20。
失败或不确定点: 当前公开 JSON 样本无可靠 problem_text；不能可靠做 step-level first_wrong_step 映射。
是否需要人工 review: 是，决定 MathEDU 是否只用于 feedback/tutor evaluation 或另找题干来源。

### Card 1.4 GSM8K / MATH loader
- [x] 实现 src/data/load_gsm8k.py
- [x] 实现 src/data/load_math.py
- [x] 提取 problem_text、gold_answer、gold_solution
- [x] 拆分 gold_solution_steps
- [x] 输出 data/interim/problem_bank.raw.jsonl

完成内容: 从 HF rows API 抽取 GSM8K train 20 条、MATH train 跨 subject 20 条，生成单源和合并 problem bank。
生成文件: src/data/load_gsm8k.py, src/data/load_math.py, data/interim/gsm8k.problem_bank.raw.jsonl, data/interim/math.problem_bank.raw.jsonl, data/interim/problem_bank.raw.jsonl, data/reports/gsm8k_summary.json, data/reports/math_summary.json, data/reports/gsm8k_20_examples.jsonl, data/reports/math_20_examples.jsonl。
运行命令: python3 -m src.data.load_gsm8k --limit 20; python3 -m src.data.load_math --limit 20。
主要统计结果: GSM8K 20/20 problem/gold answer/gold solution 覆盖，20/20 拆出 2+ steps；MATH 20/20 problem/gold solution/topic/difficulty 覆盖，gold_answer 13/20，20/20 拆出 2+ steps。
失败或不确定点: MATH gold_answer 依赖 boxed extraction，非 boxed 解答不能稳定抽取。
是否需要人工 review: 是，确认 gold_answer 缺失是否可接受。

### Card 1.5 PRM800K / ProcessBench loader
- [x] 实现 src/data/load_prm800k.py
- [x] 实现 src/data/load_processbench.py
- [x] PRM800K 输出 step correctness 格式
- [x] ProcessBench 输出 external eval 格式
- [x] 添加 split guard，禁止 ProcessBench 进入训练

完成内容: PRM800K 从 OpenAI Git LFS media URL 流式读取前 20 行；ProcessBench 从 HF rows API 读取 gsm8k split 前 20 条并强制输出 external_eval。
生成文件: src/data/load_prm800k.py, src/data/load_processbench.py, data/interim/prm800k.step_correctness.raw.jsonl, data/external_eval/processbench.external_eval.raw.jsonl, data/reports/prm800k_summary.json, data/reports/processbench_summary.json, data/reports/prm800k_20_examples.jsonl, data/reports/processbench_20_examples.jsonl, tests/test_processbench_guard.py。
运行命令: python3 -m src.data.load_prm800k --limit 20; python3 -m src.data.load_processbench --limit 20; stdlib split guard smoke。
主要统计结果: PRM800K 20/20 problem/steps/ratings 覆盖；ProcessBench 20/20 problem/steps/label/final_answer_correct 覆盖。
失败或不确定点: PRM800K 是通用 PRM supervision，不能当 pedagogical repair 标签；ProcessBench 不含 error_category/error_description/repair labels。
是否需要人工 review: 是，确认 baseline/external_eval 使用边界。

### Card 1.6 MathEDU 题干可恢复性审计
- [x] 扫描 MathEDU 全量本地原始数据
- [x] 检查 problem_text/question/prompt/problem_id/source_id/image_id/worksheet_id/original_question 等字段
- [x] 统计题干、学生过程、教师反馈、错误原因、step-level pilot、可匹配 ID、不可恢复样本
- [x] 输出 data/reports/mathedu_full_audit.json
- [x] 输出 data/reports/mathedu_recoverable_examples.jsonl
- [x] 输出 data/reports/mathedu_unusable_examples.jsonl

完成内容: 将 MathEDU GitHub 公开 JSON 同步到本地 data/raw/mathedu/ 并审计 21 个 split 文件；raw 文件被 .gitignore 忽略，不提交。
生成文件: src/data/audit_mathedu.py, data/reports/mathedu_full_audit.json, data/reports/mathedu_recoverable_examples.jsonl, data/reports/mathedu_unusable_examples.jsonl。
运行命令: python3 -m src.data.audit_mathedu。
主要统计结果: 扫描 28,336 行；problem_text 直接存在 0/28,336；可恢复 question/problem/prompt/original_question 0/28,336；student_solution_raw 28,336/28,336；teacher_feedback/review 6,992/28,336；error_type/reason 706/28,336；step-level pilot candidate 0；缺题干但有可匹配 ID 28,336；完全不可恢复 0。
失败或不确定点: 行级 id 只能说明后续可能外部匹配，当前没有题干恢复表；按规则 MathEDU 暂不进入 Phase 3 core pilot。
是否需要人工 review: 是，确认 MathEDU 是否按建议排除出核心 pilot。

## Phase 2

### Card 2.1 Edu-PPRM schema
- [x] 创建 schemas/edu_pprm.schema.json
- [x] 实现 src/data/validate_schema.py
- [x] 所有 schema conversion examples 通过 schema 校验
- [x] reserved 保留 budget_data/distillation_data/handwrite_data 且显式为 null
- [x] MathEDU 不脑补题干，审计失败样本写 excluded_reason
- [x] 添加 ProcessBench 路径守卫，禁止进入 train/interim

完成内容: 定义 problem、student_trace、existing_labels、pedagogical_labels、label_metadata、reserved 六块 schema；生成 20 条 conversion examples 并通过 validator。
生成文件: schemas/edu_pprm.schema.json, src/data/validate_schema.py, data/reports/schema_conversion_examples.jsonl, tests/test_schema.py。
运行命令: python3 -m src.data.validate_schema --write-examples --jsonl data/reports/schema_conversion_examples.jsonl。
主要统计结果: schema examples 共 20 条；StepVerify 5；GSM8K placeholder 5；MATH placeholder 5；MathEDU excluded 5；20/20 通过 validate_schema。
失败或不确定点: MathEDU examples 仅用于记录 excluded_reason，不作为 Phase 3 pilot eligible 样本。
是否需要人工 review: 是，确认 schema 是否足够支持 Phase 3 标注。

### Card 2.2 标签 taxonomy
- [x] 创建 configs/label_taxonomy.yaml
- [x] 实现 src/labels/taxonomy.py
- [x] 添加 tests/test_label_taxonomy.py
- [x] 每个 label 写 definition
- [x] 每个 label 写 positive_examples
- [x] 每个 label 写 negative_examples
- [x] 每个 label 写 common_confusions
- [x] 输出 docs/label_taxonomy_readable.md

完成内容: 按指定 taxonomy 定义 3 个 intervention states、11 个 minimal repair types、5 个 hint levels、5 个 leakage constraints，并生成可读文档。
生成文件: configs/label_taxonomy.yaml, src/labels/taxonomy.py, docs/label_taxonomy_readable.md, tests/test_label_taxonomy.py。
运行命令: python3 -m src.labels.taxonomy --check。
主要统计结果: taxonomy check 通过；minimal_repair_type 控制为 11 类。
失败或不确定点: 最可能过细或分歧的是 minimal_repair_type 中 quantity reinterpretation vs equation rewrite。
是否需要人工 review: 是，确认标签粒度。

### Card 2.3 annotation guideline
- [x] 创建 docs/annotation_guideline.md
- [x] 讲清 first_wrong_step 与 earliest_actionable_step 区别
- [x] 明确二者可能相同也可能不同
- [x] 明确不能把 earliest_actionable_step 简单设成 first_wrong_step
- [x] 明确 uncertain / insufficient_information 使用场景
- [x] 明确自我修正时 intervention_needed 可以为 false
- [x] 写 20 个边界例子
- [x] 输出 data/reports/boundary_cases_20.jsonl

完成内容: 写入 Phase 2 标注指南和 20 个边界案例，覆盖用户指定的 20 类边界情形。
生成文件: docs/annotation_guideline.md, data/reports/boundary_cases_20.jsonl。
运行命令: python3 生成 boundary cases 与 guideline。
主要统计结果: boundary cases 20/20；每条包含 problem sketch、student steps、first_wrong_step、earliest_actionable_step、intervention_needed、minimal_repair_type、hint_level、leakage_constraint、reason。
失败或不确定点: 这些是 guideline examples，不是 pilot pool，也不是 gold labels。
是否需要人工 review: 是，确认边界例子是否符合教师标注预期。

### Card 2.4 Phase 3 pilot source policy
- [x] 创建 docs/pilot_source_policy.md
- [x] 根据 Review Gate 1 和 MathEDU audit 明确 Phase 3 来源策略
- [x] StepVerify 约 120 条作为核心来源
- [x] GSM8K synthetic 约 80 条
- [x] MATH synthetic 约 40 条
- [x] MathEDU 审计失败，暂不加入 core pilot
- [x] PRM800K 不进入 pilot gold
- [x] ProcessBench 不进入 pilot，只做 external eval

完成内容: 写入 Phase 3 来源策略文档，但未构建 pilot pool。
生成文件: docs/pilot_source_policy.md。
运行命令: 无需运行；基于 Review Gate 1 和 MathEDU audit 结果撰写。
主要统计结果: 建议 Phase 3 默认 120 StepVerify + 80 GSM8K synthetic + 40 MATH synthetic；MathEDU 0；PRM800K 0；ProcessBench 0。
失败或不确定点: 具体采样和去重策略留到 Phase 3，经 Review Gate 2 批准后再做。
是否需要人工 review: 是，确认是否按该策略进入 Phase 3。

### Card 2.5 Review Gate 2 report
- [x] 创建 data/reports/review_gate_2_summary.json
- [x] 创建 reports/review_gate_2.md
- [x] 报告 MathEDU 是否进入 Phase 3 pilot 的建议
- [x] 报告 schema/taxonomy/guideline/boundary cases 路径
- [x] 报告 schema 转换样例数量
- [x] 报告标签体系是否过细
- [x] 报告最可能导致老师分歧的标签
- [x] 报告是否建议进入 Phase 3 pilot

完成内容: 生成 Review Gate 2 JSON 和 Markdown 报告；明确停止在 Gate 2，不进入 Phase 3，不构建 pilot pool。
生成文件: data/reports/review_gate_2_summary.json, reports/review_gate_2.md。
运行命令: python3 -m compileall -q src; python3 -m src.data.validate_schema --jsonl data/reports/schema_conversion_examples.jsonl; python3 -m src.labels.taxonomy --check; python3 -m pytest。
主要统计结果: compileall 通过；schema examples 20/20 通过；taxonomy check 通过；pytest unavailable。
失败或不确定点: 本机无 pytest，无法运行 pytest runner；已在 Review Gate 2 报告中注明。
是否需要人工 review: 是，Review Gate 2 必须人工决定是否进入 Phase 3。

## Auto-Silver Pilot

### Card 3.0 修复 annotation guideline lint
- [x] 检查 docs/annotation_guideline.md 和 data/reports/boundary_cases_20.jsonl
- [x] 修复 Case 1 first_wrong_step 为 null
- [x] 修复 Case 6 reason/repair_target 指向 7 x 2 = 12
- [x] 新增 src/labels/lint_boundary_cases.py
- [x] 输出 data/reports/boundary_lint_report.json

完成内容: 修复 boundary case 逻辑冲突，并新增 lint 工具。
生成文件: src/labels/lint_boundary_cases.py, data/reports/boundary_lint_report.json。
运行命令: python3 -m src.labels.lint_boundary_cases。
主要统计结果: 20/20 boundary cases 通过 lint。
失败或不确定点: 无。
是否需要人工 review: 是，确认 Case 6 的 repair_target 粒度。

### Card 3.1 构建 pilot_pool.raw
- [x] 实现 src/data/build_pilot_pool.py
- [x] StepVerify 120 条
- [x] GSM8K synthetic 80 条
- [x] MATH synthetic 40 条
- [x] MathEDU/PRM800K/ProcessBench/handwrite 均为 0 条
- [x] 输出 data/pilot/pilot_pool.raw.jsonl
- [x] 输出 data/reports/pilot_pool_summary.json
- [x] 输出 data/reports/pilot_pool_30_examples.jsonl

完成内容: 构建 240 条 raw pilot pool，包含 StepVerify 和 synthetic 样本。
生成文件: src/data/build_pilot_pool.py, data/pilot/pilot_pool.raw.jsonl, data/reports/pilot_pool_summary.json, data/reports/pilot_pool_30_examples.jsonl。
运行命令: python3 -m src.data.build_pilot_pool。
主要统计结果: total 240；StepVerify 120，GSM8K 80，MATH 40；avg student step count 4.688。
失败或不确定点: StepVerify 从 HF rows API 分页拉取；未读取 MathEDU/ProcessBench/handwrite。
是否需要人工 review: 是，确认 raw pilot source mix。

### Card 3.2 生成 synthetic pilot traces
- [x] 实现 src/synthetic/inject_math_errors.py
- [x] 实现 src/synthetic/generate_pilot_synthetic.py
- [x] 实现 src/synthetic/verify_synthetic_steps.py
- [x] 输出 data/pilot/synthetic_pilot.raw.jsonl
- [x] 输出 data/reports/synthetic_pilot_summary.json
- [x] 输出 data/reports/synthetic_pilot_40_examples.jsonl
- [x] 输出 data/reports/synthetic_generation_failures.jsonl

完成内容: 生成 deterministic known-label synthetic traces，覆盖 13 类标准错误和边界情况。
生成文件: src/synthetic/inject_math_errors.py, src/synthetic/generate_pilot_synthetic.py, src/synthetic/verify_synthetic_steps.py。
运行命令: python3 -m src.synthetic.generate_pilot_synthetic。
主要统计结果: synthetic 总数 120；GSM8K 80，MATH 40；每类 synthetic_type 至少 9 条；generation_failures 0。
失败或不确定点: synthetic 是规则模板，不是 LLM 生成自然学生解法。
是否需要人工 review: 是，确认 synthetic trace 真实性是否足够 pilot 初筛。

### Card 3.3 DeepSeek API client
- [x] 实现 src/llm/deepseek_client.py
- [x] 实现 src/llm/json_repair.py
- [x] 创建 configs/deepseek.yaml
- [x] 创建 .env.example
- [x] 添加 .env ignore
- [x] 输出 data/reports/deepseek_client_dryrun.json

完成内容: 标准库 urllib 实现 OpenAI-compatible DeepSeek client，支持 dry-run、cache、retry、JSON parse 和失败记录。
生成文件: src/llm/deepseek_client.py, src/llm/json_repair.py, configs/deepseek.yaml, .env.example, data/reports/deepseek_client_dryrun.json。
运行命令: python3 -m src.llm.deepseek_client --dry-run；真实 API smoke。
主要统计结果: dry-run payload 合法；deepseek-v4-pro smoke 成功；全量 labeler 首个 pilot 请求等待数分钟未完成，被中断。
失败或不确定点: 本轮未完成真实 DeepSeek 全量自动标注；fallback 结果不得当作真实 DeepSeek 指标。
是否需要人工 review: 是，决定是否改用更快模型或继续 deepseek-v4-pro 长跑。

### Card 3.4 DeepSeek pedagogical label generator
- [x] 实现 src/labels/deepseek_labeler.py
- [x] 实现 src/labels/deepseek_prompts.py
- [x] 实现 src/labels/validate_deepseek_labels.py
- [x] 输出 data/pilot/pilot_pool.autolabeled.jsonl
- [x] 输出 data/cache/deepseek/label_requests.jsonl
- [x] 输出 data/cache/deepseek/label_responses.jsonl
- [x] 输出 data/reports/deepseek_label_failures.jsonl
- [x] 输出 data/reports/deepseek_label_summary.json

完成内容: 生成 240 条 auto-silver autolabeled 样本；由于真实全量 API 未完成，当前 autolabeled 为 heuristic fallback，并明确写入 model_name。
生成文件: src/labels/deepseek_labeler.py, src/labels/deepseek_prompts.py, src/labels/validate_deepseek_labels.py。
运行命令: python3 -m src.labels.deepseek_labeler; python3 -m src.data.validate_schema --jsonl data/pilot/pilot_pool.autolabeled.jsonl。
主要统计结果: output 240；parse_rate 1.0；schema pass 1.0；最大 repair 类别 106/240，未超过 70%。
失败或不确定点: api_available=false in summary；真实 DeepSeek 全量标注未完成。
是否需要人工 review: 是，不能把 fallback 指标作为模型能力结论。

### Card 3.5 自动评估 DeepSeek labels
- [x] 实现 src/eval/eval_deepseek_labels.py
- [x] 实现 src/reports/make_auto_pilot_report.py
- [x] 输出 deepseek_stepverify_eval.csv
- [x] 输出 deepseek_synthetic_eval.csv
- [x] 输出 deepseek_label_distribution.json
- [x] 输出 reports/auto_pilot_label_report.md

完成内容: 评估 StepVerify first-error、synthetic known labels 和分布可行性。
生成文件: src/eval/eval_deepseek_labels.py, src/reports/make_auto_pilot_report.py。
运行命令: python3 -m src.eval.eval_deepseek_labels; python3 -m src.reports.make_auto_pilot_report。
主要统计结果: fallback StepVerify first_wrong_step_acc 1.0；synthetic repair macro F1 1.0；first_wrong_step != earliest_actionable_step ratio 0.0375，低于 0.10 Go 条件。
失败或不确定点: 指标来自 fallback，不是完整 DeepSeek API 输出。
是否需要人工 review: 是，当前不建议进入训练。

### Card 3.6 DeepSeek self-consistency test
- [x] 实现 src/eval/deepseek_self_consistency.py
- [x] 输出 data/reports/deepseek_self_consistency.csv
- [x] 输出 data/reports/deepseek_self_consistency_disagreements.jsonl

完成内容: 对 80 条样本执行 fallback self-consistency 结构测试。
生成文件: src/eval/deepseek_self_consistency.py。
运行命令: python3 -m src.eval.deepseek_self_consistency。
主要统计结果: 80 条；各字段 agreement 1.0；disagreement 0。
失败或不确定点: fallback deterministic agreement 不能代表真实 DeepSeek 多温度稳定性。
是否需要人工 review: 是，真实 API 自一致性仍需重跑。

### Card 3.7 自动 tutor feedback 小实验
- [x] 实现 src/eval/build_tutor_auto_inputs.py
- [x] 实现 src/eval/run_deepseek_tutor_generation.py
- [x] 实现 src/eval/eval_tutor_auto.py
- [x] 输出 data/reports/tutor_auto_eval.csv
- [x] 输出 data/reports/tutor_t2_t3_examples.jsonl
- [x] 输出 reports/tutor_auto_ablation_report.md

完成内容: 构造 60 条样本的 T2/T3 输入并用 heuristic fallback 生成/评价 tutor response。
生成文件: src/eval/build_tutor_auto_inputs.py, src/eval/run_deepseek_tutor_generation.py, src/eval/eval_tutor_auto.py。
运行命令: python3 -m src.eval.build_tutor_auto_inputs; python3 -m src.eval.run_deepseek_tutor_generation; python3 -m src.eval.eval_tutor_auto。
主要统计结果: 120 条 T2/T3 response/eval rows。
失败或不确定点: 不是 DeepSeek tutor generation/evaluator 真实结果，只能验证数据管线。
是否需要人工 review: 是，真实 T2/T3 ablation 需在 API throughput 可接受后重跑。

### Card 3.8 Auto-Silver Pilot Review Report
- [x] 创建 reports/review_gate_3_auto.md
- [x] 创建 data/reports/review_gate_3_auto_summary.json
- [x] 包含失败案例 30 条
- [x] 包含成功案例 20 条
- [x] 更新 tasks/status.md

完成内容: 生成 Gate 3 自动报告，明确本轮停止，不进入训练、不构建 full dataset。
生成文件: reports/review_gate_3_auto.md, data/reports/review_gate_3_auto_summary.json, data/reports/review_gate_3_failure_cases_30.json, data/reports/review_gate_3_success_cases_20.json。
运行命令: python3 -m compileall -q src; python3 -m src.labels.lint_boundary_cases; python3 -m src.data.validate_schema --jsonl data/pilot/pilot_pool.autolabeled.jsonl; python3 -m pytest。
主要统计结果: compileall passed；boundary lint passed；autolabeled schema 240/240 passed；pytest unavailable。
失败或不确定点: 真实 DeepSeek 全量标注未完成；fallback 新标签差异比例低于 Go 条件。
是否需要人工 review: 是，决定重跑真实 DeepSeek、切换更快模型，或先做小样本人核查。

### Card 3.9 Real DeepSeek Throughput + Small-Batch Label Validation
- [x] 支持 DeepSeek model override
- [x] 支持 compact prompt throughput probe
- [x] 修复 thinking disabled 与 reasoning_effort 同时设置导致的 HTTP 400
- [x] 对 deepseek-v4-flash 做真实小批量验证
- [x] 对 deepseek-v4-pro 做真实小批量验证
- [x] 输出 data/reports/deepseek_small_batch_comparison.json
- [x] 输出 reports/deepseek_small_batch_validation.md

完成内容: 添加真实 API 小批量吞吐验证脚本，并实测 compact prompt 下 flash/pro 可用性；未覆盖现有 240 条 fallback autolabeled 文件。
生成文件: src/labels/deepseek_small_batch.py, reports/deepseek_small_batch_validation.md, data/reports/deepseek_small_batch_comparison.json, data/reports/deepseek_small_batch_deepseek-v4-flash_summary.json, data/reports/deepseek_small_batch_deepseek-v4-pro_summary.json。
运行命令: python3 -m src.labels.deepseek_small_batch --limit 20 --models deepseek-v4-flash --timeout-seconds 30 --max-tokens 400; python3 -m src.labels.deepseek_small_batch --limit 2 --models deepseek-v4-pro --timeout-seconds 45 --max-tokens 400; python3 -m compileall -q src。
主要统计结果: deepseek-v4-flash 20/20 成功，parse/schema 1.0，平均延迟 2.658s，最大 3.71s；deepseek-v4-pro 2/2 成功，parse/schema 1.0，平均延迟 4.23s，最大 4.611s。
失败或不确定点: 早期小批量尝试因 invalid config 失败，已定位为 reasoning_effort 与 thinking.disabled 冲突并修复；pro 只测 2 条，未跑 20 条。
是否需要人工 review: 是，建议下一步用 deepseek-v4-flash 跑全量 240 条真实 auto labels，再重跑 Gate 3。
