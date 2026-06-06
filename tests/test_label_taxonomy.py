from src.labels.taxonomy import load_taxonomy, validate_taxonomy


def test_taxonomy_complete():
    taxonomy = load_taxonomy()
    assert validate_taxonomy(taxonomy) == []


def test_taxonomy_keeps_minimal_repair_small():
    taxonomy = load_taxonomy()
    assert len(taxonomy["minimal_repair_type"]) == 11
