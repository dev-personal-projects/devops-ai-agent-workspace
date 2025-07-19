import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from fastapi import Request, HTTPException, status, Depends
from gateway.config import settings
from gateway.app.auth.models.auth_model import ProfileResponse

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()

async def auth_required(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> ProfileResponse:
    """
    FastAPI dependency that:
    1. Extracts Bearer token
    2. Verifies it with Supabase
    3. Fetches the user's profile
    4. Stores ProfileResponse in request.state.current_user
    """
    token = credentials.credentials
    supabase: Client = settings.supabase

    # 1️⃣ Verify token with Supabase Auth
    try:
        user_response = supabase.auth.get_user(token)
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Check if user_response has error attribute or user is None
    # Handle both Pydantic model and dict responses
    if hasattr(user_response, 'user'):
        # Pydantic model response
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed - no user found",
            )
        user = user_response.user
    elif isinstance(user_response, dict):
        # Dictionary response (fallback)
        if user_response.get("error") or not user_response.get("data", {}).get("user"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
            )
        user = user_response["data"]["user"]
    else:
        # Unknown response type
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed - unexpected response format",
        )

    # 2️⃣ Load full profile from 'profiles' table
    try:
        profile_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user.id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user profile",
        )

    # Handle profile response (this might also be a Pydantic model)
    if hasattr(profile_resp, 'data') and profile_resp.data:
        profile_data = profile_resp.data
    elif isinstance(profile_resp, dict) and profile_resp.get("data"):
        profile_data = profile_resp["data"]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    # 3️⃣ Create ProfileResponse
    try:
        current_user = ProfileResponse(
            id=profile_data["id"],
            email=profile_data["email"],
            full_name=profile_data["full_name"],
            role=profile_data["role"],
        )
    except KeyError as e:
        logger.error(f"Missing profile field: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile data incomplete: missing {e}",
        )

    # 4️⃣ Attach to request.state for direct access in handlers
    request.state.current_user = current_user
    return current_user