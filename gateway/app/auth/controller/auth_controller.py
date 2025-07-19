from fastapi import APIRouter
from gateway.app.auth.services import signup_user, login_user, get_user_profile
from gateway.app.auth.models import SignupRequest, LoginRequest, ProfileResponse
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup")
def signup(payload: SignupRequest):
    return signup_user(payload.email, payload.password, payload.full_name)


@router.post("/login")
def login(payload: LoginRequest):
    session = login_user(payload.email, payload.password)
    return {"access_token": session["access_token"], "refresh_token": session["refresh_token"]}


@router.get("/profile/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: str):
    return get_user_profile(user_id)