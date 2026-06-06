import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reserved_fields_are_nullable_placeholders():
    schema = json.loads((ROOT / "schemas" / "edu_pprm.schema.json").read_text(encoding="utf-8"))
    reserved = schema["properties"]["reserved"]["properties"]
    assert reserved["handwrite_data"]["default"] is None
    assert reserved["budget_data"]["default"] is None
    assert reserved["distillation_data"]["default"] is None


def test_phase1_builders_do_not_depend_on_handwrite_data():
    src = ROOT / "src" / "data"
    relevant_files = [
        "load_stepverify.py",
        "load_mathedu.py",
        "load_gsm8k.py",
        "load_math.py",
        "load_prm800k.py",
        "load_processbench.py",
    ]
    for filename in relevant_files:
        text = (src / filename).read_text(encoding="utf-8")
        assert "handwrite_data" not in text
        assert "budget_data" not in text
        assert "distillation_data" not in text
