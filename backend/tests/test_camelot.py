from app.analysis.camelot import to_camelot


def test_camelot_a_minor() -> None:
    assert to_camelot("A", "minor") == "8A"


def test_camelot_c_major() -> None:
    assert to_camelot("C", "major") == "8B"
