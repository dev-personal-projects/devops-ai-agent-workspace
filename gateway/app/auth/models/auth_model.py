from pydantic import BaseModel, EmailStr
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str



class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProfileResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str

class SignupResponse(BaseModel):
    message: str
    user_id: str
    email: str
    full_name: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict

class ErrorResponse(BaseModel):
    detail: str