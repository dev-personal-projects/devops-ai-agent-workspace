from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from supabase import create_client, Client

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevOps AI Agent"
    PROJECT_DESCRIPTION: str = "DevOps AI Agent with FastAPI"
    VERSION: str = "0.1.0"

    ALLOWED_ORIGINS: List[str] = ["*"]
    SUPABASE_URL: str
    SUPABASE_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        case_sensitive=False
    )

    @property
    def supabase(self) -> Client:
        return create_client(self.SUPABASE_URL, self.SUPABASE_KEY)

settings = Settings()
