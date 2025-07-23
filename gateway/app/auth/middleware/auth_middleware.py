from __future__ import annotations

import logging
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from gateway.core.exceptions import AppException
from gateway.core.security import verify_token
from gateway.app.auth.models.auth_model import ProfileResponse
from gateway.config import settings

_log = logging.getLogger(__name__)
_bearer = HTTPBearer()

async def auth_required(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> ProfileResponse:
    """
    • Parse Bearer token
    • Verify JWT locally **first** (fast path)
    • Fallback to Supabase verification (legacy)
    • Load profile row
    • Attach ProfileResponse to request.state.current_user
    """
    token: str = creds.credentials
    supabase: Client = settings.supabase

    # ── 1. local-JWT fast path ───────────────────────────────────────────
    try:
        claims = verify_token(token)  # may raise AppException
        user_id = claims["sub"]
    except AppException as e:
        _log.warning(f"Local JWT verification failed: {e}")
        # not one of **our** tokens → fall-through to Supabase
        try:
            user_resp = supabase.auth.get_user(token)
            if not user_resp.user:
                raise ValueError("Supabase rejected token")
            user_id = user_resp.user.id
        except Exception as exc:
            _log.warning(f"Supabase verification failed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

    # ── 2. profile fetch ────────────────────────────────────────────────
    try:
        profile_q = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_q.data if hasattr(profile_q, "data") else profile_q.get("data")
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        current_user = ProfileResponse(**profile)
        request.state.current_user = current_user
        return current_user
    except Exception as exc:
        _log.error(f"Failed to fetch user profile: {exc}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from exc