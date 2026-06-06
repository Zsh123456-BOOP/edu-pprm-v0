from src.data.validate_schema import validate_sample, write_schema_examples


def test_schema_examples_validate():
    examples = write_schema_examples()
    assert len(examples) >= 15
    for sample in examples:
        validate_sample(sample)


def test_reserved_fields_are_null_in_examples():
    for sample in write_schema_examples():
        assert sample["reserved"] == {
            "budget_data": None,
            "distillation_data": None,
            "handwrite_data": None,
        }
