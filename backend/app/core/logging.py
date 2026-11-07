"""Logging setup that keeps personal data out of logs.

- Request bodies are never logged.
- Phone numbers appear in /numbers/{phone} paths, so those path segments are masked.
- Client IP addresses are dropped from the access log.
- httpx/httpcore log full URLs at INFO, so they are kept at WARNING.
"""

import logging
import re

_NUMBER_PATH = re.compile(r"(/numbers/)(?!report(?:[/?#]|$))[^/?#]+")

_NOISY_URL_LOGGERS = ("httpx", "httpcore")

HEALTH_PATH = "/api/v1/health"


def mask_path(path: str) -> str:
    return _NUMBER_PATH.sub(r"\1***", path)


class AccessLogPrivacyFilter(logging.Filter):
    """Rewrites uvicorn access log records: hides the client IP, masks phone numbers.

    Successful health checks (Docker polls every 15 s) are dropped so they do not bury
    real requests; failing ones are still logged.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5:
            _client, method, path, http_version, status = args
            if str(path) == HEALTH_PATH and status == 200:
                return False
            record.args = ("-", method, mask_path(str(path)), http_version, status)
        return True


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    for name in _NOISY_URL_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, AccessLogPrivacyFilter) for f in access_logger.filters):
        access_logger.addFilter(AccessLogPrivacyFilter())
