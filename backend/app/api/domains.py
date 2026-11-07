from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core import ratelimit
from app.core.device import device_id
from app.schemas.domains import DomainReportRequest, DomainReportResponse
from app.services.domain_reports import InvalidDomain, ProtectedDomain, report_domain

router = APIRouter(tags=["domains"])

THANKS_MESSAGE = "Bildiriminiz alındı. Teşekkür ederiz."
INVALID_DOMAIN_MESSAGE = "Lütfen geçerli bir site adresi girin (ör. ornek-site.com)."
PROTECTED_DOMAIN_MESSAGE = (
    "Bu adres resmî bir kuruma ya da bilinen bir platforma ait olduğu için bildirilemez."
)


@router.post("/domains/report", response_model=DomainReportResponse)
async def report(
    body: DomainReportRequest, device: Annotated[str, Depends(device_id)]
) -> DomainReportResponse:
    """Reports a suspicious domain. The same device reporting again is accepted silently."""
    await ratelimit.check(ratelimit.DOMAIN_REPORT_PER_DEVICE, device)
    try:
        await report_domain(body.domain, device)
    except InvalidDomain as exc:
        raise HTTPException(status_code=400, detail=INVALID_DOMAIN_MESSAGE) from exc
    except ProtectedDomain as exc:
        raise HTTPException(status_code=400, detail=PROTECTED_DOMAIN_MESSAGE) from exc
    return DomainReportResponse(message=THANKS_MESSAGE)
