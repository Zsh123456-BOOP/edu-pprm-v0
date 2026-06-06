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
