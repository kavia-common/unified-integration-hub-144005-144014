import base64
import os

# NOTE: For MVP/demo only. Replace with proper KMS/HSM at rest encryption.
_SECRET = (os.getenv("ENC_KEY") or "dev-secret").encode("utf-8")

def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

# PUBLIC_INTERFACE
def encrypt_str(plain: str) -> str:
    """Encrypt a string deterministically for at-rest storage (demo only)."""
    enc = _xor_bytes(plain.encode("utf-8"), _SECRET)
    return base64.urlsafe_b64encode(enc).decode("utf-8")

# PUBLIC_INTERFACE
def decrypt_str(token: str) -> str:
    """Decrypt a string encrypted by encrypt_str."""
    raw = base64.urlsafe_b64decode(token.encode("utf-8"))
    dec = _xor_bytes(raw, _SECRET)
    return dec.decode("utf-8")
