下面是一份**可直接交给 Codex 执行的方向 1 开发任务卡**。重点是：**先小规模验证问题是否成立，不要一开始大规模构建完整数据集**。如果 pilot 证明“最早可干预错误 / minimal repair”确实比已有 first-error detection 有独立价值，再进入完整数据集与实验阶段。

你的手写数据这一阶段**只预留字段，不纳入主线**。原因是当前上传样本的 JSON 主要是 `noise` 区域框，不是题干、学生步骤、最早错误或 repair 标签，不能支撑方向 1 的核心验证。

---

# Codex 总任务名称

```text
Edu-PPRM-v0: Pedagogical Process Verification Dataset and Pilot Experiments
```

目标：

```text
构建一个 text-only 教育过程验证数据集，用于验证：
1. earliest actionable intervention 是否区别于 first wrong step；
2. minimal repair policy 是否能稳定标注；
3. minimal repair policy 是否比 StepVerify-style error description 更能改善 tutor feedback。
```

不要做：

```text
不要纳入当前残缺手写数据；
不要做 VLM；
不要做方向 2 budget sweep；
不要做方向 3 scaffold distillation；
不要直接全量训练大模型；
不要把 first-error detection 包装成新贡献。
```

已有边界：

StepVerify 已经做了 1K 级学生 stepwise math reasoning chains，并由教师标注 first error step；它还证明 verifier grounding 能改善 tutor response。([arXiv][1])
ProcessBench 已经把“识别数学推理中最早错误步骤”做成 3,400 个专家标注样例的通用 benchmark。([arXiv][2])
MathEDU 已经包含真实学生解题过程和教师反馈，并评估 correctness、error identification 和 feedback generation。([arXiv][3])
BEA 2025 Shared Task 已经评估 tutor response 的 mistake identification、mistake location、guidance、actionability 等维度。([arXiv][4])

所以本项目的新意只能是：

```text
不是“找第一个错误”，而是：
把 process verifier 变成 tutor 的结构化干预选择器：
first_wrong_step
+ earliest_actionable_step
+ intervention_needed
+ minimal_repair_type
+ hint_level
+ leakage_constraint
```

---

# 0. 项目总结构要求

## Codex 需要创建的目录

```text
edu-pprm/
  README.md
  pyproject.toml
  tasks/
    status.md
    review_checkpoints.md
  configs/
    data_sources.yaml
    label_taxonomy.yaml
    split_policy.yaml
    model/
      qwen2_5_math_7b_lora.yaml
      qwen3_8b_lora.yaml
  schemas/
    edu_pprm.schema.json
    raw_dataset_registry.schema.json
    annotation.schema.json
    tutor_eval.schema.json
  data/
    raw/
    external/
    interim/
    pilot/
    processed/
    gold/
    synthetic/
    stress/
    reports/
  src/
    data/
      dataset_registry.py
      load_stepverify.py
      load_mathedu.py
      load_prm800k.py
      load_processbench.py
      load_gsm8k.py
      load_math.py
      normalize_steps.py
      build_pilot_pool.py
      build_full_dataset.py
      split_by_problem.py
      validate_schema.py
    labels/
      taxonomy.py
      convert_stepverify_labels.py
      convert_mathedu_labels.py
      generate_initial_labels.py
      adjudication.py
      agreement.py
    synthetic/
      inject_math_errors.py
      generate_student_traces.py
      verify_synthetic_steps.py
    annotation/
      streamlit_labeler.py
      export_annotation_batch.py
      import_teacher_labels.py
    eval/
      metrics.py
      eval_first_error.py
      eval_actionable.py
      eval_tutor_intervention.py
      build_stress_tests.py
    models/
      prompts.py
      llm_judge.py
      verifier_json_sft.py
      prm800k_baseline.py
    training/
      train_sft.py
      train_dpo.py
      build_dpo_pairs.py
    reports/
      make_pilot_report.py
      make_dataset_report.py
      make_experiment_tables.py
  tests/
    test_schema.py
    test_split_leakage.py
    test_label_taxonomy.py
    test_metric_examples.py
```

## Codex 必须维护任务勾选文件

Codex 每完成一项，在下面文件中勾选：

```text
tasks/status.md
```

格式：

```markdown
# Edu-PPRM-v0 Task Status

## Phase 0
- [ ] 0.1 Initialize repository
- [ ] 0.2 Add dataset registry
- [ ] 0.3 Add schema validation
...
```

每个任务完成时，Codex 必须写：

```text
完成内容
生成文件
运行命令
主要统计结果
失败或不确定点
是否需要人工 review
```

---

# Phase 0：项目初始化与执行约束

## Card 0.1 初始化仓库

**目标**
创建可复现实验工程结构。

**Codex 勾选项**

```markdown
- [ ] 创建目录结构
- [ ] 创建 pyproject.toml
- [ ] 添加 README.md
- [ ] 添加 tasks/status.md
- [ ] 添加 tasks/review_checkpoints.md
- [ ] 添加基础 pytest 配置
```

**验收标准**

```text
pytest 能运行；
README 说明当前只做方向 1；
tasks/status.md 中包含所有任务卡清单。
```

**需要回传 review**

```text
README.md
tasks/status.md
目录树截图或 tree 输出
```

---

## Card 0.2 明确禁止范围

**目标**
防止 Codex 误把方向 2/3 或手写数据纳入主线。

**Codex 勾选项**

```markdown
- [ ] 在 README 中写明：当前只做 text-only Edu-PPRM-v0
- [ ] 在 schema 中预留 handwrite 字段，但默认 null
- [ ] 在 schema 中预留 budget_data 字段，但默认 null
- [ ] 在 schema 中预留 distillation_data 字段，但默认 null
- [ ] 添加 tests/test_scope_guard.py，检查 pilot/full 数据不得依赖 handwrite 字段
```

**验收标准**

```text
pilot 和 full 数据构建脚本默认不读取手写图片；
handwrite 字段只能作为 metadata placeholder。
```

**需要回传 review**

```text
README 中的 scope section
schema 中 reserved fields
```

---

# Phase 1：数据源注册与字段摸底

这一阶段只做“接入和摸底”，不做大规模构造。

---

## Card 1.1 数据源 registry

**目标**
建立统一数据源登记表，记录来源、许可、用途和字段覆盖情况。

**Codex 勾选项**

```markdown
- [ ] 创建 configs/data_sources.yaml
- [ ] 创建 schemas/raw_dataset_registry.schema.json
- [ ] 实现 src/data/dataset_registry.py
- [ ] 为每个数据源登记：source_name、url_or_path、license、task_use、allowed_split、release_flag
```

**数据源初始列表**

