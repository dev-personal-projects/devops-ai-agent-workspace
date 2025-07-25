from fastapi import HTTPException
from gateway.config import settings
from typing import Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile data class - Clean data representation"""
    id: str
    email: str
    full_name: str
    role: str = "developer"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role
        }


@dataclass
class AuthResult:
    """Authentication result data class"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type
        }
        if self.expires_in:
            result["expires_in"] = self.expires_in
        if self.user:
            result["user"] = self.user
        return result


@dataclass
class SignupResult:
    """Signup result data class"""
    message: str
    user_id: str
    email: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "message": self.message,
            "user_id": self.user_id,
            "email": self.email
        }


class AuthenticationError(Exception):
    """Custom authentication exception"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UserNotFoundError(Exception):
    """Custom user not found exception"""
    def __init__(self, message: str = "User not found"):
        self.message = message
        super().__init__(message)


class DatabaseRepository(ABC):
    """Abstract repository interface - Dependency Inversion Principle"""
    
    @abstractmethod
    def create_user_profile(self, profile: UserProfile) -> bool:
        """Create user profile in database"""
        pass
    
    @abstractmethod
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from database"""
        pass


class AuthProvider(ABC):
    """Abstract authentication provider - Dependency Inversion Principle"""
    
    @abstractmethod
    def sign_up(self, email: str, password: str) -> str:
        """Sign up user and return user ID"""
        pass
    
    @abstractmethod
    def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in user and return auth result"""
        pass


class SupabaseRepository(DatabaseRepository):
    """Supabase database repository implementation"""
    
    def __init__(self):
        self.client = settings.create_supabase_client()
    
    def create_user_profile(self, profile: UserProfile) -> bool:
        """Create user profile in Supabase"""
        try:
            result = self.client.table("profiles").insert(profile.to_dict()).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to create profile: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from Supabase"""
        try:
            result = self.client.table("profiles").select("*").eq("id", user_id).execute()
            
            if not result.data:
                return None
            
            profile_data = result.data[0]
            return UserProfile(
                id=profile_data["id"],
                email=profile_data["email"],
                full_name=profile_data["full_name"],
                role=profile_data.get("role", "developer")
            )
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return None


class SupabaseAuthProvider(AuthProvider):
    """Supabase authentication provider implementation"""
    
    def __init__(self):
        self.client = settings.create_supabase_client()
    
    def sign_up(self, email: str, password: str) -> str:
        """Sign up user with Supabase Auth"""
        try:
            auth_result = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if not auth_result.user:
                raise AuthenticationError("Failed to create user account", 400)
            
            return auth_result.user.id
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            logger.error(f"Signup error: {e}")
            raise AuthenticationError(f"Signup failed: {str(e)}", 500)
    
    def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in user with Supabase Auth"""
        try:
            result = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not result.user or not result.session:
                raise AuthenticationError("Invalid email or password")
            
            return AuthResult(
                access_token=result.session.access_token,
                refresh_token=result.session.refresh_token,
                expires_in=result.session.expires_in,
                user={
                    "id": result.user.id,
                    "email": result.user.email
                }
            )
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            logger.error(f"Login error: {e}")
            raise AuthenticationError("Authentication failed")


class AuthService:
    """Authentication service - Single Responsibility Principle"""
    
    def __init__(self, auth_provider: AuthProvider, db_repository: DatabaseRepository):
        self.auth_provider = auth_provider
        self.db_repository = db_repository
    
    def signup_user(self, email: str, password: str, full_name: str) -> SignupResult:
        """Sign up a new user"""
        try:
            # Create user account
            user_id = self.auth_provider.sign_up(email, password)
            
            # Create user profile
            profile = UserProfile(
                id=user_id,
                email=email,
                full_name=full_name,
                role="developer"
            )
            
            if not self.db_repository.create_user_profile(profile):
                logger.error(f"Failed to create profile for user {user_id}")
                raise HTTPException(status_code=500, detail="Failed to create user profile")
            
            return SignupResult(
                message="Signup successful",
                user_id=user_id,
                email=email
            )
        except AuthenticationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected signup error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def login_user(self, email: str, password: str) -> AuthResult:
        """Log in an existing user"""
        try:
            return self.auth_provider.sign_in(email, password)
        except AuthenticationError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            logger.error(f"Unexpected login error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile by ID"""
        try:
            profile = self.db_repository.get_user_profile(user_id)
            
            if not profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            return profile
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting profile: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


# Factory function for creating auth service - Factory Pattern
def create_auth_service() -> AuthService:
    """Create auth service with default implementations"""
    auth_provider = SupabaseAuthProvider()
    db_repository = SupabaseRepository()
    return AuthService(auth_provider, db_repository)


# Global auth service instance
auth_service = create_auth_service()


# Public API functions (for backward compatibility)
def signup_user(email: str, password: str, full_name: str) -> Dict[str, Any]:
    """Sign up a new user - Public API"""
    result = auth_service.signup_user(email, password, full_name)
    return result.to_dict()


def login_user(email: str, password: str) -> Dict[str, Any]:
    """Log in an existing user - Public API"""
    result = auth_service.login_user(email, password)
    return result.to_dict()


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile by ID - Public API"""
    profile = auth_service.get_user_profile(user_id)
    return profile.to_dict()