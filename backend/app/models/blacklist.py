from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, str_enum

# RFC 1035 limit for a full hostname.
HOST_MAX_LENGTH = 253


class BlacklistSource(StrEnum):
    USOM = "usom"
    URLHAUS = "urlhaus"
    COMMUNITY = "community"


class BlacklistDomain(Base):
    """A blacklisted hostname (never a full URL)."""

    __tablename__ = "blacklist_domains"
    __table_args__ = (UniqueConstraint("domain", "source"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain: Mapped[str] = mapped_column(String(HOST_MAX_LENGTH), index=True)
    source: Mapped[BlacklistSource] = mapped_column(str_enum(BlacklistSource, "blacklist_source"))
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
