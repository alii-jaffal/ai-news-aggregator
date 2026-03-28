from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str

    DIGEST_GEMINI_API_KEY: str
    CURATOR_GEMINI_API_KEY: str
    EMAIL_GEMINI_API_KEY: str

    EMAIL: str
    APP_PASSWORD: str

    PROXY_USERNAME: str | None = None
    PROXY_PASSWORD: str | None = None


settings = Settings()