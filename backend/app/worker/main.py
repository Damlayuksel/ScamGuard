"""Scheduled jobs entry point: `python -m app.worker.main`."""

import asyncio
import logging
import signal
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging import configure_logging
from app.worker.jobs import run_job

logger = logging.getLogger("app.worker")

TIMEZONE = "Europe/Istanbul"
_JOB_DEFAULTS = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 300}


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE, job_defaults=_JOB_DEFAULTS)
    now = datetime.now(scheduler.timezone)

    def add(job: str, trigger: str, **kwargs: object) -> None:
        scheduler.add_job(run_job, trigger, args=[job], id=job, **kwargs)

    # On start: rebuild the Redis lookup hash from Postgres (no download) and download a
    # feed only if its data is missing. Deploys therefore cause no extra downloads.
    add("sync", "date", run_date=now)
    add("usom-if-empty", "date", run_date=now)
    add("urlhaus-if-empty", "date", run_date=now)
    add("rdap-if-missing", "date", run_date=now)

    # Every external download runs once a day, at night (Europe/Istanbul).
    add("usom", "cron", hour=3, minute=30)
    add("urlhaus", "cron", hour=3, minute=50)
    add("rdap-bootstrap", "cron", hour=4, minute=0)
    add("purge", "cron", hour=4, minute=30)
    return scheduler


async def run() -> None:
    configure_logging()
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Worker started with %d job(s)", len(scheduler.get_jobs()))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await stop.wait()
    scheduler.shutdown(wait=False)
    logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(run())
