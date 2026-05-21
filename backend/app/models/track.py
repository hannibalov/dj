from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TrackStatus


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[TrackStatus] = mapped_column(Enum(TrackStatus), default=TrackStatus.QUEUED)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    processing_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    final_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    album: Mapped[str | None] = mapped_column(String(512), nullable=True)
    genre: Mapped[str | None] = mapped_column(String(256), nullable=True)
    subgenre: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mix_version: Mapped[str | None] = mapped_column(String(256), nullable=True)
    musicbrainz_recording_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tag_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_metadata_review: Mapped[bool] = mapped_column(default=False)
    tagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    musical_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    camelot: Mapped[str | None] = mapped_column(String(8), nullable=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    bpm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    key_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    integrated_lufs: Mapped[float | None] = mapped_column(Float, nullable=True)
    true_peak_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fingerprint = relationship("Fingerprint", back_populates="track", uselist=False)