```yaml
sources:
  stepverify:
    role: core_first_error_student_reasoning
    use_for: [pilot, gold_candidate, baseline]
  mathedu:
    role: authentic_student_solution_teacher_feedback
    use_for: [pilot, gold_candidate, full_train]
  gsm8k:
    role: problem_bank_for_synthetic_student_errors
    use_for: [synthetic_train, synthetic_pilot]
  math:
    role: problem_bank_for_synthetic_student_errors
    use_for: [synthetic_train, synthetic_eval]
  prm800k:
    role: generic_prm_pretrain_or_baseline
    use_for: [baseline, optional_pretrain]
  processbench:
    role: external_first_error_benchmark
    use_for: [external_eval_only]
```

**验收标准**

```text
python -m src.data.dataset_registry --check
能输出所有数据源用途；
不能把 external_eval_only 数据混入训练。
```

**需要回传 review**

```text
configs/data_sources.yaml
数据源用途表
是否存在许可/下载不确定的数据源
```

---

## Card 1.2 StepVerify loader

**目标**
把 StepVerify 转成内部 raw format。

**背景边界**
StepVerify 已经做了 first-error student reasoning verification，因此它是最直接相关 baseline，不是你的新贡献来源。([arXiv][1])

**Codex 勾选项**

```markdown
- [ ] 实现 src/data/load_stepverify.py
- [ ] 读取原始字段
- [ ] 映射 problem、reference_solution、student_solution、incorrect_index、error_category、error_description
- [ ] 输出 data/interim/stepverify.raw.jsonl
- [ ] 生成字段覆盖率报告
```

**内部 raw format**

```json
{
  "source": "stepverify",
  "source_id": "...",
  "problem_text": "...",
  "reference_solution_raw": "...",
  "student_solution_raw": "...",
  "first_wrong_step_source": 3,
  "error_category_source": "...",
  "error_description_source": "...",
  "dialog_history": "...",
  "metadata": {}
}
```

**验收标准**

```text
至少成功转换 95% 以上样本；
缺字段样本单独输出到 data/reports/stepverify_missing_fields.csv；
随机导出 20 条样本供人工查看。
```

**需要回传 review**

```text
data/reports/stepverify_summary.json
data/reports/stepverify_20_examples.jsonl
字段覆盖率表
```

---

## Card 1.3 MathEDU loader

**目标**
把 MathEDU 转成内部 raw format。

**背景边界**
MathEDU 已经包含真实学生解题过程和教师反馈，并评估错误识别和反馈生成。([arXiv][3])

**Codex 勾选项**

```markdown
- [ ] 实现 src/data/load_mathedu.py
- [ ] 映射 problem、student_solution、teacher_feedback、correctness、error_type、teacher_advice
- [ ] 输出 data/interim/mathedu.raw.jsonl
- [ ] 标记哪些样本有 step-level 信息，哪些只有整体反馈
```

**验收标准**

```text
能区分：
1. 可用于 step-level pilot 的样本；
2. 只能用于 feedback/tutor evaluation 的样本；
3. 字段不足样本。
```

**需要回传 review**

```text
data/reports/mathedu_summary.json
data/reports/mathedu_20_examples.jsonl
哪些字段能可靠映射到本项目标签
```

---

## Card 1.4 GSM8K / MATH loader

**目标**
建立合成错误学生过程的题库来源。

**Codex 勾选项**

```markdown
- [ ] 实现 src/data/load_gsm8k.py
- [ ] 实现 src/data/load_math.py
- [ ] 提取 problem_text、gold_answer、gold_solution
- [ ] 拆分 gold_solution_steps
- [ ] 输出 data/interim/problem_bank.raw.jsonl
```

**注意事项**

```text
不要使用 test split 生成训练数据；
不要让同一道题不同变体跨 split；
不要把 gold answer 泄露给模型输入，除非实验条件明确要求。
```

**验收标准**

```text
每道题有 problem_id；
每道题有 source_split；
每道题有 gold_answer；
至少 70% 样本能拆出 2 个以上步骤。
```

**需要回传 review**

```text
data/reports/problem_bank_summary.json
随机 30 条拆步样本
```

---

## Card 1.5 PRM800K / ProcessBench loader

**目标**
接入通用 PRM / first-error benchmark，用于 baseline 和外部评测。

**背景边界**
PRM800K 是通用 step-level correctness supervision；ProcessBench 是 earliest error benchmark。PRM800K 不能替代教育 repair 标签，ProcessBench 不能混入训练。([arXiv][2])

**Codex 勾选项**

```markdown
- [ ] 实现 src/data/load_prm800k.py
- [ ] 实现 src/data/load_processbench.py
- [ ] PRM800K 输出 step correctness 格式
- [ ] ProcessBench 输出 external eval 格式
- [ ] 添加 split guard，禁止 ProcessBench 进入训练
```

**验收标准**

```text
ProcessBench 只出现在 data/external_eval；
PRM800K 可以作为 baseline/pretrain，但不能作为 pedagogical repair 标签来源。
```

**需要回传 review**

```text
data/reports/prm800k_summary.json
data/reports/processbench_summary.json
```

---

# Review Gate 1：数据源是否足够支撑 pilot

Codex 完成 Phase 1 后，必须停止，并把以下内容发给你 review：

```text
1. 所有数据源 summary.json
2. 每个数据源 20 条样本
3. 字段覆盖率表
4. 哪些字段可以映射到：
   - first_wrong_step
   - error_category
   - error_description
   - teacher_feedback
5. 哪些字段不能直接映射到：
   - earliest_actionable_step
   - minimal_repair_type
   - hint_level
   - leakage_risk
```

你 review 后决定：

```text
继续 Phase 2；
或者先修正数据源映射；
或者删除某个质量差的数据源。
```

---

# Phase 2：统一 schema 与标签体系

---

## Card 2.1 Edu-PPRM schema

**目标**
定义方向 1 的统一数据结构。

**Codex 勾选项**

```markdown
- [ ] 创建 schemas/edu_pprm.schema.json
- [ ] 实现 src/data/validate_schema.py
- [ ] 所有样本必须通过 schema 校验
```

**核心 schema**

```json
{
  "sample_id": "edu_pprm_000001",
  "problem": {
    "problem_id": "gsm8k_train_000001",
    "source": "gsm8k",
    "source_split": "train",
    "problem_text": "...",
    "reference_solution_steps": [
      {"step_id": 1, "text": "..."}
    ],
    "gold_answer": "...",
    "topic": null,
    "difficulty": null
  },
  "student_trace": {
    "trace_id": "trace_000001",
    "trace_source": "stepverify | mathedu | synthetic_rule | synthetic_llm",
    "student_steps": [
      {"step_id": 1, "text": "..."}
    ],
    "student_final_answer": "...",
    "is_correct": false
  },
  "existing_labels": {
    "first_wrong_step": 3,
    "error_category": "...",
    "error_description": "..."
  },
  "pedagogical_labels": {
    "intervention_needed": null,
    "earliest_actionable_step": null,
    "minimal_repair_type": null,
    "repair_target": null,
    "hint_level": null,
    "leakage_constraint": null,
    "actionable_diff_reason": null
  },
  "label_metadata": {
    "quality_tier": "raw | silver | gold",
    "label_source": "converted | auto | teacher | adjudicated",
    "annotator_ids": [],
    "adjudication_status": "none | pending | adjudicated"
  },
  "reserved": {
    "budget_data": null,
    "distillation_data": null,
    "handwrite_data": null
  }
}
```

