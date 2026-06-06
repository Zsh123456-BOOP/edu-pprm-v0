# Phase 3 Pilot Source Policy

This policy is for planning Phase 3 only. It does not build a pilot pool.

## Decision Inputs

- Review Gate 1 found that existing sources do not directly provide
  `earliest_actionable_step`, `minimal_repair_type`, `hint_level`, or
  `leakage_constraint`.
- StepVerify has direct first-error fields and is the core source for
  first-error baseline alignment.
- GSM8K and MATH are problem banks for synthetic student error traces.
- PRM800K is generic PRM supervision and can support baseline/pretrain work,
  but it is not a pedagogical repair label source.
- ProcessBench is external eval only and must not enter pilot training or gold
  annotation pools.
- MathEDU full audit scanned 28,336 local raw rows and found 0% recoverable
  question/problem text fields.

## Phase 3 Default Mix

| Source | Default Role | Approx Count | Phase 3 Policy |
| --- | --- | ---: | --- |
| StepVerify | Core first-error source | 120 | Include as core annotation source. |
| GSM8K synthetic | Synthetic student-error problem bank | 80 | Include after synthetic trace generation and leakage checks. |
| MATH synthetic | Harder synthetic student-error problem bank | 40 | Include after synthetic trace generation and leakage checks. |
| MathEDU | Real-student auxiliary data | 0 | Exclude from core pilot for now; keep for later enhancement. |
| PRM800K | Baseline/pretrain only | 0 | Exclude from pilot gold labels. |
| ProcessBench | External eval only | 0 | Exclude from pilot and train/interim paths. |

## MathEDU Policy

MathEDU does not enter the Phase 3 pilot candidate pool under the current audit.

Reason:

- `problem_text` direct ratio: 0%.
- recoverable `problem/question/prompt/original_question` ratio: 0%.
- `student_solution_raw` ratio: 100%.
- teacher feedback/review ratio: 24.68%.
- error type/reason ratio: 2.49%.
- step-level pilot candidate count: 0.
- missing question but matchable row ID count: 28,336.

Use MathEDU later only if a reliable question recovery table is found or
constructed outside the main pilot workflow.

## Guardrails

- Do not include current handwritten image data.
- Do not include ProcessBench in train, interim, pilot, or gold data.
- Do not treat PRM800K step correctness as pedagogical repair labels.
- Do not infer MathEDU problem text from student process or teacher feedback.
- Do not build the pilot pool before Review Gate 2 approval.
