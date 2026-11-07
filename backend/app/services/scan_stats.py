"""Aggregate scan statistics: only registered domains and the result level are stored."""

import logging

from app import db
from app.models import ScanStat
from app.scanner.pipeline import ScanResult

logger = logging.getLogger(__name__)


async def record(result: ScanResult) -> None:
    """Best effort: a statistics failure never fails the scan."""
    domains = sorted({domain for link in result.links for domain in link.domains})
    rows = [ScanStat(domain=domain, level=result.level) for domain in domains] or [
        ScanStat(domain=None, level=result.level)
    ]
    try:
        async with db.get_sessionmaker()() as session:
            session.add_all(rows)
            await session.commit()
    except Exception as exc:
        logger.error("Could not record scan statistics: %s", type(exc).__qualname__)
