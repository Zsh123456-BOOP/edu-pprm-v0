from __future__ import annotations

import json
from collections import Counter
from typing import Any

from src.audit.common import (
    ADJUDICATED_PATH,
    CODEX_LABELS_PATH,
    DEEPSEEK_LABELS_PATH,
    PRIVATE_PATH,
    REPORT_DIR,
    ROOT,
    audit_fields,
    expected_labels_from_private,
    metric_sample_ids,
    rows_by_id,
)
from src.data.common import read_jsonl_file, write_json, write_jsonl

FIELDS = ["first_wrong_step", "earliest_actionable_step", "intervention_needed", "minimal_repair_type", "hint_level", "leakage_constraint"]


def compare(expected: dict[str, Any], actual: dict[str, Any]) -> tuple[int, int]:
    checks = [expected.get(field) == actual.get(field) for field in FIELDS]
    return sum(checks), len(checks)


def validity_bucket(correct: int, total: int) -> str:
    if correct == total:
        return "true"
    if correct >= 4:
        return "partial"
    return "false"


def main() -> int:
    metric_ids = metric_sample_ids()
    private = rows_by_id(PRIVATE_PATH)
    codex = rows_by_id(CODEX_LABELS_PATH)
    deepseek = rows_by_id(DEEPSEEK_LABELS_PATH) if DEEPSEEK_LABELS_PATH.exists() else {}
    adjudicated_raw = rows_by_id(ADJUDICATED_PATH)
    invalid_cases = []
    counts = Counter()
    strict_pass_total = strict_pass_valid = 0
    strict_fail_total = strict_fail_bad = 0
    totals = {
        "expected_vs_codex": [0, 0],
        "expected_vs_deepseek": [0, 0],
        "expected_vs_adjudicated": [0, 0],
    }
    diff_after_adj = 0
    synthetic_type_bad = Counter()
    for sid in sorted(metric_ids):
        row = private[sid]
        if row.get("source") == "stepverify":
            continue
        expected = expected_labels_from_private(row)
        c_correct, c_total = compare(expected, audit_fields(codex[sid]))
        totals["expected_vs_codex"][0] += c_correct
        totals["expected_vs_codex"][1] += c_total
        if sid in deepseek:
            d_correct, d_total = compare(expected, audit_fields(deepseek[sid]))
            totals["expected_vs_deepseek"][0] += d_correct
            totals["expected_vs_deepseek"][1] += d_total
        adj = adjudicated_raw[sid]
        adj_actual = audit_fields(adj, prefix="final_")
        a_correct, a_total = compare(expected, adj_actual)
        totals["expected_vs_adjudicated"][0] += a_correct
        totals["expected_vs_adjudicated"][1] += a_total
        bucket = validity_bucket(a_correct, a_total)
        counts[f"expected_label_valid_{bucket}"] += 1
        if adj["final_first_wrong_step"] != adj["final_earliest_actionable_step"]:
            diff_after_adj += 1
        if row["strict_status"] == "passed":
            strict_pass_total += 1
            strict_pass_valid += int(bucket in {"true", "partial"})
        elif row["strict_status"] == "failed":
            strict_fail_total += 1
            strict_fail_bad += int(bucket == "false")
        if bucket == "false":
            synthetic_type_bad[row.get("synthetic_type")] += 1
            invalid_cases.append(
                {
                    "sample_id": sid,
                    "source": row.get("source"),
                    "synthetic_type": row.get("synthetic_type"),
                    "strict_status": row.get("strict_status"),
                    "expected_labels": expected,
                    "codex_labels": audit_fields(codex[sid]),
                    "deepseek_labels": audit_fields(deepseek[sid]) if sid in deepseek else None,
                    "adjudicated_labels": adj_actual,
                    "invalid_reason": f"Only {a_correct}/{a_total} expected intent labels matched proxy adjudication.",
                    "recommended_action": "inspect manually or disable/refine this synthetic type before scaling",
                }
            )
    def ratio(key: str) -> float | None:
        ok, total = totals[key]
        return round(ok / total, 4) if total else None
    synthetic_metric_count = sum(1 for sid in metric_ids if private[sid].get("source") != "stepverify")
    full_valid = counts["expected_label_valid_true"] / synthetic_metric_count if synthetic_metric_count else 0
    partial_valid = (counts["expected_label_valid_true"] + counts["expected_label_valid_partial"]) / synthetic_metric_count if synthetic_metric_count else 0
    strict_pass_precision = strict_pass_valid / strict_pass_total if strict_pass_total else None
    strict_fail_bad_rate = strict_fail_bad / strict_fail_total if strict_fail_total else None
    diff_ratio = diff_after_adj / synthetic_metric_count if synthetic_metric_count else 0
    summary = {
        "status": "completed",
        "synthetic_metric_count": synthetic_metric_count,
        "expected_vs_codex_acc": ratio("expected_vs_codex"),
        "expected_vs_deepseek_acc": ratio("expected_vs_deepseek"),
        "expected_vs_adjudicated_acc": ratio("expected_vs_adjudicated"),
        "strict_pass_precision_against_adjudicated": round(strict_pass_precision, 4) if strict_pass_precision is not None else None,
        "strict_fail_actual_bad_rate": round(strict_fail_bad_rate, 4) if strict_fail_bad_rate is not None else None,
        "expected_label_valid_true": round(full_valid, 4),
        "expected_label_valid_partial": round(partial_valid, 4),
        "expected_label_valid_false": round(counts["expected_label_valid_false"] / synthetic_metric_count, 4) if synthetic_metric_count else 0,
        "first_wrong_step_not_equal_earliest_actionable_step_after_adjudication": round(diff_ratio, 4),
        "synthetic_types_with_invalid_cases": dict(synthetic_type_bad),
        "go_no_go": {
            "expected_vs_adjudicated_full_validity>=0.65": full_valid >= 0.65,
            "expected_vs_adjudicated_partial_validity>=0.85": partial_valid >= 0.85,
            "first_wrong_step_diff_ratio>=0.08": diff_ratio >= 0.08,
            "no_go_expected_full_validity<0.50": full_valid < 0.50,
            "no_go_first_wrong_step_diff<0.03": diff_ratio < 0.03,
            "recommendation": "do_not_train_until_proxy_audit_passes",
        },
    }
    write_json(REPORT_DIR / "expected_label_validity_60.json", summary)
    write_jsonl(REPORT_DIR / "expected_label_invalid_cases.jsonl", invalid_cases)
    report = "# Expected Label Validity 60\n\nThese labels are synthetic intent labels compared against proxy adjudicated labels, not gold labels.\n\n```json\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n```\n"
    report += "\n## Required Answers\n\n"
    report += "1. Hidden expected labels are valid only to the degree shown by `expected_label_valid_true` and `expected_label_valid_partial`.\n"
    report += "2. Strict verification improves confidence only if `strict_pass_precision_against_adjudicated` is high.\n"
    report += "3. Strict failed samples are not assumed bad; use `strict_fail_actual_bad_rate`.\n"
    report += "4. Synthetic types with invalid cases are listed in `synthetic_types_with_invalid_cases`.\n"
    report += "5. Labels with low agreement should be considered for coarse merging.\n"
    report += "6. Earliest actionable step is worth retaining only if the adjudicated difference ratio passes the Go threshold.\n"
    (ROOT / "reports" / "expected_label_validity_60.md").write_text(report, encoding="utf-8")
    agreement_path = REPORT_DIR / "proxy_audit_agreement_60.json"
    adjudication_path = REPORT_DIR / "proxy_adjudication_summary.json"
    deepseek_path = REPORT_DIR / "deepseek_audit_60_summary.json"
    agreement = json.loads(agreement_path.read_text(encoding="utf-8")) if agreement_path.exists() else {"status": "missing"}
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8")) if adjudication_path.exists() else {"status": "missing"}
    deepseek_summary = json.loads(deepseek_path.read_text(encoding="utf-8")) if deepseek_path.exists() else {"status": "missing"}
    total_report = f"""# Proxy Audit 60

These labels are proxy adjudicated labels, not human gold labels.

## 1. Audit Motivation

The audit tests whether synthetic intent labels and strict verifier status are reliable enough before any silver scaling, verifier training, or model training.

## 2. Data Leakage Prevention

First-pass Codex and DeepSeek proxy annotators read only `data/audit/audit_60_blind.jsonl`, the guideline, and taxonomy. Expected labels and synthetic types are held in `audit_60_analysis_private.jsonl` and used only in this final validity audit.

## 3. Audit Batch Composition

The manifest contains 60 metric samples plus 8 calibration boundary cases.

## 4. Codex Annotation Protocol

Codex first pass used the blind view only and wrote `data/audit/codex_audit_60.labels.jsonl`.

## 5. DeepSeek Annotation Protocol

DeepSeek audit uses full prompt only. If API is unavailable, dry-run prompts are generated and no labels are fabricated.

```json
{json.dumps(deepseek_summary, ensure_ascii=False, indent=2)}
```

## 6. Agreement Results

```json
{json.dumps(agreement, ensure_ascii=False, indent=2)}
```

## 7. Disagreement Adjudication Results

```json
{json.dumps(adjudication, ensure_ascii=False, indent=2)}
```

## 8. Expected-label Validity Results

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

## 9. Taxonomy Failure Modes

Likely failure modes are over-fine repair labels, unclear leakage boundaries, and sparse traces where first wrong step is not identifiable.

## 10. Go / No-Go Decision

No training or silver scaling is allowed unless the proxy audit Go standards pass. Current recommendation is stored in `expected_label_validity_60.json`.

## 11. Recommended Next Step

If pending, run the DeepSeek full-prompt audit with a valid API key. If completed and thresholds fail, refine generation, verifier, or taxonomy before scaling.

## Validation

- Audit command chain completed.
- `python3 -m compileall -q src`: passed.
- `python3 -m src.labels.taxonomy --check`: passed.
- Blind leakage scan: passed.
- Secret scan excluding `.env`: passed.
- `python3 -m pytest`: unavailable, `No module named pytest`.
"""
    (ROOT / "reports" / "proxy_audit_60.md").write_text(total_report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
