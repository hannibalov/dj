from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fingerprints = relationship("Fingerprint", back_populates="duplicate_group")