**验收标准**

```text
所有 Phase 1 数据源都能转换成 schema；
缺失字段必须显式为 null，不得随意脑补。
```

**需要回传 review**

```text
schema 文件
5 条 StepVerify 转换样本
5 条 MathEDU 转换样本
5 条 synthetic placeholder 样本
```

---

## Card 2.2 标签 taxonomy

**目标**
定义本项目真正的新标签。

**Codex 勾选项**

```markdown
- [ ] 创建 configs/label_taxonomy.yaml
- [ ] 实现 src/labels/taxonomy.py
- [ ] 添加 tests/test_label_taxonomy.py
```

**标签定义**

```yaml
intervention_needed:
  true: 学生当前过程需要 tutor 介入
  false: 不需要介入，例如无错、已自我修正、信息不足不能安全判断

earliest_actionable_step:
  definition: 老师最早应该介入的位置，不一定等于 first_wrong_step
  allowed:
    - integer step_id
    - null

minimal_repair_type:
  - no_intervention_needed
  - ask_to_recompute_local_expression
  - ask_to_reinterpret_given_quantity
  - ask_to_rewrite_equation_or_expression
  - ask_to_check_operation_or_formula
  - ask_to_check_unit_conversion
  - ask_to_justify_inference
  - ask_to_compare_with_problem_condition
  - ask_to_substitute_back
  - ask_clarifying_question
  - insufficient_information

hint_level:
  - none
  - low
  - medium
  - high
  - forbidden_full_solution

leakage_constraint:
  - do_not_reveal_final_answer
  - do_not_solve_next_step
  - can_point_to_local_step_only
  - can_name_error_type
  - can_show_micro_example
```

**验收标准**

```text
taxonomy 中每个 label 都有：
定义；
正例；
反例；
容易混淆的情况。
```

**需要回传 review**

```text
configs/label_taxonomy.yaml
标签说明文档
```

---

## Card 2.3 first_wrong_step vs earliest_actionable_step 边界规则

**目标**
把“不是换名”的边界写清楚。

**Codex 勾选项**

```markdown
- [ ] 创建 docs/annotation_guideline.md
- [ ] 写清楚 first_wrong_step 和 earliest_actionable_step 区别
- [ ] 写 20 个边界例子
- [ ] 每个例子给推荐标签
```

**必须覆盖的边界情况**

```text
1. 第一处错误只是格式/表述问题，不值得介入
2. 学生先错后自我修正
3. 学生跳步但数学上没错
4. 学生路径不同于 reference solution，但仍然正确
5. 题目理解错误发生在第一步
6. 局部计算错但不影响最终答案
7. 最终答案对但过程错
8. 最终答案错但前面若干步正确
9. 错误位置不可唯一确定
10. 学生步骤太少，无法判断
11. 学生把题目条件抄错
12. 学生用了正确公式但代入错
13. 学生用了错误公式但计算正确
14. 多个错误同时出现
15. 需要先问澄清问题
16. tutor 若提示会直接泄露答案
17. no-error 样本
18. reference solution 不唯一
19. 题目本身有歧义
20. teacher 之间可能分歧的样本
```

**验收标准**

```text
每个边界例子都给：
first_wrong_step
earliest_actionable_step
intervention_needed
minimal_repair_type
hint_level
leakage_constraint
reason
```

**需要回传 review**

```text
docs/annotation_guideline.md
20 个边界例子
```

---

# Review Gate 2：标签定义是否值得进入 pilot

Codex 完成 Phase 2 后暂停，回传：

```text
1. schema
2. taxonomy
3. annotation guideline
4. 20 个边界例子
5. Codex 对当前定义的疑问清单
```

你 review 重点：

```text
标签是否太多；
老师是否能标；
earliest_actionable_step 是否真的区别于 first_wrong_step；
minimal_repair_type 是否够稳定；
hint_level 是否会太主观。
```

如果标签太复杂，先删减。建议 pilot 阶段最多保留：

```text
intervention_needed
earliest_actionable_step
minimal_repair_type
hint_level
leakage_constraint
```

不要让 pilot 过载。

---

# Phase 3：Pilot 数据集构建

目标：先做 200–300 条，不扩量。

---

## Card 3.1 pilot pool 采样

**目标**
构建 200–300 条 pilot 样本，覆盖 StepVerify、MathEDU、少量 synthetic。

**Codex 勾选项**

```markdown
- [ ] 实现 src/data/build_pilot_pool.py
- [ ] 从 StepVerify 抽 120 条
- [ ] 从 MathEDU 抽 80 条
- [ ] 从 GSM8K synthetic 抽 80 条
- [ ] 保证 no-error / wrong / ambiguous 样本都有
- [ ] 输出 data/pilot/pilot_pool.raw.jsonl
```

**推荐采样比例**

```text
StepVerify: 120
MathEDU: 80
Synthetic GSM8K: 80
总计: 280
```

**采样分层**

```text
error_category
first_wrong_step_position
student_solution_length
source_dataset
no_error_or_correct
```

**验收标准**

```text
总样本 200–300；
每个 source 至少 50 条；
每条样本有 problem、reference_solution、student_steps；
first_wrong_step 已有或可自动预标。
```

**需要回传 review**

```text
data/reports/pilot_pool_summary.json
data/pilot/pilot_pool_30_examples.jsonl
```

---

## Card 3.2 synthetic GSM8K pilot 生成

**目标**
生成小规模可控错误学生解法，补齐 StepVerify/MathEDU 不覆盖的边界。

**Codex 勾选项**

```markdown
- [ ] 实现 src/synthetic/inject_math_errors.py
- [ ] 支持 5 类错误注入
- [ ] 生成 80 条 synthetic pilot 样本
- [ ] 保存 injected_error_step 和 injected_error_type
```

**第一版只做 5 类**

```yaml
synthetic_error_types:
  - arithmetic_error
  - sign_error
  - wrong_operation
  - misread_given_quantity
  - unit_conversion_error
```

**禁止**

```text
不要生成太复杂的多错样本；
不要一条样本注入多个主错误；
不要让 LLM 自由发挥导致标签不可控。
```

**验收标准**

```text
80 条样本；
每条只有一个主错误；
injected_error_step 可追踪；
人工抽样 20 条看起来合理。
```

