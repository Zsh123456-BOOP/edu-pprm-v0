from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.data.common import ROOT

TAXONOMY_PATH = ROOT / "configs" / "label_taxonomy.yaml"
REQUIRED_LABEL_SECTIONS = {
    "intervention_needed",
    "minimal_repair_type",
    "hint_level",
    "leakage_constraint",
}
REQUIRED_ENTRY_FIELDS = {
    "definition",
    "positive_examples",
    "negative_examples",
    "common_confusions",
}


def load_taxonomy(path: Path = TAXONOMY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_taxonomy(taxonomy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_sections = REQUIRED_LABEL_SECTIONS - set(taxonomy)
    if missing_sections:
        errors.append(f"missing sections: {sorted(missing_sections)}")
    for section, entries in taxonomy.items():
        if not isinstance(entries, dict):
            errors.append(f"{section} must be an object")
            continue
        for label, payload in entries.items():
            if not isinstance(payload, dict):
                errors.append(f"{section}.{label} must be an object")
                continue
            missing_fields = REQUIRED_ENTRY_FIELDS - set(payload)
            if missing_fields:
                errors.append(f"{section}.{label} missing {sorted(missing_fields)}")
            for list_field in ["positive_examples", "negative_examples", "common_confusions"]:
                value = payload.get(list_field)
                if not isinstance(value, list) or not value:
                    errors.append(f"{section}.{label}.{list_field} must be a non-empty list")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Edu-PPRM label taxonomy")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    taxonomy = load_taxonomy()
    errors = validate_taxonomy(taxonomy)
    print(f"taxonomy sections: {', '.join(taxonomy)}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
