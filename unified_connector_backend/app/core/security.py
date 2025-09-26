from cryptography.fernet import Fernet, InvalidToken
from .config import settings

def _get_cipher() -> Fernet:
    # Expect ENCRYPTION_KEY env var base64 url-safe 32 bytes; if not, we derive from SECRET_KEY (dev only)
    key = settings.ENCRYPTION_KEY
    if not key or len(key) < 32:
        # WARNING: This fallback is for development only
        import base64, hashlib
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)

def encrypt_secret(value: str) -> str:
    if not value:
        return value
    f = _get_cipher()
    return f.encrypt(value.encode()).decode()

def decrypt_secret(token: str) -> str:
    if not token:
        return token
    f = _get_cipher()
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        # Return as-is if can't decrypt (migrating)
        return token
