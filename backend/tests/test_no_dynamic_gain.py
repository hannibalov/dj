"""Regression guard: the pipeline must only ever apply a single constant volume gain.

app/download/linear_gain.py computes one static `volume=XdB` ffmpeg filter per file from
measured LUFS. Dynamic/adaptive audio filters (loudnorm, dynaudnorm, compand, acompressor)
must never be reintroduced anywhere in the backend — they reshape dynamics per-sample instead
of applying a single uniform offset, which defeats the "constant gain" design.
"""

from pathlib import Path

_FORBIDDEN_FILTERS = ("loudnorm", "dynaudnorm", "compand", "acompressor")

_APP_ROOT = Path(__file__).parent.parent / "app"


def test_no_dynamic_gain_filters_in_app_source() -> None:
    violations: list[str] = []
    for path in _APP_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8").casefold()
        for filt in _FORBIDDEN_FILTERS:
            if filt in text:
                violations.append(f"{path}: contains forbidden dynamic-gain filter '{filt}'")

    assert not violations, "\n".join(violations)
