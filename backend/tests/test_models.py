import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hashing import hmac_sha256
from app.models import BlacklistDomain, BlacklistSource, DomainReport, ScanLevel, ScanStat


def test_hmac_is_keyed_and_deterministic() -> None:
    value = "203.0.113.7"

    digest = hmac_sha256(value)

    assert digest == hmac_sha256(value)
    assert digest != hmac_sha256("203.0.113.8")
    assert len(digest) == 64
    assert value not in digest


async def test_same_domain_can_come_from_several_sources(db_session: AsyncSession) -> None:
    db_session.add_all(
        [
            BlacklistDomain(domain="evil.example", source=BlacklistSource.USOM),
            BlacklistDomain(domain="evil.example", source=BlacklistSource.URLHAUS),
        ]
    )
    await db_session.commit()

    rows = (await db_session.scalars(select(BlacklistDomain.source))).all()
    assert sorted(rows) == [BlacklistSource.URLHAUS, BlacklistSource.USOM]


async def test_domain_report_unique_per_device(db_session: AsyncSession) -> None:
    device_hash = hmac_sha256("device-1")
    db_session.add(DomainReport(domain="evil.example", device_hash=device_hash))
    await db_session.commit()

    db_session.add(DomainReport(domain="evil.example", device_hash=device_hash))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_scan_stat_allows_missing_domain(db_session: AsyncSession) -> None:
    db_session.add(ScanStat(domain=None, level=ScanLevel.NO_KNOWN_THREAT))
    await db_session.commit()

    stat = await db_session.scalar(select(ScanStat))
    assert stat is not None
    assert stat.level is ScanLevel.NO_KNOWN_THREAT
