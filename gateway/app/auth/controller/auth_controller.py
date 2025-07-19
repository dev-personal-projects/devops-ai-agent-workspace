from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends

from gateway.app.auth.models.auth_model import (
    SignupRequest,
    LoginRequest,
    ProfileResponse,
    SignupResponse,
    LoginResponse,
    ErrorResponse
)
from gateway.app.auth.services.auth_service import signup_user, login_user, get_user_profile
from gateway.app.auth.middleware.auth_middleware import  auth_required

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup",
            response_model=SignupResponse,
            status_code=status.HTTP_201_CREATED,
            responses={
                400: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            })
def signup(payload: SignupRequest):
    """
    Create a new user account
    """
    return signup_user(payload.email, payload.password, payload.full_name)

@router.post("/login",
            response_model=LoginResponse,
            responses={
                401: {"model": ErrorResponse}
            })
def login(payload: LoginRequest):
    """
    Authenticate user and return access tokens
    """
    return login_user(payload.email, payload.password)

@router.get("/profile/{user_id}",
           response_model=ProfileResponse,
           responses={
               404: {"model": ErrorResponse},
               500: {"model": ErrorResponse}
           })
def get_profile(user_id: str):
    """
    Get user profile information
    """
    return get_user_profile(user_id)

# Apply authentication middleware to all routes in this router
@router.get("/info")
def protected_info(current_user = Depends(auth_required)):
    # current_user is a ProfileResponse
    return {
        "message": f"Welcome back, {current_user.full_name}!",
        "role": current_user.role
    }