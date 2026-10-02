from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./governance.db"
    jwt_secret: str
    jwt_expiry_minutes: int = 60
    cors_origins: str = "http://localhost:5174,http://localhost:3010"
    bootstrap_password: str
    data_root: Path = Path(__file__).resolve().parents[3] / "data"
    openlineage_url: str = "http://localhost:8010/api/lineage/events"
    marquez_url: str = ""

    @field_validator("jwt_secret")
    @classmethod
    def secret_length(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value

    @field_validator("bootstrap_password")
    @classmethod
    def password_length(cls, value: str) -> str:
        if len(value) < 12:
            raise ValueError("BOOTSTRAP_PASSWORD must contain at least 12 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
