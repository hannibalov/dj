from app.analysis.loudness import _parse_integrated_lufs, _parse_last

_SAMPLE_EBUR128_OUTPUT = """
[Parsed_ebur128_0] t: 0.0999792  TARGET:-23 LUFS    M:-120.7 S:-120.7     I: -70.0 LUFS
[Parsed_ebur128_0] t: 257.999979 TARGET:-23 LUFS    M: -39.7 S: -33.2     I:  -8.6 LUFS
[Parsed_ebur128_0] Summary:

  Integrated loudness:
    I:          -8.6 LUFS
    Threshold: -19.2 LUFS

  True peak:
    Peak:        1.5 dBFS
"""


def test_parse_integrated_lufs_uses_summary_not_initial_meter() -> None:
    assert _parse_integrated_lufs(_SAMPLE_EBUR128_OUTPUT) == -8.6


def test_parse_last_peak_from_summary() -> None:
    from app.analysis.loudness import _PEAK_RE

    assert _parse_last(_PEAK_RE, _SAMPLE_EBUR128_OUTPUT) == 1.5
