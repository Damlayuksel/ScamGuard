import hashlib
import hmac

from app.config import get_settings


def hmac_sha256(value: str) -> str:
    """Keyed hash for device ids and IP addresses; plain values are never stored."""
    key = get_settings().secret_key.get_secret_value().encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()
