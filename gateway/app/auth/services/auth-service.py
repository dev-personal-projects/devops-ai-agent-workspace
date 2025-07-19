from fastapi import HTTPException
from config import settings


def signup_user(email: str, password: str, full_name: str):
    auth_result = settings.supabase.auth.sign_up({"email": email, "password": password})
    if auth_result.get("error"):
        raise HTTPException(status_code=400, detail=auth_result["error"]["message"])

    user_id = auth_result["user"]["id"]
    profile = {
        "id": user_id,  
        "email": email,
        "full_name": full_name,
        "role": "developer"
    }

    insert_result = settings.supabase.table("profiles").insert(profile).execute()
    if insert_result.get("error"):
        raise HTTPException(status_code=500, detail="Failed to create user profile.")
    
    return {"message": "Signup successful", "user_id": user_id}


def login_user(email: str, password: str):
    result = settings.supabase.auth.sign_in_with_password({"email": email, "password": password})
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"]["message"])
    return result["session"]  # Returns access_token, refresh_token, etc.


def get_user_profile(user_id: str):
    result = settings.supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    if result.get("error"):
        raise HTTPException(status_code=404, detail="Profile not found.")
    return result["data"]
