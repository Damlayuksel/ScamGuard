from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, str_enum
from app.models.blacklist import HOST_MAX_LENGTH


class ScanLevel(StrEnum):
    DANGEROUS = "dangerous"
    SUSPICIOUS = "suspicious"
    NO_KNOWN_THREAT = "no_known_threat"


class ScanStat(Base):
    """Aggregate scan statistics. Holds only a hostname, never message text or a full URL."""

    __tablename__ = "scan_stats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain: Mapped[str | None] = mapped_column(String(HOST_MAX_LENGTH), nullable=True)
    level: Mapped[ScanLevel] = mapped_column(str_enum(ScanLevel, "scan_level"))
    created_at: Mapped[datetime] = created_at_column()
