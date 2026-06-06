from src.data.load_processbench import assert_external_only


def test_processbench_guard_accepts_external_eval_path():
    assert_external_only("data/external_eval/processbench.external_eval.raw.jsonl")


def test_processbench_guard_rejects_train_path():
    try:
        assert_external_only("data/interim/processbench.raw.jsonl")
    except ValueError:
        return
    raise AssertionError("ProcessBench train/interim path should be rejected")
