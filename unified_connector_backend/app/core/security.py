# PUBLIC_INTERFACE
"""
Security helpers: optional AES-GCM encryption/decryption of credential blobs.

Use ENCRYPTION_KEY environment variable if provided. If missing, credentials are stored plaintext in memory
(but we still ensure they are never logged).
"""
from __future__ import annotations

import base64
import os
import secrets
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .settings import get_settings


def _normalize_key(raw: str) -> bytes:
    # Accept base64 or hex or raw utf-8. Prefer 32 bytes.
    try:
        return base64.b64decode(raw)
    except Exception:
        try:
            return bytes.fromhex(raw)
        except Exception:
            data = raw.encode("utf-8")
            # stretch or trim to 32 bytes deterministically (demo only)
            if len(data) >= 32:
                return data[:32]
            return (data + b"\0" * 32)[:32]


def _get_aesgcm() -> Optional[AESGCM]:
    key_env = get_settings().encryption_key
    if not key_env:
        return None
    key = _normalize_key(key_env)
    return AESGCM(key)


# PUBLIC_INTERFACE
def encrypt_blob(plaintext: bytes) -> bytes:
    """Encrypt bytes using AES-GCM with random nonce. Returns nonce|ciphertext|tag."""
    aead = _get_aesgcm()
    if not aead:
        return plaintext
    nonce = secrets.token_bytes(12)
    ct = aead.encrypt(nonce, plaintext, associated_data=None)
    return nonce + ct


# PUBLIC_INTERFACE
def decrypt_blob(blob: bytes) -> bytes:
    """Decrypt bytes using AES-GCM. Input must be nonce|ciphertext|tag."""
    aead = _get_aesgcm()
    if not aead:
        return blob
    nonce, ct = blob[:12], blob[12:]
    return aead.decrypt(nonce, ct, associated_data=None)
