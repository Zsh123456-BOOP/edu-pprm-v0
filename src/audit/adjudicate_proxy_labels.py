from __future__ import annotations

import json
from collections import Counter

from src.audit.common import (
    ADJUDICATED_PATH,
    BLIND_PATH,
    CODEX_LABELS_PATH,
    DEEPSEEK_LABELS_PATH,
    REPORT_DIR,
    ROOT,
    metric_sample_ids,
    rows_by_id,
)
from src.data.common import write_json, write_jsonl


def choose_label(codex: dict, deepseek: dict | None) -> tuple[dict, str, str]:
    if deepseek is None:
        return codex, "codex_preferred", "DeepSeek proxy label unavailable; Codex first-pass proxy label retained."
    if codex["minimal_repair_type"] == deepseek["minimal_repair_type"] and codex["first_wrong_step"] == deepseek["first_wrong_step"]:
        chosen = dict(codex if codex["confidence"] >= deepseek["confidence"] else deepseek)
        return chosen, "hybrid", "Both proxy annotators agree on the main error location and repair type; higher-confidence wording was retained."
    if codex["confidence"] >= deepseek["confidence"] + 0.1:
        return codex, "codex_preferred", "Codex proxy label had materially higher confidence and a more conservative rationale."
    if deepseek["confidence"] >= codex["confidence"] + 0.1:
        return deepseek, "deepseek_preferred", "DeepSeek proxy label had materially higher confidence."
    return codex, "uncertain", "Proxy annotators disagreed without a clear confidence advantage; Codex conservative label retained pending human review."


def main() -> int:
    metric_ids = sorted(metric_sample_ids())
    codex = rows_by_id(CODEX_LABELS_PATH)
    deepseek = rows_by_id(DEEPSEEK_LABELS_PATH) if DEEPSEEK_LABELS_PATH.exists() else {}
    rows = []
    for sid in metric_ids:
        chosen, decision, rationale = choose_label(codex[sid], deepseek.get(sid))
        rows.append(
            {
                "sample_id": sid,
                "final_first_wrong_step": chosen["first_wrong_step"],
                "final_earliest_actionable_step": chosen["earliest_actionable_step"],
                "final_intervention_needed": chosen["intervention_needed"],
                "final_minimal_repair_type": chosen["minimal_repair_type"],
                "final_hint_level": chosen["hint_level"],
                "final_leakage_constraint": chosen["leakage_constraint"],
                "adjudication_decision": decision,
                "adjudication_rationale": rationale,
            }
        )
    write_jsonl(ADJUDICATED_PATH, rows)
    summary = {
        "status": "completed_with_pending_deepseek" if not deepseek else "completed",
        "count": len(rows),
        "decision_distribution": dict(Counter(row["adjudication_decision"] for row in rows)),
        "note": "proxy_adjudicated_60.jsonl is proxy adjudicated labels only, not human gold labels.",
    }
    write_json(REPORT_DIR / "proxy_adjudication_summary.json", summary)
    report = "# Proxy Adjudication 60\n\nThese labels are proxy adjudicated labels, not human gold labels.\n\n```json\n" + json.dumps(summary, ensure_ascii=False, indent=2) + "\n```\n"
    (ROOT / "reports" / "proxy_adjudication_60.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
