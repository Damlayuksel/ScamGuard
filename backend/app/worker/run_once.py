"""Runs a single worker job by hand: `python -m app.worker.run_once usom|urlhaus|purge|sync`."""

import asyncio
import sys

from app.cache import close_redis
from app.core.logging import configure_logging
from app.db import dispose_engine
from app.worker.jobs import JOBS


async def _main(name: str) -> int:
    configure_logging()
    try:
        result = await JOBS[name]()
    finally:
        await dispose_engine()
        await close_redis()
    print(f"{name}: {result}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in JOBS:
        print(f"usage: python -m app.worker.run_once {{{'|'.join(JOBS)}}}", file=sys.stderr)
        sys.exit(2)
    sys.exit(asyncio.run(_main(sys.argv[1])))
