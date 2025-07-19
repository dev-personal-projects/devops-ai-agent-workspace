from fastapi import APIRouter, HTTPException, status
from gateway.app.auth.models.auth_model import (
    SignupRequest,
    LoginRequest,
    ProfileResponse,
    SignupResponse,
    LoginResponse,
    ErrorResponse
)
from gateway.app.auth.services.auth_service import signup_user, login_user, get_user_profile

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