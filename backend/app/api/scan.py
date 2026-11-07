from fastapi import APIRouter, Request

from app.core import ratelimit
from app.core.client_ip import client_ip
from app.scanner.pipeline import scan
from app.schemas.scan import ScannedLink, ScanRequest, ScanResponse
from app.services import scan_stats
from app.services.scan_texts import ADVICE, LABELS, MESSAGES

router = APIRouter(tags=["scan"])


@router.post("/scan", response_model=ScanResponse)
async def scan_message(body: ScanRequest, request: Request) -> ScanResponse:
    """Scans a message. The text is never stored; only domain + level go to scan_stats."""
    await ratelimit.check(ratelimit.SCAN_PER_IP, client_ip(request))

    result = await scan(body.text)
    await scan_stats.record(result)

    return ScanResponse(
        level=result.level,
        label=LABELS[result.level],
        message=MESSAGES[result.level],
        score=result.score,
        reasons=result.reasons,
        links=[
            ScannedLink(domain=link.domain, score=link.score, reasons=link.reasons)
            for link in result.links
        ],
        advice=ADVICE[result.level],
    )
