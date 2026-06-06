from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.data.common import ROOT, load_json_yaml, write_json

REQUIRED_FIELDS = {
    "source_name",
    "url_or_path",
    "license",
    "task_use",
    "allowed_split",
    "release_flag",
}
TRAIN_USES = {"full_train", "synthetic_train", "optional_pretrain", "gold_candidate"}


def load_registry(path: Path = ROOT / "configs" / "data_sources.yaml") -> dict[str, Any]:
    return load_json_yaml(path)


def check_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    names = set()
    for index, source in enumerate(registry.get("sources", [])):
        missing = REQUIRED_FIELDS - set(source)
        if missing:
            errors.append(f"sources[{index}] missing {sorted(missing)}")
        name = source.get("source_name")
        if name in names:
            errors.append(f"duplicate source_name: {name}")
        names.add(name)
        task_use = set(source.get("task_use", []))
        if "external_eval_only" in task_use and task_use & TRAIN_USES:
            errors.append(f"{name} mixes external_eval_only with train use: {sorted(task_use)}")
    for guarded_name in registry.get("guards", {}).get("external_eval_only_must_not_train", []):
        source = next((item for item in registry.get("sources", []) if item.get("source_name") == guarded_name), None)
        if not source:
            errors.append(f"guard references missing source: {guarded_name}")
            continue
        task_use = set(source.get("task_use", []))
        if task_use != {"external_eval_only"}:
            errors.append(f"{guarded_name} must be external_eval_only only, got {sorted(task_use)}")
    return errors


def build_usage_table(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source_name": item["source_name"],
            "role": item.get("role"),
            "task_use": item.get("task_use", []),
            "allowed_split": item.get("allowed_split", []),
            "license": item.get("license"),
            "release_flag": item.get("release_flag"),
            "url_or_path": item.get("url_or_path"),
        }
        for item in registry.get("sources", [])
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Edu-PPRM data source registry")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", default=str(ROOT / "data" / "reports" / "dataset_registry_summary.json"))
    args = parser.parse_args()

    registry = load_registry()
    errors = check_registry(registry)
    usage_table = build_usage_table(registry)
    summary = {"source_count": len(usage_table), "sources": usage_table, "errors": errors}
    write_json(Path(args.summary), summary)

    for row in usage_table:
        print(
            f"{row['source_name']}: use={','.join(row['task_use'])} "
            f"split={','.join(row['allowed_split'])} license={row['license']}"
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
