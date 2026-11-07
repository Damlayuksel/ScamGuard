"""Error handling that never echoes or logs request content.

FastAPI's default validation error response includes the submitted `input`, and
Starlette re-raises unhandled exceptions so uvicorn logs their message. Both could
leak message text, so they are replaced here.
"""

import logging
import re
import traceback
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import mask_path

logger = logging.getLogger(__name__)

INTERNAL_ERROR_MESSAGE = "Beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin."
VALIDATION_ERROR_MESSAGE = "Gönderilen bilgiler geçersiz."

_HTTP_MESSAGES: dict[int, str] = {
    400: "İstek geçersiz.",
    401: "Bu işlem için yetkiniz yok.",
    403: "Bu işlem için yetkiniz yok.",
    404: "Aradığınız sayfa bulunamadı.",
    405: "Bu işlem desteklenmiyor.",
    409: "Bu işlem daha önce yapılmış.",
    413: "Gönderilen veri çok büyük.",
    429: "Çok fazla istek gönderdiniz. Lütfen biraz bekleyip tekrar deneyin.",
    500: INTERNAL_ERROR_MESSAGE,
    503: "Hizmet şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
}

_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "Bu alan zorunludur.",
    "string_type": "Metin bekleniyordu.",
    "string_too_short": "En az {min_length} karakter olmalıdır.",
    "string_too_long": "En fazla {max_length} karakter olabilir.",
    "json_invalid": "Gönderilen veri okunamadı.",
    "model_attributes_type": "Gönderilen veri okunamadı.",
    "uuid_parsing": "Geçersiz kimlik biçimi.",
    "uuid_type": "Geçersiz kimlik biçimi.",
    "enum": "Geçersiz seçim.",
    "literal_error": "Geçersiz seçim.",
    "int_parsing": "Sayı bekleniyordu.",
    "int_type": "Sayı bekleniyordu.",
    "extra_forbidden": "Bu alan kabul edilmiyor.",
}
_DEFAULT_VALIDATION_MESSAGE = "Geçersiz değer."
_SAFE_CTX_KEYS = ("min_length", "max_length")
_SAFE_LOC_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def _validation_message(error: dict[str, Any]) -> str:
    template = _VALIDATION_MESSAGES.get(error.get("type", ""), _DEFAULT_VALIDATION_MESSAGE)
    ctx = error.get("ctx") or {}
    try:
        return template.format(**{k: ctx[k] for k in _SAFE_CTX_KEYS if k in ctx})
    except (KeyError, IndexError):
        return _DEFAULT_VALIDATION_MESSAGE


def _validation_field(error: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for part in error.get("loc", ()):
        if isinstance(part, int):
            parts.append(str(part))
        elif isinstance(part, str) and _SAFE_LOC_PART.match(part):
            parts.append(part)
        else:
            return None
    return ".".join(parts) or None


async def _validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {"field": _validation_field(error), "message": _validation_message(error)}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": VALIDATION_ERROR_MESSAGE, "errors": errors},
    )


async def _http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    try:
        default_phrase = HTTPStatus(exc.status_code).phrase
    except ValueError:
        default_phrase = None
    if detail is None or detail == default_phrase:
        detail = _HTTP_MESSAGES.get(exc.status_code, _DEFAULT_VALIDATION_MESSAGE)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=getattr(exc, "headers", None),
    )


def log_exception_safely(exc: BaseException, method: str, path: str) -> None:
    """Logs exception types and stack frames only; exception messages may hold user content."""
    chain: list[str] = []
    current: BaseException | None = exc
    while current is not None and len(chain) < 5:
        chain.append(type(current).__qualname__)
        current = current.__cause__ or current.__context__
    frames = "".join(traceback.format_tb(exc.__traceback__))
    logger.error("Unhandled %s on %s %s\n%s", " <- ".join(chain), method, mask_path(path), frames)


class SafeErrorMiddleware:
    """Turns unhandled exceptions into a Turkish 500 response without re-raising."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            log_exception_safely(exc, scope.get("method", "-"), scope.get("path", "-"))
            if not response_started:
                response = JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR_MESSAGE})
                await response(scope, receive, send)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