**需要回传 review**

```text
20 条 synthetic 样本
错误类型分布
Codex 发现的生成失败案例
```

---

## Card 3.3 自动预标 pedagogical labels

**目标**
先用规则 + LLM prompt 给 pilot 样本做初始标签，降低老师负担。

**Codex 勾选项**

```markdown
- [ ] 实现 src/labels/generate_initial_labels.py
- [ ] 输入 pilot_pool.raw.jsonl
- [ ] 输出 pilot_pool.prelabeled.jsonl
- [ ] 每条样本给 pedagogical_labels 初稿
- [ ] 标记 confidence 和 needs_teacher_review
```

**预标策略**

```text
如果 synthetic_rule：
    first_wrong_step = injected_error_step
    earliest_actionable_step 默认 = injected_error_step
    repair_type 根据 injected_error_type 映射

如果 StepVerify：
    first_wrong_step = incorrect_index
    earliest_actionable_step 初始 = incorrect_index
    repair_type 从 error_category + error_description 映射

如果 MathEDU：
    根据 teacher_feedback 和 error_type 预映射
    低置信样本标 needs_teacher_review = true
```

**验收标准**

```text
所有 pilot 样本都有预标；
每个预标字段有 confidence；
不能把 null 字段强行填满。
```

**需要回传 review**

```text
data/pilot/pilot_pool.prelabeled.jsonl
30 条预标样本
repair_type 分布
低置信样本比例
```

---

## Card 3.4 标注界面

**目标**
让老师只核对，不从零标注。

**Codex 勾选项**

```markdown
- [ ] 实现 src/annotation/streamlit_labeler.py
- [ ] 支持加载 pilot_pool.prelabeled.jsonl
- [ ] 显示 problem、reference solution、student steps、已有 first_wrong_step
- [ ] 显示系统预标 pedagogical labels
- [ ] 老师可一键接受或修改
- [ ] 支持标记 ambiguous / unusable
- [ ] 支持导出 teacher labels
```

**界面必须显示**

```text
Problem
Reference solution
Student solution steps
Existing first wrong step
Error description
Proposed earliest actionable step
Proposed minimal repair type
Proposed hint level
Proposed leakage constraint
Reason
```

**老师操作**

```text
Accept all
Edit earliest_actionable_step
Edit intervention_needed
Edit minimal_repair_type
Edit hint_level
Edit leakage_constraint
Mark ambiguous
Mark unusable
Add note
```

**验收标准**

```text
老师标一条样本不超过 1 分钟；
导出 JSONL；
支持两个老师独立标注同一批样本。
```

**需要回传 review**

```text
标注界面截图
导出的 annotation schema
5 条模拟标注结果
```

---

## Card 3.5 双人标注与一致性计算

**目标**
计算“minimal repair 是否能稳定标”的关键证据。

**Codex 勾选项**

```markdown
- [ ] 实现 src/labels/agreement.py
- [ ] 支持两个 annotator 文件输入
- [ ] 计算 exact agreement
- [ ] 计算 Cohen's kappa
- [ ] 计算 per-label confusion matrix
- [ ] 输出 disagreement cases
```

**指标**

```text
first_wrong_step agreement
earliest_actionable_step agreement
intervention_needed kappa
minimal_repair_type kappa
hint_level agreement
leakage_constraint agreement
```

**判定建议**

```text
first_wrong_step kappa ≥ 0.65：可接受
intervention_needed kappa ≥ 0.50：可接受
minimal_repair_type kappa ≥ 0.40：勉强可继续
minimal_repair_type kappa < 0.30：标签体系太主观，需要重做
```

**验收标准**

```text
输出 agreement_report.json；
输出 disagreement_cases.jsonl；
能按 source_dataset 分开统计。
```

**需要回传 review**

```text
agreement_report.json
disagreement_cases 前 30 条
Codex 总结最容易分歧的标签
```

---

# Review Gate 3：Pilot 生死线

Codex 完成 Phase 3 后暂停，回传完整 pilot 报告。

## 必须回传

```text
1. pilot 样本数量和来源分布
2. first_wrong_step 与 earliest_actionable_step 不同的比例
3. actionable_diff_reason 分布
4. minimal_repair_type 分布
5. 老师一致性报告
6. 低置信 / ambiguous / unusable 比例
7. 30 条 disagreement cases
8. Codex 建议删除或合并的标签
```

## 是否继续的判定

### Go

满足以下条件可以继续：

```text
first_wrong_step != earliest_actionable_step 比例 ≥ 15%
minimal_repair_type kappa ≥ 0.40
ambiguous/unusable 比例 ≤ 20%
老师认为 repair_type 对反馈有实际意义
```

### Weak Go

如果：

```text
first_wrong_step != earliest_actionable_step 比例 10%–15%
但 minimal_repair_type 稳定且 downstream 有明显收益
```

可以继续，但论文主张要改成：

```text
不是 earliest actionable localization，
而是 minimal repair policy prediction。
```

### No-Go

如果：

```text
first_wrong_step != earliest_actionable_step 比例 < 10%
minimal_repair_type kappa < 0.30
老师认为 repair_type 不稳定
```

则不要继续把方向 1 当主论文。转向：

```text
方向 2 budget allocation
或方向 3 scaffold distillation
```

---

# Phase 4：问题存在性实验

这阶段只用 pilot 数据验证“这个问题是不是值得做”。

---

## Card 4.1 baseline prompt 实现

**目标**
先比较简单 baseline，不训练大模型。

**Codex 勾选项**

```markdown
- [ ] 实现 src/models/prompts.py
- [ ] 实现 src/models/llm_judge.py
- [ ] 添加 3 套 prompt
```

**Prompt 条件**

```text
P0: problem + student steps
P1: problem + reference solution + student steps
P2: problem + reference solution + aligned student/reference steps
```

**输出 JSON**

```json
{
  "first_wrong_step": 3,
  "earliest_actionable_step": 3,
  "intervention_needed": true,
  "minimal_repair_type": "ask_to_recompute_local_expression",
  "hint_level": "low",
  "leakage_constraint": "can_point_to_local_step_only"
}
```

**验收标准**

```text
JSON parse rate ≥ 95%；
无效 JSON 自动重试一次；
所有失败样本记录。
```

**需要回传 review**

```text
prompt 文本
20 条模型输出
JSON failure rate
```

---

## Card 4.2 规则 baseline

**目标**
建立非 LLM baseline。

**Codex 勾选项**

```markdown
- [ ] 实现 FinalAnswerJudge
- [ ] 实现 FirstWrongStepCopyBaseline
- [ ] 实现 ErrorCategoryToRepairMappingBaseline
- [ ] 实现 RandomRepairBaseline
```

**Baseline 定义**

