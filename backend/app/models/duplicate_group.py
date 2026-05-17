from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    preferred_track_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tracks.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fingerprints = relationship("Fingerprint", back_populates="duplicate_group")
