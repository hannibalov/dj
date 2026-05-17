from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tracks.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    duplicate_group_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("duplicate_groups.id", ondelete="SET NULL"), nullable=True
    )
    fingerprint_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_fingerprint: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    track = relationship("Track", back_populates="fingerprint")
    duplicate_group = relationship("DuplicateGroup", back_populates="fingerprints")