```text
FinalAnswerJudge:
    只能判断最终答案对错，不能定位步骤

FirstWrongStepCopyBaseline:
    earliest_actionable_step = first_wrong_step

ErrorCategoryToRepairMappingBaseline:
    用 error_category 规则映射 repair_type

RandomRepairBaseline:
    按训练集分布随机猜 repair_type
```

**验收标准**

```text
每个 baseline 都能输出统一 JSON；
能在 pilot gold 上评估。
```

**需要回传 review**

```text
baseline 输出样例
规则映射表
```

---

## Card 4.3 pilot metrics

**目标**
实现方向 1 的核心指标。

**Codex 勾选项**

```markdown
- [ ] 实现 src/eval/metrics.py
- [ ] 支持 step accuracy
- [ ] 支持 off-by-one accuracy
- [ ] 支持 macro F1
- [ ] 支持 source-wise breakdown
- [ ] 支持 no-intervention F1
```

**指标列表**

```text
first_wrong_step_acc
earliest_actionable_step_acc
off_by_one_acc
intervention_needed_f1
minimal_repair_type_macro_f1
hint_level_acc
leakage_constraint_macro_f1
json_validity_rate
ambiguous_excluded_count
```

**验收标准**

```text
tests/test_metric_examples.py 通过；
指标能按 source_dataset 输出。
```

**需要回传 review**

```text
metrics.py
metric example tests
```

---

## Card 4.4 pilot baseline report

**目标**
生成问题存在性报告。

**Codex 勾选项**

```markdown
- [ ] 实现 src/reports/make_pilot_report.py
- [ ] 运行所有 baseline
- [ ] 生成 reports/pilot_problem_existence.md
- [ ] 生成 reports/pilot_metrics.csv
- [ ] 生成 reports/pilot_error_analysis.jsonl
```

**报告必须包含**

```text
1. 数据分布
2. first_wrong_step 与 earliest_actionable_step 差异比例
3. 哪些场景二者不同
4. repair_type 一致性
5. baseline 表现
6. LLM judge 是否已经足够强
7. 当前方向是否值得继续
```

**验收标准**

```text
报告中必须明确给出 Go / Weak Go / No-Go 建议；
不能只报平均指标，要有 case analysis。
```

**需要回传 review**

```text
reports/pilot_problem_existence.md
reports/pilot_metrics.csv
reports/pilot_error_analysis.jsonl
```

---

# Review Gate 4：是否扩展完整数据集

你 review pilot report 后做决策。

如果 No-Go：

```text
停止方向 1 全量数据构建；
保留已完成数据作为方向 2/3 的辅助探索；
不要继续训练 verifier。
```

如果 Go / Weak Go：

```text
进入 Phase 5，构建完整 Edu-PPRM-v0。
```

---

# Phase 5：完整数据集构建

只有 Gate 4 通过后执行。

---

## Card 5.1 完整数据集规模规划

**目标**
生成完整数据构建计划，不直接扩量。

**Codex 勾选项**

```markdown
- [ ] 创建 docs/full_dataset_plan.md
- [ ] 统计每个 source 可用样本
- [ ] 规划 gold/silver/bronze 比例
- [ ] 规划 train/dev/test split
- [ ] 规划 teacher annotation workload
```

**推荐规模**

```text
Gold test:
    300–500 条，老师核对

Gold dev:
    100–200 条，老师核对

Silver train:
    2,000–5,000 条，自动预标 + 抽样核对

Bronze synthetic train:
    20,000–50,000 条，自动生成

External eval:
    ProcessBench / PRMBench，只评测不训练
```

**验收标准**

```text
按 problem_id split；
同一道题的所有变体不得跨 split；
test split 不用于 prompt 调参。
```

**需要回传 review**

```text
docs/full_dataset_plan.md
预计样本数表
预计老师工作量
```

---

## Card 5.2 数据切分与泄漏防护

**目标**
防止 train/test 泄漏。

**Codex 勾选项**

```markdown
- [ ] 实现 src/data/split_by_problem.py
- [ ] 添加 tests/test_split_leakage.py
- [ ] 按 problem_id 切分
- [ ] 对同题不同 trace 做 group split
- [ ] 对 synthetic derived samples 保留 parent_problem_id
```

**禁止**

```text
同一道题的正确解法在 train，错误 trace 在 test；
同一道题的不同错误版本跨 split；
用 ProcessBench 参与训练；
用 test set 做 prompt 选择。
```

**验收标准**

```text
split leakage test 通过；
输出 train/dev/test problem overlap = 0。
```

**需要回传 review**

```text
split summary
overlap check report
```

---

## Card 5.3 StepVerify / MathEDU 完整转换

**目标**
把直接相关教育数据转换为 Edu-PPRM 格式。

**Codex 勾选项**

```markdown
- [ ] 转换 StepVerify 全量
- [ ] 转换 MathEDU 可用子集
- [ ] 应用 Phase 3 修订后的 label taxonomy
- [ ] 生成 silver labels
- [ ] 标记 teacher_review_needed
```

**验收标准**

```text
所有样本通过 schema；
低置信样本有 reason；
不可用样本单独输出。
```

**需要回传 review**

```text
转换数量
不可用比例
低置信样本示例
```

---

## Card 5.4 synthetic student traces 扩量

**目标**
从 GSM8K/MATH 生成 20k–50k 条可控学生错误 trace。

**Codex 勾选项**

```markdown
- [ ] 扩展 src/synthetic/inject_math_errors.py
- [ ] 支持 8–10 类错误
- [ ] 支持 LLM 改写为学生风格
- [ ] 保留 injected_error_step
- [ ] 保留 repair_type 自动映射
- [ ] 输出 synthetic_train.jsonl
```

**错误类型**

```yaml
error_types:
  - arithmetic_error
  - sign_error
  - wrong_operation
  - misread_given_quantity
  - unit_conversion_error
  - wrong_formula
  - equation_setup_error
  - substitution_error
  - distribution_error
  - premature_final_answer
```

**质量过滤**

```text
只保留单主错误样本；
学生步骤不少于 2 步；
LLM 改写后 injected_error_step 仍可定位；
格式不是完美 CoT，要像学生过程，但不能太乱。
```

**验收标准**

```text
20k+ synthetic traces；
每类错误至少 1k；
自动校验失败率报告；
抽样 100 条供老师查看。
```

**需要回传 review**

```text
100 条 synthetic 样本
错误类型分布
校验失败案例
```

---

## Card 5.5 teacher gold set 构建

**目标**
构建可用于论文主评测的 gold set。

**Codex 勾选项**

```markdown
- [ ] 从 StepVerify/MathEDU/synthetic 分层抽样 500 条
- [ ] 生成 teacher annotation batch
- [ ] 双人标注
- [ ] 自动计算一致性
- [ ] 输出 adjudication batch
- [ ] 导出 final gold set
```

