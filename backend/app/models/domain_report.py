from datetime import datetime

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column
from app.models.blacklist import HOST_MAX_LENGTH

# Hex-encoded HMAC-SHA256.
HASH_LENGTH = 64


class DomainReport(Base):
    __tablename__ = "domain_reports"
    __table_args__ = (UniqueConstraint("domain", "device_hash"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain: Mapped[str] = mapped_column(String(HOST_MAX_LENGTH), index=True)
    device_hash: Mapped[str] = mapped_column(String(HASH_LENGTH))
    created_at: Mapped[datetime] = created_at_column()
