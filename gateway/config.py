from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    PROJECT_NAME: str = "DevOps AI Agent"
    PROJECT_DESCRIPTION: str = "DevOps AI Agent with FastAPI"
    VERSION: str = "0.1.0"

    ALLOWED_ORIGINS: List[str] = ["*"]

    # Using Field aliases if your .env uses lowercase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    # Azure AI Foundry Configuration
    AZURE_AI_FOUNDRY_ENDPOINT: str
    AZURE_AI_FOUNDRY_API_KEY: str
    AZURE_AI_FOUNDRY_DEPLOYMENT_NAME: str = "gpt-o4-mini"
    AZURE_AI_FOUNDRY_API_VERSION : str = "2024-10-01-preview"
    # Azure Monitor Configuration
    AZURE_MONITOR_CONNECTION_STRING: str
    # JWT Secret
    JWT_SECRET: str 
    # Debug mode
    DEBUG: bool = False


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def supabase(self) -> Client:
        try:
            return create_client(self.SUPABASE_URL, self.SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {str(e)}")
            raise e


settings = Settings()