**gold set 建议比例**

```text
StepVerify: 200
MathEDU: 150
Synthetic: 150
```

**验收标准**

```text
至少 300 条 adjudicated gold；
最好 500 条；
minimal_repair_type kappa 达到 Gate 3 标准；
ambiguous 样本不超过 20%。
```

**需要回传 review**

```text
gold_set_summary.json
agreement_report.json
disagreement_cases.jsonl
final label distribution
```

---

# Review Gate 5：完整数据集质量 review

Codex 暂停，回传：

```text
1. full dataset plan
2. train/dev/test 数量
3. gold/silver/bronze 数量
4. 标签分布
5. 老师一致性
6. synthetic 质量抽样
7. 不可用/ambiguous 样本比例
8. split leakage 检查报告
```

你决定：

```text
继续训练；
先修标签；
减少 synthetic 占比；
合并 repair_type；
或者只做数据论文/benchmark。
```

---

# Phase 6：Verifier 训练与 baseline

---

## Card 6.1 统一输入输出格式

**目标**
把数据转成模型训练格式。

**Codex 勾选项**

```markdown
- [ ] 实现 src/data/build_training_format.py
- [ ] 生成 sft_train.jsonl
- [ ] 生成 sft_dev.jsonl
- [ ] 生成 gold_test.jsonl
```

**输入模板**

```text
You are a pedagogical process verifier.

Problem:
{problem_text}

Reference solution:
Step 1: ...
Step 2: ...

Student solution:
Step 1: ...
Step 2: ...

Task:
Return JSON with:
first_wrong_step,
earliest_actionable_step,
intervention_needed,
minimal_repair_type,
repair_target,
hint_level,
leakage_constraint.
```

**输出模板**

```json
{
  "first_wrong_step": 3,
  "earliest_actionable_step": 3,
  "intervention_needed": true,
  "minimal_repair_type": "ask_to_recompute_local_expression",
  "repair_target": "Step 3",
  "hint_level": "low",
  "leakage_constraint": "can_point_to_local_step_only"
}
```

**验收标准**

```text
所有 target JSON 可解析；
训练集中不包含 gold test；
不把 teacher notes 放进模型输入。
```

**需要回传 review**

```text
20 条训练格式样本
输入长度统计
target JSON 合法率
```

---

## Card 6.2 baseline 评测

**目标**
在训练前先跑所有 baseline。

**Codex 勾选项**

```markdown
- [ ] FinalAnswerJudge
- [ ] FirstWrongStepCopyBaseline
- [ ] ErrorCategoryToRepairMappingBaseline
- [ ] LLM-as-a-Judge
- [ ] PRM800K baseline
- [ ] StepVerify-style verifier baseline
```

**主指标**

```text
first_wrong_step_acc
earliest_actionable_step_acc
off_by_one_acc
intervention_needed_f1
minimal_repair_type_macro_f1
hint_level_acc
leakage_constraint_macro_f1
```

**验收标准**

```text
每个 baseline 都在 dev 和 gold_test 上有结果；
每个 baseline 都输出错误案例。
```

**需要回传 review**

```text
reports/baseline_results.csv
reports/baseline_error_cases.jsonl
```

---

## Card 6.3 SFT verifier

**目标**
训练第一个 generative JSON verifier。

**Codex 勾选项**

```markdown
- [ ] 实现 src/training/train_sft.py
- [ ] 支持 LoRA
- [ ] 支持 Qwen2.5-Math-7B
- [ ] 支持 Qwen3-8B
- [ ] 支持 resume
- [ ] 支持 dev eval
```

**训练约束**

```text
先训小样本 smoke test；
再训 full train；
sequence length 2k–4k；
不要训练 VLM；
不要做 RL；
不要过度调参 test set。
```

**验收标准**

```text
smoke test 成功；
dev JSON parse rate ≥ 98%；
dev minimal_repair_type F1 超过规则 baseline；
dev earliest_actionable_step_acc 不低于 LLM judge 太多。
```

**需要回传 review**

```text
训练日志
dev 结果
50 条预测样本
失败样本分析
```

---

## Card 6.4 DPO repair policy

**目标**
如果 SFT 已有可用结果，再做 DPO 强化 minimal repair / non-leakage。

**Codex 勾选项**

```markdown
- [ ] 实现 src/training/build_dpo_pairs.py
- [ ] 构造 chosen/rejected pair
- [ ] 实现 src/training/train_dpo.py
- [ ] 评估 DPO 前后变化
```

**chosen / rejected 规则**

```text
chosen:
    正确定位
    repair_type 正确
    hint_level 合适
    leakage_constraint 合理

rejected:
    位置错
    repair_type 泛泛
    hint_level 过高
    直接泄露答案
    full solution
```

**验收标准**

```text
DPO 后 leakage_constraint 指标提升；
minimal_repair_type 不下降超过 2 个点；
JSON 合法率不下降。
```

**需要回传 review**

```text
DPO pairs 样例 50 条
DPO 前后指标对比
DPO 后错误案例
```

---

# Phase 7：Stress Test

---

## Card 7.1 stress test 构造

**目标**
构造能证明 verifier 不是走捷径的测试集。

**Codex 勾选项**

```markdown
- [ ] 实现 src/eval/build_stress_tests.py
- [ ] 构造 8 类 stress cases
- [ ] 每类至少 50 条
- [ ] 输出 data/stress/stress_test.jsonl
```

**8 类 stress case**

```text
1. final_answer_correct_but_process_wrong
2. final_answer_wrong_but_prefix_correct
3. first_error_self_corrected
4. neat_format_wrong_logic
5. alternative_correct_solution
6. skipped_steps_but_correct
7. ambiguous_error_location
8. hint_would_leak_answer
```

**验收标准**

```text
至少 400 条 stress cases；
每条有 stress_type；
每类有人工检查样本。
```

**需要回传 review**

```text
每类 10 条样本
stress_type 分布
Codex 认为最难构造的类型
```

---

## Card 7.2 stress test 评测

**目标**
比较不同模型在边界情况上的鲁棒性。

**Codex 勾选项**

```markdown
- [ ] 在 stress_test 上跑所有 baseline
- [ ] 在 stress_test 上跑 SFT/DPO verifier
- [ ] 输出 per-stress-type 指标
- [ ] 输出 shortcut failure examples
```

**关键指标**

```text
self_correction_false_intervention_rate
alternative_solution_false_positive_rate
format_bias_rate
leakage_constraint_failure_rate
ambiguous_overclaim_rate
```

**验收标准**

```text
报告中说明模型主要失败模式；
不能只报总分。
```

**需要回传 review**

```text
reports/stress_results.csv
reports/stress_failure_cases.md
```

---

# Phase 8：Downstream Tutor Intervention

