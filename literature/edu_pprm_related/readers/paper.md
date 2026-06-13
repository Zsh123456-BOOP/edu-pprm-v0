# Edu-PPRM Related Literature Focused Reader

This reader uses source-grounded bilingual notes to support one decision:

```text
Edu-PPRM-v0 should focus on first_wrong_step -> coarse minimal_repair_type,
with hint/leakage as secondary diagnostics and earliest_actionable_step as
boundary-only.
```

## Reader Index

- S001: Let's Verify Step by Step
- S002: Math-Shepherd
- S003: ProcessBench
- S004: Stepwise Verification and Remediation
- S005: MathDial
- S006: MRBench
- S007: KMP-Bench
- S008: Toward In-Context Teaching

## S001. Process Supervision Is Valuable, But Not Pedagogical Repair

**Source:** `literature/edu_pprm_related/text/lets_verify_step_by_step_iclr2024.txt`, page 1 abstract and page 2 contributions.

**Original:** The paper compares outcome supervision with process supervision and releases PRM800K, a large step-level feedback dataset for mathematical reasoning.

**中文:** 该文证明过程监督比只看最终答案更能训练可靠的奖励模型，并发布了 PRM800K 这类大规模 step-level feedback 数据。

**Edu-PPRM reading:** This directly supports using first-error / step-level labels as a foundation. However, PRM800K is still mainly correctness/reward supervision. It does not define the teacher's minimal repair action, hint level, or answer-leakage constraint.

## S002. Automatic Process Labels Scale, But They Are Still Correctness Labels

**Source:** `literature/edu_pprm_related/text/math_shepherd_acl2024.txt`, page 1 abstract and introduction.

**Original:** Math-Shepherd automatically constructs process-wise supervision by estimating whether intermediate steps can lead to correct final answers.

**中文:** Math-Shepherd 通过自动估计中间步骤是否能导向正确答案，构造过程监督数据。

**Edu-PPRM reading:** This validates synthetic or automatic step supervision as a serious direction. It also warns us not to confuse automatic step quality with pedagogical repair labels: a step can be mathematically bad, but the tutor action still needs a separate policy.

## S003. First-Error Detection Is Now A Benchmark, Not A Complete Tutoring Task

**Source:** `literature/edu_pprm_related/text/processbench_acl2025.txt`, page 1 abstract and introduction.

**Original:** ProcessBench asks models to identify the earliest erroneous step or conclude that all steps are correct.

**中文:** ProcessBench 评测模型是否能找到最早错误步骤，或者判断所有步骤正确。

**Edu-PPRM reading:** This is an important external benchmark for first_wrong_step. It also makes clear that simply finding the first wrong step is becoming a baseline task. Edu-PPRM needs to add value after localization: what minimal pedagogical repair should follow?

## S004. Closest Prior: Verify Then Generate Tutor Feedback

**Source:** `literature/edu_pprm_related/text/stepwise_verification_remediation_emnlp2024.txt`, page 1 abstract and introduction.

**Original:** The paper collects stepwise student reasoning chains with first-error annotations and shows that verification-grounded generation improves targeted tutor responses.

**中文:** 该文收集带第一处错误标注的学生推理链，并证明先验证再生成反馈能提升 tutor response 的针对性。

**Edu-PPRM reading:** This is the closest related work. It reduces the novelty of a generic "verify then tutor" claim. Edu-PPRM's defensible gap is narrower: structured repair-policy labels before generation, especially a stable coarse minimal_repair_type taxonomy.

## S005. Math Tutoring Needs Scaffolding And Non-Leakage

**Source:** `literature/edu_pprm_related/text/mathdial_findings_emnlp2023.txt`, page 1 abstract and introduction.

**Original:** MathDial shows that models can solve math problems while giving poor tutoring feedback, including incorrect feedback and revealing solutions too early.

**中文:** MathDial 表明，会解数学题并不等于会教学；模型可能给出错误反馈，或过早泄露答案。

**Edu-PPRM reading:** This strongly supports keeping hint/leakage diagnostics. It also supports the idea that a tutoring dataset should separate "what is wrong" from "how to intervene without over-helping."

## S006. Pedagogical Evaluation Already Includes Mistake Location And Answer Revealing

**Source:** `literature/edu_pprm_related/text/mrbench_naacl2025.txt`, page 1 abstract and introduction.

**Original:** MRBench proposes evaluation dimensions including mistake identification, mistake location, revealing the answer, guidance, actionability, and coherence.

**中文:** MRBench 的评价维度包括错误识别、错误定位、是否泄露答案、引导性、可执行性和连贯性。

**Edu-PPRM reading:** This supports the label family Edu-PPRM is converging toward. It also suggests that leakage should be reported as an auxiliary diagnostic rather than forced into a single over-specific repair label.

## S007. Solver Ability And Tutor Ability Are Different

**Source:** `literature/edu_pprm_related/text/kmp_bench_aaai2026.txt`, page 1 abstract and introduction.

**Original:** KMP-Bench argues that mathematical problem-solving proficiency does not equal skilled teaching and evaluates pedagogical tutoring abilities separately.

**中文:** KMP-Bench 明确指出，数学解题能力不等于教学能力，需要单独评价 pedagogical tutoring ability。

**Edu-PPRM reading:** This is high-level support for the entire project framing. Edu-PPRM should not claim merely better solving; it should claim structured supervision for better educational intervention policies.

## S008. Teaching Must Adapt To Misconceptions

**Source:** `literature/edu_pprm_related/text/toward_in_context_teaching_acl2024.txt`, page 1 abstract and introduction.

**Original:** This work studies adaptive teaching by inferring student misconceptions and selecting informative examples.

**中文:** 该文研究如何推断学生误解，并据此选择更有信息量的教学样例。

**Edu-PPRM reading:** This supports the educational motivation for repair categories such as quantity_or_condition and equation_or_formula. The current project should keep "student misconception / error type -> intervention type" as the core bridge.

## Bottom Line

Edu-PPRM has research value if it is framed as:

```text
structured pedagogical repair supervision for math reasoning traces
```

The strongest current version is not:

```text
earliest_actionable_step as a new core label
```

The literature suggests a clear gap between PRM-style correctness supervision
and tutor-feedback generation. Edu-PPRM should occupy that gap by producing
validated, compact labels that tell a tutor what kind of minimal intervention is
appropriate after locating a student error.
