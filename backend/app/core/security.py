"""
Password hashing + JWT token utilities for BhaavShare auth.
"""
import hashlib
import hmac
import json
import base64
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings

# ---------------------------------------------------------------
# Password hashing — PBKDF2-HMAC-SHA256 (stdlib-only, no extra deps)
# ---------------------------------------------------------------
_PBKDF2_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, hexhash = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters))
        return hmac.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False


# ---------------------------------------------------------------
# Minimal JWT (HS256) — stdlib only
# ---------------------------------------------------------------
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_access_token(subject: str, extra: Optional[dict] = None,
                        expires_minutes: int = None) -> str:
    expires_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(subject),
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_minutes * 60,
    }
    if extra:
        payload.update(extra)

    h_enc = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_enc = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h_enc}.{p_enc}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    s_enc = _b64url_encode(sig)
    return f"{h_enc}.{p_enc}.{s_enc}"


def decode_access_token(token: str) -> Optional[dict]:
    try:
        h_enc, p_enc, s_enc = token.split(".")
        signing_input = f"{h_enc}.{p_enc}".encode()
        expected = hmac.new(settings.SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(s_enc), expected):
            return None
        payload = json.loads(_b64url_decode(p_enc))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