这是证明方向 1 有意义的最关键实验。

---

## Card 8.1 tutor condition 构造

**目标**
固定同一个 tutor，只改变 verifier signal。

**Codex 勾选项**

```markdown
- [ ] 实现 src/eval/build_tutor_intervention_inputs.py
- [ ] 为每条 gold test 样本生成 T0–T4 五种输入
- [ ] 确保 tutor base model、temperature、max_tokens 完全一致
```

**五种条件**

```text
T0: no verifier
T1: final correctness only
T2: StepVerify-style first error + error description
T3: your structured repair policy
T4: oracle teacher repair policy
```

**T3 输入格式**

```json
{
  "first_wrong_step": 3,
  "earliest_actionable_step": 3,
  "intervention_needed": true,
  "minimal_repair_type": "ask_to_recompute_local_expression",
  "repair_target": "Step 3",
  "hint_level": "low",
  "leakage_constraint": "can_point_to_local_step_only"
}
```

**验收标准**

```text
同一条样本五个条件除了 verifier signal 外完全一致；
不让 tutor 看到 gold answer，除非所有条件都看到。
```

**需要回传 review**

```text
10 条 T0–T4 输入样例
prompt 模板
```

---

## Card 8.2 tutor response 生成

**目标**
生成 tutor feedback，用于比较 structured repair policy 是否有效。

**Codex 勾选项**

```markdown
- [ ] 实现 src/eval/run_tutor_generation.py
- [ ] 固定 model、temperature、top_p、max_tokens
- [ ] 输出 tutor_responses.jsonl
- [ ] 记录 generation config
```

**输出格式**

```json
{
  "sample_id": "...",
  "condition": "T3",
  "tutor_response": "...",
  "generation_model": "...",
  "generation_config": {}
}
```

**验收标准**

```text
每条 gold 样本有 T0–T4 五个 response；
失败样本可重试；
response 不得混入 evaluator 信息。
```

**需要回传 review**

```text
每个条件 20 条 response
生成失败率
平均 token 数
```

---

## Card 8.3 tutor response 自动评估

**目标**
先用自动 evaluator 筛查 response 质量。

**Codex 勾选项**

```markdown
- [ ] 实现 src/eval/eval_tutor_intervention.py
- [ ] 评价 targeted
- [ ] 评价 correct
- [ ] 评价 actionable
- [ ] 评价 minimal
- [ ] 评价 non_leakage
- [ ] 评价 repair_consistent
- [ ] 输出自动评分报告
```

**评价维度**

```text
targeted:
    是否针对学生实际错误

correct:
    反馈内容是否数学正确

actionable:
    学生是否知道下一步做什么

minimal:
    是否没有过度解释

non_leakage:
    是否没有直接给最终答案或完整解法

repair_consistent:
    是否符合 minimal_repair_type

over_help:
    是否帮学生做了本该学生完成的下一步
```

**验收标准**

```text
每个 response 都有评分；
自动评分 prompt 独立于 tutor prompt；
输出低置信样本供人工评估。
```

**需要回传 review**

```text
自动评价 prompt
reports/tutor_auto_eval.csv
低置信样本 50 条
```

---

## Card 8.4 人工盲评包

**目标**
生成老师可盲评的 pairwise preference 数据。

**Codex 勾选项**

```markdown
- [ ] 实现 src/eval/build_blind_teacher_eval.py
- [ ] 隐藏 condition 名称
- [ ] 随机打乱 T0–T4 顺序
- [ ] 输出 pairwise 或 listwise 标注包
```

**老师评价问题**

```text
哪个反馈更适合学生下一步？
哪个反馈更少泄露答案？
哪个反馈更简洁？
哪个反馈更针对错误？
哪个反馈更符合最小修复？
```

**验收标准**

```text
老师看不到模型条件；
每条样本最多比较 2–3 个 response，避免工作量过大；
支持导入老师偏好。
```

**需要回传 review**

```text
盲评样例
老师工作量估计
评价表 schema
```

---

## Card 8.5 tutor intervention 结果报告

**目标**
证明 T3 是否真的优于 T2。

**Codex 勾选项**

```markdown
- [ ] 汇总自动评价
- [ ] 汇总人工偏好
- [ ] 对比 T2 vs T3
- [ ] 统计 token length
- [ ] 统计 leakage rate
- [ ] 统计 over-help rate
- [ ] 输出 reports/tutor_intervention_report.md
```

**关键判定**

```text
如果 T3 相比 T2：
    teacher preference ≥ 55%
    leakage rate 下降
    over-help rate 下降
    repair_consistent 提升
则 structured repair policy 有价值。

如果 T3 与 T2 无差异：
    方向 1 新意不足，需要收缩或转向。
```

**需要回传 review**

```text
reports/tutor_intervention_report.md
T2 vs T3 case studies
失败案例
```

---

# Phase 9：论文级主实验整理

---

## Card 9.1 主结果表

**Codex 勾选项**

```markdown
- [ ] 生成 main_results.csv
- [ ] 生成 per_source_results.csv
- [ ] 生成 per_error_type_results.csv
- [ ] 生成 per_repair_type_results.csv
```

**主表字段**

```text
model
first_wrong_step_acc
earliest_actionable_step_acc
intervention_needed_f1
minimal_repair_type_macro_f1
hint_level_acc
leakage_constraint_f1
json_validity
tutor_preference_vs_T2
leakage_rate_downstream
```

---

## Card 9.2 消融实验

**Codex 勾选项**

```markdown
- [ ] 数据消融
- [ ] 输入消融
- [ ] 标签消融
- [ ] 训练方法消融
```

**数据消融**

```text
StepVerify only
MathEDU only
Synthetic only
StepVerify + MathEDU
StepVerify + MathEDU + Synthetic
PRM800K pretrain + full
```

**输入消融**

```text
problem + student steps
problem + reference + student steps
problem + aligned reference/student steps
```

**标签消融**

```text
first_wrong only
first_wrong + error_category
first_wrong + earliest_actionable
first_wrong + repair_type
first_wrong + repair_type + leakage_constraint
```

**验收标准**

```text
消融必须回答：
repair_type 是否真的有用；
reference solution 是否必要；
synthetic 数据是否有帮助；
PRM800K pretrain 是否有帮助。
```

---

## Card 9.3 case study

**Codex 勾选项**

```markdown
- [ ] 自动挑选 20 个成功案例
- [ ] 自动挑选 20 个失败案例
- [ ] 自动挑选 20 个 T2 vs T3 差异案例
- [ ] 生成 reports/case_studies.md
```

**每个 case study 包含**

```text
problem
student steps
first_wrong_step
earliest_actionable_step
minimal_repair_type
T2 response
T3 response
teacher preference
analysis
```

---

# Phase 10：最终决策报告

---

