from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.audit.common import (
    CODEX_LABELS_PATH,
    DEEPSEEK_LABELS_PATH,
    REPORT_DIR,
    ROOT,
    agreement_rate,
    load_coarse_map,
    metric_sample_ids,
    off_by_one_rate,
    rows_by_id,
)
from src.data.common import write_json, write_jsonl

FIELDS = [
    "first_wrong_step",
    "earliest_actionable_step",
    "intervention_needed",
    "minimal_repair_type",
    "hint_level",
    "leakage_constraint",
]


def main() -> int:
    if not DEEPSEEK_LABELS_PATH.exists():
        reason = "DeepSeek audit labels missing; run src.audit.run_deepseek_audit with DEEPSEEK_API_KEY before agreement metrics."
        write_json(REPORT_DIR / "proxy_audit_agreement_60.json", {"status": "pending", "reason": reason})
        (ROOT / "reports" / "proxy_audit_agreement_60.md").write_text(f"# Proxy Audit Agreement 60\n\nStatus: pending\n\n{reason}\n", encoding="utf-8")
        write_jsonl(REPORT_DIR / "proxy_audit_disagreements.jsonl", [])
        print(json.dumps({"status": "pending", "reason": reason}, indent=2))
        return 0
    metric_ids = metric_sample_ids()
    codex = rows_by_id(CODEX_LABELS_PATH)
    deepseek = rows_by_id(DEEPSEEK_LABELS_PATH)
    common_ids = sorted(metric_ids & set(codex) & set(deepseek))
    coarse = load_coarse_map()

    field_pairs: dict[str, list[tuple[Any, Any]]] = defaultdict(list)
    disagreements: list[dict[str, Any]] = []
    confidence_gaps = []
    for sid in common_ids:
        c = codex[sid]
        d = deepseek[sid]
        confidence_gaps.append(abs(float(c["confidence"]) - float(d["confidence"])))
        for field in FIELDS:
            cv = c[field]
            dv = d[field]
            field_pairs[field].append((cv, dv))
            if cv != dv:
                disagreements.append(
                    {
                        "sample_id": sid,
                        "field_name": field,
                        "codex_value": cv,
                        "deepseek_value": dv,
                        "codex_confidence": c["confidence"],
                        "deepseek_confidence": d["confidence"],
                        "codex_rationale": c["rationale"],
                        "deepseek_rationale": d["rationale"],
                    }
                )
    coarse_pairs = [
        (coarse.get(codex[sid]["minimal_repair_type"]), coarse.get(deepseek[sid]["minimal_repair_type"]))
        for sid in common_ids
    ]
    summary = {
        "status": "completed",
        "metric_sample_count": len(metric_ids),
        "compared_count": len(common_ids),
        "first_wrong_step_exact_agreement": agreement_rate(field_pairs["first_wrong_step"]),
        "first_wrong_step_off_by_one_agreement": off_by_one_rate(field_pairs["first_wrong_step"]),
        "earliest_actionable_step_exact_agreement": agreement_rate(field_pairs["earliest_actionable_step"]),
        "intervention_needed_agreement": agreement_rate(field_pairs["intervention_needed"]),
        "minimal_repair_type_exact_agreement": agreement_rate(field_pairs["minimal_repair_type"]),
        "minimal_repair_type_coarse_agreement": agreement_rate(coarse_pairs),
        "hint_level_agreement": agreement_rate(field_pairs["hint_level"]),
        "leakage_constraint_agreement": agreement_rate(field_pairs["leakage_constraint"]),
        "mean_confidence_gap": round(sum(confidence_gaps) / len(confidence_gaps), 4) if confidence_gaps else None,
        "disagreement_count": len(disagreements),
        "note": "If 11-class agreement is low but 6-class agreement is much higher, this suggests the taxonomy may be too fine-grained rather than the task being invalid.",
    }
    write_json(REPORT_DIR / "proxy_audit_agreement_60.json", summary)
    write_jsonl(REPORT_DIR / "proxy_audit_disagreements.jsonl", disagreements)
    report = (
        "# Proxy Audit Agreement 60\n\n"
        "These labels are proxy labels, not human gold labels. Metrics compare `codex_manual_proxy` against `deepseek_proxy`; "
        "the `heuristic_proxy` baseline is excluded from the main agreement metrics.\n\n```json\n"
        + json.dumps(summary, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    (ROOT / "reports" / "proxy_audit_agreement_60.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
