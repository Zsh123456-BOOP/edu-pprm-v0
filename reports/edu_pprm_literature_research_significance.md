# Edu-PPRM-v0 Literature Review: Research Significance Check

## Short Answer

有研究意义，但必须保持当前收缩后的版本。

最稳的研究 idea 不是：

```text
earliest_actionable_step
```

而是：

```text
first_wrong_step -> coarse minimal_repair_type
```

也就是：先定位学生推理中的第一处错误，再判断老师应该采用哪一类最小教学修复动作。

## Why This Is Still Meaningful

现有高水平工作大致分成两条线。

第一条是 PRM / process supervision。`Let's Verify Step by Step`、`Math-Shepherd`、`ProcessBench` 都说明 step-level reasoning supervision 是重要问题，而且 first-error detection 已经成为主流 benchmark 能力。但这些工作主要回答：

```text
这一步对不对？
哪一步最早错？
这个 step 值多少 reward？
```

它们通常不回答：

```text
老师下一句应该怎么最小干预？
应该让学生重算、重读题、改方程、检查代入，还是先澄清信息？
提示到什么程度才不泄露答案？
```

第二条是 AI tutor / remediation。`MathDial`、`Stepwise Verification and Remediation`、`MRBench`、`KMP-Bench` 都说明 LLM 会解题不等于会教学，常见问题包括错误定位不准、反馈不针对、直接泄露答案、给出不合适的支架式提示。这些工作证明了教育反馈很重要，但多数直接评估或生成 tutor response，没有把中间的 repair policy 做成紧凑、可训练、可审计的数据标签。

所以 Edu-PPRM 的空白是：

```text
把 PRM 的 step-level localization 和 AI tutor 的 pedagogical feedback 接起来。
```

## Literature Map

| Paper | Venue / status | What it proves | Relation to Edu-PPRM |
|---|---|---|---|
| Let's Verify Step by Step | ICLR 2024 | Process supervision improves reward models and releases PRM800K | Supports first-error/step-level foundation, but lacks repair policy labels |
| Math-Shepherd | ACL 2024 Long | Automatic process supervision can scale | Supports synthetic labels, but labels remain correctness/reward oriented |
| ProcessBench | ACL 2025 Long | Earliest erroneous step is now a benchmark task | Makes first_wrong_step a baseline, not the whole novelty |
| Toward In-Context Teaching | ACL 2024 Long | Teaching should adapt to misconceptions | Supports student-error-type-aware intervention |
| KMP-Bench | AAAI 2026 | Solver ability differs from tutor ability | Supports educational framing |
| Stepwise Verification and Remediation | EMNLP 2024 Main | Verification-grounded generation improves tutor responses | Closest prior; Edu-PPRM must differentiate through structured repair labels |
| MathDial | Findings EMNLP 2023 | Tutor feedback needs scaffolding and non-leakage | Supports hint/leakage diagnostics |
| MRBench | NAACL 2025 Long | Tutor evaluation needs dimensions like mistake location, answer revealing, actionability | Supports current label family, but suggests leakage should be auxiliary |
| Process-vs-outcome feedback | arXiv 2022 | Process feedback reduces reasoning trace errors | Process supervision precursor |

## Novelty Boundary

不能这样写：

```text
We propose the first system for verifying student reasoning and generating feedback.
```

这会撞上 `Stepwise Verification and Remediation` 和 MathDial 系列。

应该这样写：

```text
We study a compact pedagogical repair-label layer between first-error localization
and tutor response generation.
```

更具体一点：

```text
Given a math problem and a student reasoning trace, Edu-PPRM labels the first wrong
step and maps it to a coarse minimal repair type, with optional hint and leakage
diagnostics. This converts raw error localization into a controllable tutor policy.
```

## What The Literature Suggests We Should Drop Or De-emphasize

`earliest_actionable_step` 暂时不要作为核心贡献。现有论文里也更自然地围绕 mistake location、verification、remediation、answer revealing、actionability 展开；Phase 3.17 也没有证明 earliest_actionable 和 first_wrong_step 能稳定分开。

`leakage_constraint` 不要做主 Go 指标。文献支持“不要泄露答案”很重要，但更像 tutor response 安全性/诊断维度，而不是和 repair type 同级的主标签。

细粒度 11 类 `minimal_repair_type` 不适合当前阶段主打。MRBench/KMP-Bench 这类工作也强调多维 pedagogical evaluation，但不意味着每个维度一开始就要切得很细。当前应主打 6 类 coarse taxonomy。

## Recommended Next Experiment

下一步仍然是 Phase 3.18 synthetic v2 小规模重写，不训练、不扩 silver。

目标：

```text
验证 6 类 coarse repair taxonomy 能否从 24 条人工核查扩到 100-150 条更干净 synthetic traces。
```

建议设计：

- 保留或重写 Phase 3.17 支持的 synthetic types；
- 停用 Phase 3.17 和 proxy audit 中反复无效的类型；
- 每条 synthetic trace 必须让错误在 student_trace 中可见；
- expected labels 继续叫 synthetic intent labels，不叫 gold；
- 用 DeepSeek/proxy 只做自动对照，再抽 20 条人审 spot-check。

## Research Claim If Phase 3.18 Passes

可以主张：

```text
A compact 6-class pedagogical repair taxonomy is feasible for math reasoning
traces and can bridge first-error detection with controlled tutor feedback.
```

暂时不要主张：

```text
We have a full educational PRM dataset ready for verifier training.
```

也不要主张：

```text
earliest_actionable_step is a stable new supervision signal.
```

## Local Artifacts

- PDFs: `literature/edu_pprm_related/pdfs/`
- Extracted text: `literature/edu_pprm_related/text/`
- Focused reader: `literature/edu_pprm_related/readers/paper.md`
- Download manifest: `literature/edu_pprm_related/metadata/download_manifest.json`

## Decision

当前 idea 没走偏，反而更清楚了：

```text
Edu-PPRM 不应该和 PRM800K / ProcessBench 抢“找错步骤”；
它应该做“找错步骤之后，老师应该怎么最小修复”的结构化监督。
```

这在已有高水平论文之间有明确夹缝：PRM 工作不解决教学 repair policy，AI tutor 工作需要这种中间结构但通常直接生成反馈。因此研究意义成立，但必须先用 synthetic v2 和小规模人审继续证明数据质量。
