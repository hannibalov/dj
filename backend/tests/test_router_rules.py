from app.router.rules import needs_review


def test_needs_review_when_too_quiet() -> None:
    assert needs_review(
        integrated_lufs=-20.0,
        true_peak_db=-2.0,
        lufs_threshold=-18.0,
        peak_threshold=-0.1,
    )


def test_needs_review_when_clipped() -> None:
    assert needs_review(
        integrated_lufs=-14.0,
        true_peak_db=0.5,
        lufs_threshold=-18.0,
        peak_threshold=-0.1,
    )


def test_passes_when_within_limits() -> None:
    assert not needs_review(
        integrated_lufs=-14.0,
        true_peak_db=-1.0,
        lufs_threshold=-18.0,
        peak_threshold=-0.1,
    )
