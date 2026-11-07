"""Community domain reports (layer 4).

A domain reported from COMMUNITY_THRESHOLD different devices joins the community blacklist.
"""

import logging
from enum import StrEnum

from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app import db
from app.core.hashing import hmac_sha256
from app.models import BlacklistDomain, BlacklistSource, DomainReport
from app.scanner.hosts import host_from_entry, is_protected
from app.worker import blacklist_store

logger = logging.getLogger(__name__)

COMMUNITY_THRESHOLD = 5


class ReportOutcome(StrEnum):
    RECORDED = "recorded"
    DUPLICATE = "duplicate"


class InvalidDomain(ValueError):
    pass


class ProtectedDomain(ValueError):
    pass


def normalize_reported_domain(raw: str) -> str:
    host = host_from_entry(raw)
    if host is None or "." not in host:
        raise InvalidDomain
    if is_protected(host):
        raise ProtectedDomain
    return host


async def report_domain(raw_domain: str, device_id: str) -> ReportOutcome:
    domain = normalize_reported_domain(raw_domain)
    device_hash = hmac_sha256(device_id)

    async with db.get_sessionmaker()() as session:
        inserted = await session.scalar(
            insert(DomainReport)
            .values(domain=domain, device_hash=device_hash)
            .on_conflict_do_nothing(index_elements=["domain", "device_hash"])
            .returning(DomainReport.id)
        )
        devices = await session.scalar(
            select(func.count(func.distinct(DomainReport.device_hash))).where(
                DomainReport.domain == domain
            )
        )
        promoted = False
        if devices is not None and devices >= COMMUNITY_THRESHOLD:
            promoted = (
                await session.scalar(
                    insert(BlacklistDomain)
                    .values(domain=domain, source=BlacklistSource.COMMUNITY)
                    .on_conflict_do_nothing(index_elements=["domain", "source"])
                    .returning(BlacklistDomain.id)
                )
                is not None
            )
        await session.commit()

    if promoted:
        logger.info("A domain reached the community blacklist threshold")
        try:
            await blacklist_store.add_to_redis(domain, BlacklistSource.COMMUNITY)
        except RedisError:
            logger.warning("Redis unavailable; community entry will appear after the next sync")

    return ReportOutcome.RECORDED if inserted is not None else ReportOutcome.DUPLICATE
