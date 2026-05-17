def needs_review(
    *,
    integrated_lufs: float | None,
    true_peak_db: float | None,
    lufs_threshold: float,
    peak_threshold: float,
) -> bool:
    """True when track is too quiet or clipped per spec."""
    too_quiet = integrated_lufs is not None and integrated_lufs < lufs_threshold
    clipped = true_peak_db is not None and true_peak_db > peak_threshold
    return too_quiet or clipped
