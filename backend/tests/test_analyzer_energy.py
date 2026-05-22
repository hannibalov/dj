from app.analysis.analyzer import _energy_from_lufs


def test_energy_from_lufs_spreads_across_typical_library() -> None:
    quiet = _energy_from_lufs(-20.0)
    groove = _energy_from_lufs(-14.0)
    loud = _energy_from_lufs(-9.0)
    assert quiet < groove < loud
    assert 0 <= quiet <= 100
    assert 0 <= loud <= 100
    assert loud < 100  # club masters should not all clip


def test_energy_from_lufs_clamps_extremes() -> None:
    assert _energy_from_lufs(-30.0) == 0
    assert _energy_from_lufs(0.0) == 100
