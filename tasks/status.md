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

## Phase 2

### Card 2.1 Edu-PPRM schema
- [ ] 未开始，Review Gate 1 后再决定

### Card 2.2 标签 taxonomy
- [ ] 未开始，Review Gate 1 后再决定
