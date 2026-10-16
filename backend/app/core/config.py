
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    # Application configuration
    APP_NAME: str = "IngredientIQ API"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Frontend configuration
    FRONTEND_ORIGINS: list[str] = Field(default_factory=list)

    # Database configuration
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # Gemini AI configuration
    GEMINI_API_KEY: SecretStr | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_TIMEOUT_SECONDS: int = Field(
        default=30,
        ge=1,
        le=120,
    )

    # RAG embedding configuration
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSIONS: int = Field(default=768, ge=1)
    EMBEDDING_TIMEOUT_SECONDS: int = Field(default=30, ge=1, le=120)
    EMBEDDING_MAX_RETRIES: int = Field(default=3, ge=1, le=5)
    CHUNK_MAX_WORDS: int = Field(default=180, ge=30, le=400)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def validate_settings(self):
        if self.APP_ENV == "production" and self.DEBUG:
            raise ValueError(
                "DEBUG must be disabled in production"
            )

        if self.APP_ENV == "production":
            for origin in self.FRONTEND_ORIGINS:
                if not origin.startswith("https://"):
                    raise ValueError(
                        "Production frontend origins must use HTTPS"
                    )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
