from __future__ import annotations

import json
from pathlib import Path

from src.data.common import REPORT_DIR, ROOT
from src.eval.eval_deepseek_labels import evaluate


def main() -> int:
    metrics = evaluate(ROOT / "data" / "pilot" / "pilot_pool.raw.jsonl", ROOT / "data" / "pilot" / "pilot_pool.autolabeled.jsonl")
    label_summary = json.loads((REPORT_DIR / "deepseek_label_summary.json").read_text(encoding="utf-8"))
    lines = [
        "# Auto Pilot Label Report",
        "",
        f"API available: `{label_summary.get('api_available')}`.",
        "",
        "## StepVerify",
        "",
        json.dumps(metrics["stepverify"], ensure_ascii=False, indent=2),
        "",
        "## Synthetic",
        "",
        json.dumps(metrics["synthetic"], ensure_ascii=False, indent=2),
        "",
        "## Distribution",
        "",
        json.dumps(metrics["distribution"], ensure_ascii=False, indent=2),
    ]
    path = ROOT / "reports" / "auto_pilot_label_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
