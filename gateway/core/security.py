"""
Stateless crypto helpers – no DB, no HTTP side-effects.
"""
from __future__ import annotations
import json
import time
from functools import lru_cache
from typing import Dict
import httpx
import jwt  # PyJWT
from argon2 import PasswordHasher
from jwt import InvalidTokenError
from gateway.core.exceptions import AppException
from gateway.config import settings


JWT_ALG = "HS256"
_JWT_SECRET = settings.jwt_secret  # override via env / DI

_hasher = PasswordHasher()

# ── Passwords ──────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return _hasher.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except Exception:  # noqa: BLE001
        return False
    
# ── JWT --------------------------------------------------------------------
def create_access_token(data: Dict, exp_seconds: int = 3600, secret: str | None = None) -> str:
    payload = data.copy()
    payload["exp"] = int(time.time()) + exp_seconds
    return jwt.encode(payload, secret or _JWT_SECRET, algorithm=JWT_ALG)

def verify_token(token: str, secret: str | None = None) -> Dict:
    try:
        return jwt.decode(token, secret or _JWT_SECRET, algorithms=[JWT_ALG])
    except InvalidTokenError as exc:

        raise AppException(code="auth/invalid-token", message=str(exc), status_code=401) from exc


# ── OAuth → remote JWKS -----------------------------------------------------
@lru_cache(maxsize=4)
def _fetch_jwks(jwks_url: str) -> Dict:
    jwks = httpx.get(jwks_url, timeout=4).json()
    return {k["kid"]: k for k in jwks["keys"]}


def parse_jwt_from_provider(token: str, jwks_url: str) -> Dict:
    unverified = jwt.get_unverified_header(token)
    kid = unverified["kid"]
    jwk = _fetch_jwks(jwks_url)[kid]
    return jwt.decode(token, jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk)), algorithms=[jwk["alg"]])