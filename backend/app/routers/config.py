from fastapi import APIRouter

from app.config import settings
from app.database import check_database_connection
from app.schemas import AppConfigResponse

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=AppConfigResponse)
def get_app_config() -> AppConfigResponse:
    return AppConfigResponse(
        ai_mode="openai" if settings.openai_api_key else "mock",
        mapbox_configured=bool(settings.mapbox_access_token),
        mapbox_token=settings.mapbox_access_token,
        mapbox_style_url=settings.mapbox_style_url,
        database="connected" if check_database_connection() else "disconnected",
    )
