from app.metadata.sanity import detect_possible_swap, title_contains_artist


def test_detect_possible_swap_true_when_title_is_known_artist() -> None:
    known = frozenset({"Oasis", "Eric Prydz"})
    assert detect_possible_swap("Wonderwall", "Oasis", known) is True


def test_detect_possible_swap_false_when_artist_also_known() -> None:
    known = frozenset({"Oasis", "Eric Prydz"})
    # Both sides match a known artist — not the asymmetric "probably reversed" signal.
    assert detect_possible_swap("Oasis", "Eric Prydz", known) is False


def test_detect_possible_swap_false_when_neither_side_known() -> None:
    known = frozenset({"Oasis"})
    assert detect_possible_swap("Some Artist", "Some Title", known) is False


def test_detect_possible_swap_handles_no_known_artists_gracefully() -> None:
    assert detect_possible_swap("Some Artist", "Some Title", frozenset()) is False


def test_title_contains_artist_true_for_plain_containment() -> None:
    assert title_contains_artist("Daft Punk", "Daft Punk - One More Time") is True


def test_title_contains_artist_false_when_not_present() -> None:
    assert title_contains_artist("Daft Punk", "One More Time") is False


def test_title_contains_artist_short_artist_name_guard() -> None:
    # "Air" is < 4 chars — containment check must be skipped to avoid false positives.
    assert title_contains_artist("Air", "Airwaves Anthem") is False


def test_title_contains_artist_ignores_trailing_remix_credit_parenthetical() -> None:
    # The mix-version tag legitimately includes the remixer's name — must not be flagged.
    assert title_contains_artist("Eric Prydz", "Opus (Eric Prydz Remix)") is False


def test_title_contains_artist_exact_equality_still_flags() -> None:
    assert title_contains_artist("Eric Prydz", "Eric Prydz") is True
