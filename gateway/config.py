from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from supabase import create_client, Client
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_env_file() -> str:
    """Find .env file in project root"""
    current_dir = Path(__file__).resolve().parent
    while current_dir != current_dir.parent:
        env_file = current_dir / ".env"
        if env_file.exists():
            logger.info(f"Found .env file at: {env_file}")
            return str(env_file)
        current_dir = current_dir.parent
    logger.warning("No .env file found, using default")
    return ".env"


class Settings(BaseSettings):
    """Clean, simple settings following SOLID principles"""
    
    # Application metadata
    project_name: str = Field(default="DevOps AI Agent", alias="PROJECT_NAME")
    project_description: str = Field(default="DevOps AI Agent with FastAPI", alias="PROJECT_DESCRIPTION")
    version: str = Field(default="0.1.0", alias="VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # CORS settings
    allowed_origins: List[str] = Field(default=["*"], alias="ALLOWED_ORIGINS")
    
    # Database settings
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_key: str = Field(alias="SUPABASE_KEY")
    
    # Azure settings
    azure_ai_foundry_endpoint: str = Field(alias="AZURE_AI_FOUNDRY_ENDPOINT")
    azure_ai_foundry_api_key: str = Field(alias="AZURE_AI_FOUNDRY_API_KEY")
    azure_ai_foundry_deployment_name: str = Field(default="gpt-4-mini", alias="AZURE_AI_FOUNDRY_DEPLOYMENT_NAME")
    azure_ai_foundry_api_version: str = Field(default="2024-10-01-preview", alias="AZURE_AI_FOUNDRY_API_VERSION")
    azure_monitor_connection_string: str = Field(alias="AZURE_MONITOR_CONNECTION_STRING")
    
    # Redis settings
    azure_redis_connection_string: str = Field(default="", alias="AZURE_REDIS_CONNECTION_STRING")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    
    # Security
    jwt_secret: str = Field(alias="JWT_SECRET")
    
    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        extra="ignore",
        case_sensitive=False,
    )
    
    @computed_field
    @property
    def redis_url(self) -> str:
        """Build Redis URL from Azure connection string"""
        if not self.azure_redis_connection_string:
            return "redis://localhost:6379/0"
            
        try:
            # Parse Azure connection string format:
            # "hostname.redis.cache.windows.net:6380,password=xxx,ssl=True"
            parts = self.azure_redis_connection_string.split(",")
            host_port = parts[0]  # hostname:port
            password = ""
            ssl = False
            
            for part in parts[1:]:
                if part.startswith("password="):
                    password = part.split("=", 1)[1]
                elif part.startswith("ssl="):
                    ssl = part.split("=", 1)[1].lower() == "true"
            
            protocol = "rediss" if ssl else "redis"
            auth_part = f":{password}@" if password else ""
            return f"{protocol}://{auth_part}{host_port}/{self.redis_db}"
        except Exception as e:
            logger.error(f"Failed to parse Redis connection string: {e}")
            return "redis://localhost:6379/0"
    
    @computed_field
    @property
    def celery_broker_url(self) -> str:
        """Celery broker URL"""
        return self.redis_url
        
    @computed_field
    @property
    def celery_result_backend(self) -> str:
        """Celery result backend URL"""
        return self.redis_url
    
    # Legacy compatibility properties for existing code
    @property
    def CELERY_BROKER_URL(self) -> str:
        """Legacy compatibility for Celery broker URL"""
        return self.celery_broker_url
        
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Legacy compatibility for Celery result backend URL"""
        return self.celery_result_backend
    
    @property
    def DEBUG(self) -> bool:
        """Legacy compatibility for debug flag"""
        return self.debug
    
    @property
    def AZURE_MONITOR_CONNECTION_STRING(self) -> str:
        """Legacy compatibility for Azure Monitor connection string"""
        return self.azure_monitor_connection_string
    
    def create_supabase_client(self) -> Client:
        """Create Supabase client"""
        try:
            return create_client(self.supabase_url, self.supabase_key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {str(e)}")
            raise e


# Create settings instance
settings = Settings()