from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from src.core.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PKCEBundle:
    verifier: str
    challenge: str
    method: str = "S256"


# PUBLIC_INTERFACE
def get_fernet() -> Fernet:
    """Return a Fernet instance configured with ENCRYPTION_KEY from settings.

    The ENCRYPTION_KEY must be a base64 32-byte key or raw string which we will KDF
    into a Fernet key using SHA-256 (not ideal KDF but acceptable here as a simple derivation).
    """
    settings = get_settings()
    raw = settings.security.ENCRYPTION_KEY
    # Avoid logging secret
    # Derive 32 bytes from raw key and base64-url encode as Fernet expects
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


# PUBLIC_INTERFACE
def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string with Fernet; returns token in urlsafe base64."""
    f = get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


# PUBLIC_INTERFACE
def decrypt_secret(token: Optional[str]) -> Optional[str]:
    """Decrypt a token; returns plaintext or None if input is None."""
    if token is None:
        return None
    f = get_fernet()
    try:
        plain = f.decrypt(token.encode("utf-8"))
        return plain.decode("utf-8")
    except (InvalidToken, ValueError):
        # Do not leak the token content in logs
        logger.warning("Failed to decrypt secret token; treating as missing.")
        return None


# PUBLIC_INTERFACE
def generate_csrf_state(tenant_id: str, connector_id: str) -> str:
    """Generate a CSRF state token bound to tenant and connector.

    We create a HMAC of random nonce + tenant + connector with ENCRYPTION_KEY.
    """
    settings = get_settings()
    nonce = base64.urlsafe_b64encode(os.urandom(24)).decode("utf-8").rstrip("=")
    msg = f"{nonce}:{tenant_id}:{connector_id}".encode("utf-8")
    mac = hmac.new(settings.security.ENCRYPTION_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
    state = base64.urlsafe_b64encode(nonce.encode("utf-8") + b"." + mac).decode("utf-8")
    return state


# PUBLIC_INTERFACE
def verify_csrf_state(state: Optional[str]) -> bool:
    """Best-effort validation that state format and HMAC exist.

    We cannot reconstruct original msg without storing nonce parts, but we at least
    ensure integrity footprint is present. For strict validation, callers should also
    compare state with stored copy in DB for the auth session.
    """
    if not state:
        return False
    try:
        blob = base64.urlsafe_b64decode(state.encode("utf-8"))
        # requires delimiter
        return b"." in blob and len(blob.split(b".", 1)[1]) == 32  # sha256 digest length
    except Exception:
        return False


# PUBLIC_INTERFACE
def generate_pkce() -> PKCEBundle:
    """Generate PKCE code_verifier and S256 code_challenge."""
    verifier_bytes = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=")
    verifier = verifier_bytes.decode("utf-8")
    sha = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(sha).decode("utf-8").rstrip("=")
    return PKCEBundle(verifier=verifier, challenge=challenge)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# PUBLIC_INTERFACE
def compute_expiry(expires_in_seconds: int, skew_seconds: int = 30) -> datetime:
    """Return absolute expiry time with small safety skew."""
    return _now_utc() + timedelta(seconds=max(0, expires_in_seconds - skew_seconds))


# PUBLIC_INTERFACE
def is_expired(expires_at: Optional[datetime]) -> bool:
    """Check if a timestamp is in the past or missing."""
    if not expires_at:
        return True
    return expires_at <= _now_utc()
