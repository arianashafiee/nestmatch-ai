from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE = f"sqlite:///{_BACKEND_DIR / 'nestmatch.db'}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NestMatch AI"
    debug: bool = True

    database_url: str = _DEFAULT_SQLITE

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    mapbox_access_token: Optional[str] = None
    mapbox_style_url: str = "mapbox://styles/mapbox/streets-v12"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]


settings = Settings()
