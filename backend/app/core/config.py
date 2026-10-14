
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
