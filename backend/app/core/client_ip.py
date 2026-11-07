"""Client IP for rate limiting.

X-Forwarded-For is applied by uvicorn's proxy-headers middleware only when the direct peer
is listed in FORWARDED_ALLOW_IPS (set from TRUSTED_PROXIES), so request.client is already
the real client here. The value is only ever used hashed.
"""

from fastapi import Request


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
