
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar

class Settings(BaseSettings):
    PROJECT_NAME: str = "Uptown/District API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 
    
    ADMIN_SECRET_KEY: str = "change-this-admin-secret"

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "12345"
    POSTGRES_DB: str = "uptown_db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql://postgres:12345@localhost:5432/uptown_db"

    # ClassVar is needed because computed_field or validator is preferred in v2, 
    # but for simplicity in BaseSettings we can use a property or post-init if complex.
    # However, pydantic-settings handles env vars automatically. 
    # We can override DATABASE_URL property or set it in .env.
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra="ignore"
    )

    def assemble_db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
settings.DATABASE_URL = settings.assemble_db_url()
