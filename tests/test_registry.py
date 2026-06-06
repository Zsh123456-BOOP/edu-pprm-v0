from src.data.dataset_registry import check_registry, load_registry


def test_registry_valid_and_processbench_external_only():
    registry = load_registry()
    assert check_registry(registry) == []
    processbench = next(item for item in registry["sources"] if item["source_name"] == "processbench")
    assert processbench["task_use"] == ["external_eval_only"]
