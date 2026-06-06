# Edu-PPRM Annotation Guideline

## Core Distinction

- `first_wrong_step` is the mathematically first incorrect step in the student trace.
- `earliest_actionable_step` is the earliest point where a tutor should intervene.
- They may be the same, but they can differ.
- Do not mechanically set `earliest_actionable_step = first_wrong_step`.
- If the evidence is not enough, use `intervention_needed = uncertain` and `minimal_repair_type = insufficient_information`.
- If the student has already self-corrected, `intervention_needed` can be `false` even when a prior wrong step exists.

## Annotation Order

1. Read the problem and student steps exactly as given.
2. Identify the first mathematically wrong step, if one is visible.
3. Decide whether a tutor should intervene at the current point.
4. Choose the earliest actionable step independently from first wrong step.
5. Choose the minimal repair type that asks for the smallest useful student action.
6. Choose hint level and leakage constraint to avoid giving away the solution.
7. If the problem, trace, or intent is missing or ambiguous, mark uncertainty instead of guessing.

## Boundary Cases

### 1. 第一处错误只是表述问题，不值得介入

Problem sketch: Find the number of apples after buying 3 more from 5.

Student steps:
- 5+3 means I add the new apples.
- So there are 8 apples.
- Answer: 8

first_wrong_step: 1
earliest_actionable_step: None
intervention_needed: False
minimal_repair_type: no_intervention_needed
hint_level: none
leakage_constraint: can_point_to_local_step_only
reason: The wording is informal but the mathematical action and result are correct; intervention would distract.

### 2. 学生先错后自我修正

Problem sketch: Compute 14 x 6.

Student steps:
- 14 x 6 = 74.
- Wait, 10 x 6 = 60 and 4 x 6 = 24.
- So 14 x 6 = 84.

first_wrong_step: 1
earliest_actionable_step: None
intervention_needed: False
minimal_repair_type: no_intervention_needed
hint_level: none
leakage_constraint: do_not_reveal_final_answer
reason: A mathematical error appears, but the student repairs it before tutor intervention is needed.

### 3. 跳步但数学正确

Problem sketch: Solve 3x + 2 = 11.

Student steps:
- 3x + 2 = 11.
- x = 3.

first_wrong_step: None
earliest_actionable_step: None
intervention_needed: False
minimal_repair_type: no_intervention_needed
hint_level: none
leakage_constraint: can_point_to_local_step_only
reason: The student skipped algebra details but the inference is valid and short enough for this problem.

### 4. 不同于 reference 的正确解法

Problem sketch: Find 25% of 80.

Student steps:
- 10% of 80 is 8.
- 20% is 16 and 5% is 4.
- 25% is 20.

first_wrong_step: None
earliest_actionable_step: None
intervention_needed: False
minimal_repair_type: no_intervention_needed
hint_level: none
leakage_constraint: do_not_reveal_final_answer
reason: The method differs from multiplying by 0.25 but is mathematically correct.

### 5. 题目理解错误

Problem sketch: A bike has 2 wheels. Tom has 3 times as many wheels as Ana, who has 4 bikes. How many bikes could Tom have after one tricycle is included?

Student steps:
- Ana has 4 bikes, so Tom has 3 x 4 = 12 bikes.
- One tricycle is included, so 12 - 1 = 11 bikes.

first_wrong_step: 1
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_to_reinterpret_given_quantity
hint_level: medium
leakage_constraint: do_not_solve_next_step
reason: The first step treats wheels as bikes; this is immediately actionable because later work inherits the misread quantity.

### 6. 局部计算错误

Problem sketch: A shirt costs 18 dollars and a hat costs 7 dollars. Buy 3 shirts and 2 hats.

Student steps:
- 3 shirts cost 18 x 3 = 54.
- 2 hats cost 7 x 2 = 12.
- Total is 54 + 12 = 68.

first_wrong_step: 2
earliest_actionable_step: 2
intervention_needed: True
minimal_repair_type: ask_to_recompute_local_expression
hint_level: low
leakage_constraint: do_not_reveal_final_answer
reason: The setup is correct; the earliest useful action is to ask for recomputation of the local sum.

### 7. 最终答案正确但过程错误

Problem sketch: Find 6 x 7.

Student steps:
- 6 x 7 = 40.
- But I remember the answer is 42.
- Answer: 42

first_wrong_step: 1
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_to_recompute_local_expression
hint_level: medium
leakage_constraint: do_not_solve_next_step
reason: The final answer is correct by recall, but the process contains an actionable computation error.

### 8. 最终答案错误但前缀正确

Problem sketch: Solve x/4 = 9.

Student steps:
- x/4 = 9.
- Multiply both sides by 4.
- x = 36.
- Answer: 34

first_wrong_step: 4
earliest_actionable_step: 4
intervention_needed: True
minimal_repair_type: ask_to_compare_with_problem_condition
hint_level: low
leakage_constraint: do_not_reveal_final_answer
reason: The reasoning prefix is correct; the final transcription conflicts with the derived value.

### 9. 错误位置不唯一

Problem sketch: Find the average of 4, 8, and 12.

