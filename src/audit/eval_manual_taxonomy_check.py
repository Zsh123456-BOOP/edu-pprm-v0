from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.audit.common import load_coarse_map, off_by_one_rate, rows_by_id
from src.data.common import DATA_DIR, REPORT_DIR, ROOT, read_jsonl_file, write_json

MANUAL_DIR = DATA_DIR / "manual"
DEFAULT_LABELS = MANUAL_DIR / "phase3_17_human_labels_24.jsonl"
DEFAULT_PRIVATE = MANUAL_DIR / "phase3_17_human_analysis_private.jsonl"
DEFAULT_DEEPSEEK = DATA_DIR / "audit" / "deepseek_audit_60.labels.jsonl"

COARSE_REPAIRS = {
    "no_intervention",
    "local_computation",
    "quantity_or_condition",
    "equation_or_formula",
    "verification_check",
    "insufficient_or_clarify",
}
HINT_COARSE = {"none", "nudge", "targeted_or_scaffolded"}
TRACE_VALIDITY = {"as_intended", "visible_but_other_error", "no_visible_error", "insufficient_trace"}


def parse_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text in {"", "null", "none", "na", "n/a"}:
        return None
    if "." in text:
        as_float = float(text)
        if as_float.is_integer():
            return int(as_float)
    return int(text)


def parse_intervention(value: Any) -> bool | str:
    if value is True or value is False:
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    if text == "uncertain":
        return "uncertain"
    raise ValueError(f"invalid intervention_needed: {value}")


def read_label_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        rows = read_jsonl_file(path)
    labels = []
    for row in rows:
        if not str(row.get("rationale") or "").strip():
            continue
        labels.append(
            {
                "sample_id": row["sample_id"],
                "reviewer_id": str(row.get("reviewer_id") or "").strip(),
                "first_wrong_step": parse_optional_int(row.get("first_wrong_step")),
                "intervention_needed": parse_intervention(row.get("intervention_needed")),
                "minimal_repair_coarse_6": str(row.get("minimal_repair_coarse_6") or "").strip(),
                "hint_level_coarse_3": str(row.get("hint_level_coarse_3") or "").strip(),
                "trace_validity_for_intended_type": str(row.get("trace_validity_for_intended_type") or "").strip(),
                "rationale": str(row.get("rationale") or "").strip(),
                "earliest_actionable_step_optional": parse_optional_int(row.get("earliest_actionable_step_optional")),
                "leakage_risk_binary": None if row.get("leakage_risk_binary") in {None, ""} else str(row.get("leakage_risk_binary")).strip(),
            }
        )
    return labels


def validate_label(label: dict[str, Any]) -> list[str]:
    errors = []
    if not label["sample_id"]:
        errors.append("sample_id required")
    if label["intervention_needed"] not in {True, False, "uncertain"}:
        errors.append("invalid intervention_needed")
    if label["minimal_repair_coarse_6"] not in COARSE_REPAIRS:
        errors.append("invalid minimal_repair_coarse_6")
    if label["hint_level_coarse_3"] not in HINT_COARSE:
        errors.append("invalid hint_level_coarse_3")
    if label["trace_validity_for_intended_type"] not in TRACE_VALIDITY:
        errors.append("invalid trace_validity_for_intended_type")
    if label["leakage_risk_binary"] not in {"yes", "no", None}:
        errors.append("invalid leakage_risk_binary")
    if not label["rationale"]:
        errors.append("rationale required")
    return errors


