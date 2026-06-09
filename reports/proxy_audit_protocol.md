# Proxy Human Audit Protocol

These labels are proxy adjudicated labels, not human gold labels.

## Motivation

The DeepSeek synthetic 240 run showed that synthetic expected labels are not reliable enough to train from directly. Phase 3.11-3.16 therefore audits whether Codex and DeepSeek-pro can independently identify stable pedagogical labels from blind traces.

## Leakage Prevention

First-pass annotators may read only `data/audit/audit_60_blind.jsonl`, `docs/annotation_guideline.md`, and `configs/label_taxonomy.yaml`.

They must not read `data/audit/audit_60_analysis_private.jsonl`, `synthetic_metadata.expected_*`, `synthetic_type`, `injected_error_type`, or strict verifier status.

The blind exporter fails if leakage terms appear in blind rows.

## Audit Batch

The metric batch has 60 samples: 12 strict-pass match, 18 strict-pass mismatch, 15 strict-failed hard types, 5 strict-failed random types, and 10 StepVerify raw samples. Eight boundary cases are calibration only.

## Annotation Order

Annotators judge problem/trace completeness, first wrong step, intervention need, earliest actionable step, repair type, hint level, leakage constraint, confidence, and rationale.

## Go / No-Go

No model training, verifier training, or silver scaling may start unless proxy audit metrics meet the Go thresholds recorded in the task card.
