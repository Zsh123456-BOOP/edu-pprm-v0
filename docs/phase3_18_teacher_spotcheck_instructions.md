# Phase 3.18 Teacher Spot-Check Instructions

请老师只看这三个文件：

```text
data/manual/phase3_18_teacher_spotcheck_24.blind.jsonl
data/manual/phase3_18_teacher_spotcheck_24.template.csv
data/manual/phase3_18_teacher_spotcheck_24.template.jsonl
```

建议直接填写 CSV：

```text
data/manual/phase3_18_teacher_spotcheck_24.template.csv
```

不要看 private 文件：

```text
data/manual/phase3_18_teacher_spotcheck_24.private.jsonl
```

private 文件里有 synthetic_type、hidden expected labels、DeepSeek labels，只能用于最后评估。

## 填写字段

每行是一道题和一个学生解题过程。老师需要填：

- `reviewer_id`: 老师代号，例如 `teacher_01`
- `first_wrong_step`: 第一处数学错误步骤编号；如果没有明确错误，填空
- `intervention_needed`: `true` / `false` / `uncertain`
- `minimal_repair_coarse_6`: 六选一
- `hint_level_coarse_3`: 三选一
- `trace_validity_for_intended_type`: 四选一
- `rationale`: 简短理由
- `earliest_actionable_step_optional`: 可选；不确定可空
- `leakage_risk_binary`: `yes` / `no` / 空

## minimal_repair_coarse_6 六类

```text
no_intervention
local_computation
quantity_or_condition
equation_or_formula
verification_check
insufficient_or_clarify
```

含义：

- `no_intervention`: 没有需要老师介入的错误，或学生已自我修正
- `local_computation`: 局部算式算错
- `quantity_or_condition`: 读错题目条件、给定量、最终答案与题意/前缀不一致
- `equation_or_formula`: 方程、公式、运算关系、单位换算设置错
- `verification_check`: 需要代回、检查推理或核对已得结果
- `insufficient_or_clarify`: 信息太少，无法安全判断，或应先问澄清问题

## hint_level_coarse_3 三类

```text
none
nudge
targeted_or_scaffolded
```

含义：

- `none`: 不需要提示
- `nudge`: 轻微提醒，不直接指出完整做法
- `targeted_or_scaffolded`: 有针对性的支架式提示

## trace_validity_for_intended_type 四类

```text
as_intended
visible_but_other_error
no_visible_error
insufficient_trace
```

含义：

- `as_intended`: 学生步骤里确实有清楚、可判断的目标错误
- `visible_but_other_error`: 有错误，但不像预期那类错误
- `no_visible_error`: 看不出错误
- `insufficient_trace`: 步骤太少，无法判断

## 判断原则

- 不要因为知道最终答案就直接给学生完整解法。
- `first_wrong_step` 是数学上第一处错误。
- 如果学生先错后自我修正，`intervention_needed=false`。
- 如果只有最终答案或过程太少，优先 `uncertain + insufficient_or_clarify`。
- 不确定时不要硬判，写 `uncertain` 并在 `rationale` 说明。