Student steps:
- There are 2 numbers.
- 4 + 8 + 12 = 24.
- 24 / 2 = 12.

first_wrong_step: 1
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_to_compare_with_problem_condition
hint_level: medium
leakage_constraint: can_name_error_type
reason: The division step is also wrong downstream, but the earliest actionable issue is counting the given numbers.

### 10. 步骤太少无法判断

Problem sketch: Solve 2x + 5 = 17.

Student steps:
- x = 8

first_wrong_step: None
earliest_actionable_step: None
intervention_needed: uncertain
minimal_repair_type: insufficient_information
hint_level: medium
leakage_constraint: can_point_to_local_step_only
reason: The final value is wrong, but the missing work prevents a safe first-error or minimal-repair diagnosis.

### 11. 抄错题目条件

Problem sketch: A rectangle has length 12 and width 5. Find area.

Student steps:
- Length is 10 and width is 5.
- Area = 10 x 5 = 50.

first_wrong_step: 1
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_to_compare_with_problem_condition
hint_level: low
leakage_constraint: do_not_solve_next_step
reason: The student copied a condition incorrectly; repairing later multiplication would miss the source.

### 12. 正确公式但代入错

Problem sketch: Area of triangle with base 10 and height 6.

Student steps:
- A = 1/2 bh.
- A = 1/2 x 10 x 8.
- A = 40.

first_wrong_step: 2
earliest_actionable_step: 2
intervention_needed: True
minimal_repair_type: ask_to_reinterpret_given_quantity
hint_level: low
leakage_constraint: do_not_solve_next_step
reason: Formula choice is correct; the actionable repair is checking which given number is the height.

### 13. 错误公式但计算正确

Problem sketch: Circumference of circle with radius 3.

Student steps:
- Use area formula pi r^2.
- pi x 3^2 = 9pi.

first_wrong_step: 1
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_to_check_operation_or_formula
hint_level: medium
leakage_constraint: can_name_error_type
reason: The arithmetic follows the chosen formula, but the formula does not answer the requested quantity.

### 14. 多个错误同时出现

Problem sketch: Convert 2.5 hours to minutes, then add 15 minutes.

Student steps:
- 2.5 hours = 25 minutes, and plus 15 is 35 minutes.

first_wrong_step: 1
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_to_check_unit_conversion
hint_level: medium
leakage_constraint: can_show_micro_example
reason: The unit conversion and addition are both wrong in one step; the unit conversion is the minimal upstream repair.

### 15. 需要先问澄清问题

Problem sketch: Student writes a solution using n without defining what n counts.

Student steps:
- Let n be it.
- Then 3n + 2 = 17.

first_wrong_step: None
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_clarifying_question
hint_level: medium
leakage_constraint: can_point_to_local_step_only
reason: The notation is too ambiguous to judge correctness; the earliest teacher action is clarification, not error correction.

### 16. 提示容易泄露答案

Problem sketch: What is the one missing number in 4 + __ = 9?

Student steps:
- Maybe the missing number is 4.

first_wrong_step: 1
earliest_actionable_step: 1
intervention_needed: True
minimal_repair_type: ask_to_substitute_back
hint_level: low
leakage_constraint: do_not_reveal_final_answer
reason: A direct correction reveals the answer; ask the student to substitute their guess back instead.

### 17. no-error 样本

Problem sketch: Compute 9 + 6.

Student steps:
- 9 + 6 = 15.
- Answer: 15

first_wrong_step: None
earliest_actionable_step: None
intervention_needed: False
minimal_repair_type: no_intervention_needed
hint_level: none
leakage_constraint: do_not_reveal_final_answer
reason: The trace is correct; no repair label should be forced.

### 18. reference solution 不唯一

Problem sketch: Find a number that satisfies x^2 = 4.

Student steps:
- x = -2.
- Because (-2)^2 = 4.

first_wrong_step: None
earliest_actionable_step: None
intervention_needed: False
minimal_repair_type: no_intervention_needed
hint_level: none
leakage_constraint: can_point_to_local_step_only
reason: A reference may list x=2, but x=-2 is also valid unless the problem asks for positive x.

### 19. 题目本身有歧义

Problem sketch: Find the next number: 2, 4, 8, ...

Student steps:
- The next number is 10 because the differences are 2 then 4, so maybe add 2 next.

first_wrong_step: None
earliest_actionable_step: None
intervention_needed: uncertain
minimal_repair_type: ask_clarifying_question
hint_level: medium
leakage_constraint: do_not_reveal_final_answer
reason: Multiple sequence rules may fit; the teacher should clarify the intended pattern before marking an error.

### 20. 老师可能分歧的样本

Problem sketch: Estimate 19 x 21 mentally.

Student steps:
- 19 x 21 is about 20 x 20.
- So about 400.

first_wrong_step: None
earliest_actionable_step: None
intervention_needed: uncertain
minimal_repair_type: insufficient_information
hint_level: low
leakage_constraint: can_point_to_local_step_only
reason: If the task expects estimation, this is fine; if exact computation is required, more work is needed. Annotators may disagree without task intent.
