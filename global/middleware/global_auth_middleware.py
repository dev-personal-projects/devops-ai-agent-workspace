"""
Authentication utilities for microservices
Use this in other services that need authentication
"""

from fastapi import Request, HTTPException, Depends
from typing import Optional, Dict, Any
import httpx
import os
import logging

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ServiceAuthenticator:
    """Authentication handler for microservices"""

    def __init__(self, gateway_url: Optional[str] = None):
        self.gateway_url = gateway_url or os.getenv("GATEWAY_URL", "http://localhost:8000")

    async def verify_token_with_gateway(self, token: str) -> Dict[str, Any]:
        """Verify token by calling the gateway service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.gateway_url}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=401,
                        detail="Token verification failed"
                    )
        except httpx.RequestError as e:
            logger.error(f"Gateway communication error: {e}")
            raise HTTPException(
                status_code=503,
                detail="Authentication service unavailable"
            )

    def get_current_user_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get current user from request state (if middleware set it)"""
        return getattr(request.state, 'current_user', None)

    def get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract Bearer token from request headers"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        return auth_header.split(" ")[1]


# Global instance
service_auth = ServiceAuthenticator()


# Dependency functions for FastAPI
async def require_auth(request: Request) -> Dict[str, Any]:
    """
    Dependency that requires authentication
    Use in FastAPI endpoints like: current_user = Depends(require_auth)
    """
    # First try to get user from request state (set by middleware)
    current_user = service_auth.get_current_user_from_request(request)
    if current_user:
        return current_user

    # If not found, try to verify token
    token = service_auth.get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    # Verify with gateway
    user_info = await service_auth.verify_token_with_gateway(token)

    # Set in request state for future use
    request.state.current_user = user_info
    return user_info


def optional_auth(request: Request) -> Optional[Dict[str, Any]]:
    """
    Dependency that makes authentication optional
    Returns None if not authenticated
    """
    try:
        return service_auth.get_current_user_from_request(request)
    except:
        return None


# Middleware for other services
async def auth_middleware_for_service(request: Request, call_next, protected_paths: list = None):
    """
    Reusable authentication middleware for other microservices

    Usage in other services:

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        protected = ["/api/protected", "/api/admin"]
        return await auth_middleware_for_service(request, call_next, protected)
    """
    if protected_paths is None:
        protected_paths = []

    # Check if path needs protection
    needs_auth = any(request.url.path.startswith(path) for path in protected_paths)

    if not needs_auth:
        return await call_next(request)

    # Get token and verify
    token = service_auth.get_token_from_request(request)
    if not token:
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )

    try:
        user_info = await service_auth.verify_token_with_gateway(token)
        request.state.current_user = user_info
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.detail}
        )

    return await call_next(request)