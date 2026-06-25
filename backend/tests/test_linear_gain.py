import pytest

from app.download.linear_gain import compute_linear_gain_db


def test_compute_linear_gain_boosts_quiet_track() -> None:
    gain = compute_linear_gain_db(-15.0, -10.0, target_lufs=-9.0, peak_ceiling_db=-0.5)
    assert gain == pytest.approx(6.0)


def test_compute_linear_gain_caps_by_peak_headroom() -> None:
    # Would need +6 dB for LUFS but peak only allows +2 dB before -0.5 ceiling
    gain = compute_linear_gain_db(-15.0, -2.5, target_lufs=-9.0, peak_ceiling_db=-0.5)
    assert gain == pytest.approx(2.0)


def test_compute_linear_gain_never_attenuates() -> None:
    assert compute_linear_gain_db(-8.0, -1.0) == 0.0


def test_compute_linear_gain_no_measurement() -> None:
    assert compute_linear_gain_db(None, None) == 0.0
