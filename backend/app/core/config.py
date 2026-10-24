
from functools import lru_cache
from ipaddress import ip_network
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application configuration
    APP_NAME: str = "IngredientIQ API"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Frontend configuration
    FRONTEND_ORIGINS: list[str] = Field(default_factory=list)

    # API abuse protection
    API_REQUESTS_PER_MINUTE: int = Field(default=10, ge=1)
    API_DAILY_ANALYSES_PER_IP: int = Field(default=5, ge=1)
    API_DAILY_SUBMISSIONS_PER_IP: int = Field(default=100, ge=1)
    API_DAILY_IMAGE_EXTRACTIONS_PER_IP: int = Field(default=10, ge=1)
    API_LIMIT_HASH_SECRET: SecretStr | None = None
    TRUSTED_PROXY_IPS: list[str] = Field(default_factory=list)

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
    EMBEDDING_RETRY_BASE_SECONDS: float = Field(default=2.0, ge=0.1, le=30.0)
    CHUNK_MAX_WORDS: int = Field(default=180, ge=30, le=400)
    # RAG retrieval configuration
    RETRIEVAL_TOP_K: int = Field(default=5, ge=1, le=20)
    RETRIEVAL_MIN_SIMILARITY: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
    )
    RETRIEVAL_CANDIDATE_MULTIPLIER: int = Field(
        default=4,
        ge=1,
        le=10,
    )

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
            if (
                self.API_LIMIT_HASH_SECRET is None
                or len(
                    self.API_LIMIT_HASH_SECRET.get_secret_value().strip()
                ) < 32
            ):
                raise ValueError(
                    "API_LIMIT_HASH_SECRET must contain at least 32 "
                    "characters in production"
                )

            for origin in self.FRONTEND_ORIGINS:
                if not origin.startswith("https://"):
                    raise ValueError(
                        "Production frontend origins must use HTTPS"
                    )

        for proxy_ip in self.TRUSTED_PROXY_IPS:
            try:
                ip_network(proxy_ip, strict=False)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid trusted proxy IP or network: {proxy_ip}"
                ) from exc

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
