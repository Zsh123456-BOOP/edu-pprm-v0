from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found")
    return cleaned[start : end + 1]


def parse_json_object(text: str) -> dict[str, Any]:
    return json.loads(extract_json_object(text))
