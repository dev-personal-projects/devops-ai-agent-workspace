from fastapi import HTTPException
from gateway.config import settings
import logging
from gateway.app.auth.proto.grpc_client import  auth_event_client

logger = logging.getLogger(__name__)


def signup_user(email: str, password: str, full_name: str):
    try:
        # Sign up the user with Supabase Auth
        auth_result = settings.supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        # Check if signup was successful
        if not auth_result.user:
            raise HTTPException(status_code=400, detail="Failed to create user account")

        user_id = auth_result.user.id

        # Create user profile in profiles table
        profile_data = {
            "id": user_id,
            "email": email,
            "full_name": full_name,
            "role": "developer"
        }

        profile_result = settings.supabase.table("profiles").insert(profile_data).execute()

        # Check if profile creation was successful
        if not profile_result.data:
            logger.error(f"Failed to create profile for user {user_id}")
            raise HTTPException(status_code=500, detail="Failed to create user profile")

        # Emit signup event via gRPC (fire-and-forget)
        try:
            event_response = auth_event_client.emit_signup_event(
                user_id=user_id,
                email=email,
                full_name=full_name,
                role="developer"
            )
            if event_response and event_response.get("success"):
                logger.info(f"Signup event successfully emitted for user {user_id}")
            else:
                logger.warning(f"Signup event emission failed for user {user_id}")
        except Exception as e:
            # Don't fail the signup if event emission fails
            logger.error(f"Failed to emit signup event: {str(e)}")

        return {
            "message": "Signup successful",
            "user_id": user_id,
            "email": email
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


def login_user(email: str, password: str):
    try:
        # Sign in with email and password
        result = settings.supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        # Check if login was successful
        if not result.user or not result.session:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Emit login event via gRPC (fire-and-forget)
        try:
            event_response = auth_event_client.emit_login_event(
                user_id=result.user.id,
                email=result.user.email,
                token=result.session.access_token
            )
            if event_response and event_response.get("success"):
                logger.info(f"Login event successfully emitted for user {result.user.id}")
            else:
                logger.warning(f"Login event emission failed for user {result.user.id}")
        except Exception as e:
            # Don't fail the login if event emission fails
            logger.error(f"Failed to emit login event: {str(e)}")

        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
            "token_type": "bearer",
            "expires_in": result.session.expires_in,
            "user": {
                "id": result.user.id,
                "email": result.user.email
            }
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def get_user_profile(user_id: str):
    try:
        # Get user profile from profiles table
        result = settings.supabase.table("profiles").select("*").eq("id", user_id).execute()

        # Check if profile was found
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="User profile not found")

        profile = result.data[0]
        return {
            "id": profile["id"],
            "email": profile["email"],
            "full_name": profile["full_name"],
            "role": profile["role"]
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user profile")