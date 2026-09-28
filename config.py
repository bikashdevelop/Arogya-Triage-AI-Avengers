from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration loader.
    Reads values from the .env file in the same directory.
    Falls back to sensible defaults if a value is missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── LLM ──
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TIMEOUT_SECONDS: int = 20

    # ── Security ──
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "internal"
    LOG_LEVEL: str = "INFO"

    # ── Database ──
    DATABASE_URL: str = "sqlite:///./triage.db"


settings = Settings()