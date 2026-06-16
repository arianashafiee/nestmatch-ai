from urllib.parse import quote

from typing import Optional, Tuple

import httpx
from fastapi import APIRouter
from openai import OpenAI

from app.config import _ENV_FILE, settings
from app.database import check_database_connection
from app.schemas import AppConfigResponse

router = APIRouter(prefix="/api", tags=["config"])


def _check_openai_key() -> Tuple[bool, Optional[str]]:
    if not settings.openai_api_key:
        return False, "OPENAI_API_KEY not set in backend/.env"
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": "Reply with OK"}],
            max_tokens=5,
        )
        if response.choices[0].message.content:
            return True, None
        return False, "OpenAI returned an empty response"
    except Exception as exc:
        return False, str(exc)


def _check_mapbox_token() -> Tuple[bool, Optional[str]]:
    if not settings.mapbox_access_token:
        return False, "MAPBOX_ACCESS_TOKEN not set in backend/.env"
    try:
        url = (
            "https://api.mapbox.com/geocoding/v5/mapbox.places/"
            f"{quote('Baltimore, MD')}.json"
        )
        response = httpx.get(
            url,
            params={"access_token": settings.mapbox_access_token, "limit": 1},
            timeout=10,
        )
        if response.status_code == 200 and response.json().get("features"):
            return True, None
        return False, f"Mapbox geocoding returned {response.status_code}"
    except Exception as exc:
        return False, str(exc)


@router.get("/config", response_model=AppConfigResponse)
def get_app_config() -> AppConfigResponse:
    return AppConfigResponse(
        ai_mode="openai" if settings.openai_api_key else "mock",
        mapbox_configured=bool(settings.mapbox_access_token),
        mapbox_token=settings.mapbox_access_token,
        mapbox_style_url=settings.mapbox_style_url,
        database="connected" if check_database_connection() else "disconnected",
    )


@router.get("/config/validate")
def validate_app_config() -> dict:
    openai_ok, openai_error = _check_openai_key()
    mapbox_ok, mapbox_error = _check_mapbox_token()
    return {
        "openai_configured": bool(settings.openai_api_key),
        "openai_working": openai_ok,
        "openai_error": openai_error,
        "mapbox_configured": bool(settings.mapbox_access_token),
        "mapbox_working": mapbox_ok,
        "mapbox_error": mapbox_error,
        "env_file": str(_ENV_FILE),
    }
