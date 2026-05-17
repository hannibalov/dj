"""Lightweight SQLite migrations for additive columns."""

from sqlalchemy import Engine, inspect, text


def _add_columns(engine: Engine, table: str, additions: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    with engine.begin() as conn:
        for name, col_type in additions.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}"))


def migrate_tracks_analysis_columns(engine: Engine) -> None:
    _add_columns(
        engine,
        "tracks",
        {
            "scale": "VARCHAR(16)",
            "bpm_confidence": "FLOAT",
            "key_confidence": "FLOAT",
            "integrated_lufs": "FLOAT",
            "true_peak_db": "FLOAT",
        },
    )


def migrate_phase4_columns(engine: Engine) -> None:
    _add_columns(
        engine,
        "tracks",
        {
            "album": "VARCHAR(512)",
            "mix_version": "VARCHAR(256)",
            "musicbrainz_recording_id": "VARCHAR(64)",
            "tag_confidence": "FLOAT",
            "needs_metadata_review": "BOOLEAN DEFAULT 0",
            "tagged_at": "DATETIME",
        },
    )
    _add_columns(
        engine,
        "fingerprints",
        {
            "raw_fingerprint": "VARCHAR(8192)",
        },
    )


def run_migrations(engine: Engine) -> None:
    migrate_tracks_analysis_columns(engine)
    migrate_phase4_columns(engine)
