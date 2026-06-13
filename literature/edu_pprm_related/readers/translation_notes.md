# Translation And Reading Notes

This is a focused multi-paper reading artifact created to answer a project
decision question:

```text
Does Edu-PPRM-v0 still have research value after narrowing to
first_wrong_step -> coarse minimal_repair_type?
```

It is not a full paragraph-by-paragraph bilingual translation of every paper.
The PDFs and extracted text are stored locally, and the reader preserves source
anchors for the passages used in the decision.

## Extraction Notes

- All PDFs had extractable text layers.
- Figures were not cropped because this review is decision-oriented and did not
  require figure-level visual inspection.
- ACL/AAAI/arXiv PDFs were downloaded from open official sources.

## Terminology Ledger

| Canonical term | Chinese rendering | Notes |
|---|---|---|
| process supervision | 过程监督 | Step-level supervision/reward for intermediate reasoning. |
| process reward model (PRM) | 过程奖励模型 | Scores intermediate reasoning steps. |
| first wrong step | 第一处错误步骤 | First mathematically wrong step in the student trace. |
| minimal repair type | 最小修复类型 | Edu-PPRM target label: the smallest pedagogical intervention category. |
| scaffolding | 支架式引导 | Tutor feedback that guides without directly revealing the full solution. |
| leakage / answer revealing | 答案泄露 | Feedback gives the answer or next step too directly. |
| remediation | 错误补救/修复 | Tutor response that addresses a student mistake. |
| misconception | 误解/错误概念 | Student's underlying wrong belief or interpretation. |