def hint_to_coarse(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    if value == "none":
        return "none"
    if value == "low":
        return "nudge"
    if value in {"medium", "high", "forbidden_full_solution"}:
        return "targeted_or_scaffolded"
    return None


def agreement(pairs: list[tuple[Any, Any]]) -> float | None:
    if not pairs:
        return None
    return round(sum(a == b for a, b in pairs) / len(pairs), 4)


def valid_trace_for_policy(synthetic_type: str | None, validity: str) -> bool:
    if validity == "as_intended":
        return True
    if synthetic_type == "sparse_insufficient_trace" and validity == "insufficient_trace":
        return True
    if synthetic_type == "hint_would_leak_answer" and validity in {"as_intended", "insufficient_trace"}:
        return True
    return False


def calibration_expected_options(private_row: dict[str, Any], coarse: dict[str, str]) -> list[dict[str, Any]]:
    base = {
        "first_wrong_step": private_row.get("expected_first_wrong_step"),
        "intervention_needed": private_row.get("expected_intervention_needed"),
        "minimal_repair_coarse_6": coarse.get(private_row.get("expected_minimal_repair_type")),
    }
    case_id = private_row.get("boundary_case_id")
    if case_id == "bc05_problem_misread":
        return [
            base,
            {
                "first_wrong_step": private_row.get("expected_first_wrong_step"),
                "intervention_needed": "uncertain",
                "minimal_repair_coarse_6": "insufficient_or_clarify",
            },
        ]
    if case_id == "bc08_wrong_answer_correct_prefix":
        return [
            base,
            {
                "first_wrong_step": private_row.get("expected_first_wrong_step"),
                "intervention_needed": private_row.get("expected_intervention_needed"),
                "minimal_repair_coarse_6": "verification_check",
            },
        ]
    return [base]


def write_pending(reason: str, label_count: int) -> int:
    payload = {"status": "pending", "label_count": label_count, "reason": reason}
    write_json(REPORT_DIR / "phase3_17_calibration_scorecard.json", payload)
    write_json(REPORT_DIR / "phase3_17_type_validity_summary.json", payload)
    write_json(REPORT_DIR / "phase3_17_repair_taxonomy_summary.json", payload)
    teacher_files = (
        "- `docs/phase3_17_human_review_instructions.md`\n"
        "- `data/manual/phase3_17_human_pack_24.blind.jsonl`\n"
        "- `data/manual/phase3_17_human_template_24.csv`\n"
        "- `data/manual/phase3_17_human_template_24.jsonl`\n"
    )
    private_files = (
        "- `data/manual/phase3_17_human_analysis_private.jsonl`\n"
        "- `data/manual/phase3_17_human_manifest.json`\n"
    )
    for name, title in [
        ("phase3_17_calibration_scorecard.md", "Phase 3.17 Calibration Scorecard"),
        ("phase3_17_synthetic_type_policy.md", "Phase 3.17 Synthetic Type Policy"),
        ("phase3_17_repair_taxonomy_check.md", "Phase 3.17 Repair Taxonomy Check"),
    ]:
        (ROOT / "reports" / name).write_text(
            f"# {title}\n\n"
            f"Status: pending\n\n{reason}\n\n"
            "## Teacher-Facing Files\n\n"
            f"{teacher_files}\n"
            "## Private Files\n\nDo not send these to reviewers:\n\n"
            f"{private_files}\n"
            "## Next Command\n\n"
            "After labels are returned, write them to `data/manual/phase3_17_human_labels_24.jsonl` "
            "or pass the filled CSV via `--labels`, then run:\n\n"
            "```bash\npython3 -m src.audit.eval_manual_taxonomy_check\n```\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Phase 3.17 human repair-taxonomy check labels")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS))
    parser.add_argument("--private", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--deepseek", default=str(DEFAULT_DEEPSEEK))
    args = parser.parse_args()

    labels = read_label_rows(Path(args.labels))
    if len(labels) < 24:
        return write_pending("Human labels are not complete; fill the 24-row template before evaluation.", len(labels))
    errors = []
    for label in labels:
        label_errors = validate_label(label)
        if label_errors:
            errors.append({"sample_id": label.get("sample_id"), "errors": label_errors})
    if errors:
        raise SystemExit(json.dumps({"status": "failed", "errors": errors}, ensure_ascii=False, indent=2))

    labels_by_id = {row["sample_id"]: row for row in labels}
    private = rows_by_id(Path(args.private))
    deepseek = rows_by_id(Path(args.deepseek)) if Path(args.deepseek).exists() else {}
    coarse = load_coarse_map()

    calibration_ids = [sid for sid, row in private.items() if row.get("review_group") == "calibration"]
    core_ids = [sid for sid, row in private.items() if row.get("review_group") != "calibration"]

    calibration_checks = []
    calibration_pass = 0
    for sid in sorted(calibration_ids):
        label = labels_by_id[sid]
        options = calibration_expected_options(private[sid], coarse)
        option_checks = [
            {
                "first_wrong_step": label["first_wrong_step"] == option["first_wrong_step"],
                "intervention_needed": label["intervention_needed"] == option["intervention_needed"],
                "minimal_repair_coarse_6": label["minimal_repair_coarse_6"] == option["minimal_repair_coarse_6"],
            }
            for option in options
        ]
        passed = any(all(checks.values()) for checks in option_checks)
        checks = next((checks for checks in option_checks if all(checks.values())), option_checks[0])
        calibration_pass += int(passed)
        calibration_checks.append({"sample_id": sid, "passed": passed, "checks": checks, "accepted_options": options})

    fw_pairs = []
    intervention_pairs = []
    repair_pairs = []
    hint_pairs = []
    missing_deepseek = []
    type_validity: dict[str, Counter] = defaultdict(Counter)
    retained_valid = 0
    retained_total = 0
    for sid in sorted(core_ids):
        label = labels_by_id[sid]
        synthetic_type = private[sid].get("synthetic_type")
        validity = label["trace_validity_for_intended_type"]
        type_validity[synthetic_type][validity] += 1
        retained_total += 1
        retained_valid += int(valid_trace_for_policy(synthetic_type, validity))
        deepseek_id = private[sid].get("original_sample_id", sid)
        if deepseek_id not in deepseek:
            missing_deepseek.append(sid)
            continue
        d = deepseek[deepseek_id]
        fw_pairs.append((label["first_wrong_step"], d.get("first_wrong_step")))
        intervention_pairs.append((label["intervention_needed"], d.get("intervention_needed")))
        repair_pairs.append((label["minimal_repair_coarse_6"], coarse.get(d.get("minimal_repair_type"))))
        hint_pairs.append((label["hint_level_coarse_3"], hint_to_coarse(d.get("hint_level"))))

    calibration_summary = {
        "status": "completed",
        "calibration_count": len(calibration_ids),
        "calibration_pass_count": calibration_pass,
        "calibration_pass_rate": round(calibration_pass / len(calibration_ids), 4) if calibration_ids else None,
        "calibration_checks": calibration_checks,
    }
    taxonomy_summary = {
        "status": "completed",
        "core_count": len(core_ids),
        "deepseek_compared_count": len(fw_pairs),
        "missing_deepseek_sample_ids": missing_deepseek,
        "first_wrong_step_off_by_one_agreement": off_by_one_rate(fw_pairs),
        "intervention_needed_agreement": agreement(intervention_pairs),
        "minimal_repair_coarse_6_agreement": agreement(repair_pairs),
        "hint_level_coarse_3_agreement": agreement(hint_pairs),
        "go_no_go": {
            "calibration_pass_rate>=7/8": calibration_pass >= 7,
            "first_wrong_step_off_by_one_agreement>=0.80": (off_by_one_rate(fw_pairs) or 0) >= 0.80,
            "intervention_needed_agreement>=0.80": (agreement(intervention_pairs) or 0) >= 0.80,
            "minimal_repair_coarse_6_agreement>=0.70": (agreement(repair_pairs) or 0) >= 0.70,
            "retained_types_trace_validity>=0.70": (retained_valid / retained_total if retained_total else 0) >= 0.70,
        },
    }
    type_summary = {
        "status": "completed",
        "type_validity_distribution": {key: dict(value) for key, value in type_validity.items()},
        "retained_types_trace_validity": round(retained_valid / retained_total, 4) if retained_total else None,
    }
    write_json(REPORT_DIR / "phase3_17_calibration_scorecard.json", calibration_summary)
    write_json(REPORT_DIR / "phase3_17_type_validity_summary.json", type_summary)
    write_json(REPORT_DIR / "phase3_17_repair_taxonomy_summary.json", taxonomy_summary)

    (ROOT / "reports" / "phase3_17_calibration_scorecard.md").write_text(
        "# Phase 3.17 Calibration Scorecard\n\n```json\n" + json.dumps(calibration_summary, ensure_ascii=False, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    (ROOT / "reports" / "phase3_17_synthetic_type_policy.md").write_text(
        "# Phase 3.17 Synthetic Type Policy\n\n```json\n" + json.dumps(type_summary, ensure_ascii=False, indent=2) + "\n```\n",
        encoding="utf-8",
    )
    (ROOT / "reports" / "phase3_17_repair_taxonomy_check.md").write_text(
        "# Phase 3.17 Repair Taxonomy Check\n\nThese are human review results, not training data and not silver labels.\n\n```json\n"
        + json.dumps(taxonomy_summary, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )
    print(json.dumps(taxonomy_summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