## Card 10.1 Go / Pivot / Stop 报告

**目标**
给出是否继续方向 1 的客观判断。

**Codex 勾选项**

```markdown
- [ ] 汇总所有实验
- [ ] 写 reports/final_decision_report.md
- [ ] 给出 Go / Pivot / Stop 建议
```

**Go 条件**

```text
1. earliest_actionable_step 与 first_wrong_step 有足够差异；
2. minimal_repair_type 老师一致性可接受；
3. structured repair policy 比 StepVerify-style error description 改善 downstream tutor feedback；
4. stress test 显示模型不是简单 copy first_wrong_step；
5. full dataset 构建成本可控。
```

**Pivot 条件**

```text
earliest_actionable_step 差异不大，
但 minimal_repair_type 明显提升 downstream feedback。

则论文主张改为：
Minimal Repair Policy Prediction for Student Error Remediation
而不是：
Earliest Actionable Error Localization。
```

**Stop 条件**

```text
earliest_actionable_step 几乎等于 first_wrong_step；
minimal_repair_type 一致性低；
T3 不优于 T2；
teacher 认为标签无实际教学价值。
```

**需要回传 review**

```text
reports/final_decision_report.md
所有主表
所有关键 case study
Codex 对下一步方向建议
```

---

# 全流程 Review Checkpoints 汇总

Codex 必须在以下节点暂停，把结果发给你 review。

```text
Review Gate 1:
数据源摸底完成后

Review Gate 2:
schema + taxonomy + annotation guideline 完成后

Review Gate 3:
pilot 标注和一致性完成后

Review Gate 4:
问题存在性 baseline 完成后

Review Gate 5:
完整数据集构建完成后

Review Gate 6:
SFT/DPO verifier 初步训练完成后

Review Gate 7:
stress test 完成后

Review Gate 8:
downstream tutor intervention 完成后

Review Gate 9:
final decision report 完成后
```

每个 Review Gate 必须包含：

```text
1. 生成了什么文件
2. 运行了什么命令
3. 样本数量
4. 主要指标
5. 失败案例
6. Codex 不确定的问题
7. 是否建议继续
```

---

# 关键注意事项

## 1. 不要把已有工作当成不存在

写作和实验中必须承认：

```text
StepVerify 做过 first-error verification；
ProcessBench 做过 earliest error benchmark；
MathEDU 做过真实学生过程 + 教师反馈；
BEA/MRBench 做过 tutor response actionability 评价。
```

你的实验必须证明：

```text
structured minimal repair policy
>
first-error description only
```

否则方向 1 不成立。

---

## 2. 不要让 earliest_actionable_step 变成 first_wrong_step 的别名

pilot 必须统计：

```text
first_wrong_step != earliest_actionable_step 的比例
```

如果比例低，这个标签不能做主创新。

---

## 3. 不要让 repair_type 太细

第一版 repair taxonomy 控制在 8–10 类。太细会导致：

```text
老师一致性低；
模型学不稳；
评审认为标签主观。
```

---

## 4. no-error 和 self-correction 必须保留

不能只做错误样本。否则模型会学成：

```text
永远找一个错步。
```

必须有：

```text
no_error
self_corrected
insufficient_information
ambiguous
```

---

## 5. tutor response 不能泄露答案

方向 1 的教育意义很大一部分来自：

```text
更少泄露答案；
更少 over-help；
更短、更准。
```

所以 downstream 实验必须包含：

```text
non-leakage
minimality
over-help rate
repair-consistency
```

---

## 6. 按 problem_id split

所有 synthetic trace 必须保留：

```text
parent_problem_id
```

避免同题泄漏。

---

## 7. 当前手写数据只预留

schema 里可以保留：

```json
"handwrite_data": {
  "image_path": null,
  "ocr_text": null,
  "problem_recovery_level": null
}
```

但当前阶段不要读取、训练或评测它。它现在的标注主要是图像噪声框，不是 reasoning label。

---

# Phase 3.17：真实人工 Repair Taxonomy 与 Synthetic Type 有效性核查

## 目标

当前不进入训练、不训练 verifier、不扩大 silver 数据。先生成一个 24 条人工审核包，用真实老师核查：

```text
1. 6 类 coarse minimal_repair_type 是否能稳定标注；
2. 当前 synthetic_type 哪些有效、哪些要停用或重写。
```

## 输入

```text
data/audit/audit_60_blind.jsonl
data/audit/audit_60_analysis_private.jsonl
data/reports/boundary_cases_20.jsonl
configs/minimal_repair_coarse_map.yaml
configs/synthetic_type_policy.yaml
```

## 输出

```text
schemas/repair_taxonomy_check.schema.json
configs/synthetic_type_policy.yaml
docs/phase3_17_human_review_instructions.md
src/audit/build_manual_taxonomy_check_pack.py
src/audit/eval_manual_taxonomy_check.py
data/manual/phase3_17_human_pack_24.blind.jsonl
data/manual/phase3_17_human_template_24.jsonl
data/manual/phase3_17_human_template_24.csv
data/manual/phase3_17_human_labels_24.jsonl
data/manual/phase3_17_human_analysis_private.jsonl
data/manual/phase3_17_human_manifest.json
data/reports/phase3_17_human_pack_summary.json
reports/phase3_17_repair_taxonomy_check.md
reports/phase3_17_calibration_scorecard.md
reports/phase3_17_synthetic_type_policy.md
```

## 样本组成

```text
8 条 calibration boundary cases；
16 条 synthetic type-stratified core samples。
```

Core synthetic targets:

```text
sign_error x2
equation_setup_error x2
no_error_correct_trace x2
final_answer_correct_process_wrong x2
final_answer_wrong_prefix_correct x2
unit_conversion_error x1
sparse_insufficient_trace x3
hint_would_leak_answer x2
```

## 老师只标这些字段

```text
first_wrong_step
intervention_needed: true / false / uncertain
minimal_repair_coarse_6
hint_level_coarse_3
trace_validity_for_intended_type
rationale
earliest_actionable_step_optional
leakage_risk_binary
```

## 禁止事项

```text
不要给老师 expected_*；
不要给老师 synthetic_type；
不要给老师 DeepSeek labels；
不要给老师 proxy adjudicated labels；
不要把本轮人工包用于训练；
不要把本轮结果称为 gold labels。
```

## Go / No-Go

老师填完后运行：

```bash
python3 -m src.audit.eval_manual_taxonomy_check
```

Go 条件：

```text
calibration_pass_rate >= 7/8
first_wrong_step_off_by_one_agreement >= 0.80
intervention_needed_agreement >= 0.80
minimal_repair_coarse_6_agreement >= 0.70
retained_types_trace_validity >= 0.70
```

未通过则继续修 taxonomy / synthetic type policy，不进入训练或 silver scaling。
