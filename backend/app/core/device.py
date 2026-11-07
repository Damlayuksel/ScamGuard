"""Anonymous device id sent by the app in the X-Device-Id header (a random UUID).

The plain value is never stored; callers use its HMAC hash.
"""

import uuid
from typing import Annotated

from fastapi import Header, HTTPException

INVALID_DEVICE_MESSAGE = "Cihaz kimliği eksik veya geçersiz. Lütfen uygulamayı yeniden açın."


def device_id(
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> str:
    try:
        return str(uuid.UUID(x_device_id or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=INVALID_DEVICE_MESSAGE) from exc
