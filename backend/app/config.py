from pathlib import Path
from typing import Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE = f"sqlite:///{_BACKEND_DIR / 'nestmatch.db'}"
_ENV_FILE = _BACKEND_DIR / ".env"
_DEFAULT_CORS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
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

    jwt_secret: str = "nestmatch-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 168

    cors_origins: list[str] = _DEFAULT_CORS

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, list[str]]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
