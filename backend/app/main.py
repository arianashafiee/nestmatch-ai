from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, check_database_connection, engine
from app.migrate import run_migrations
from app.routers import apartments, auth, commute, config, parse, photos, profile, search

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_STATIC_DIR = _BACKEND_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if check_database_connection():
        Base.metadata.create_all(bind=engine)
        run_migrations()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.3.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(config.router)
app.include_router(apartments.router)
app.include_router(parse.router)
app.include_router(search.router)
app.include_router(commute.router)
app.include_router(photos.router)


@app.get("/api/health")
def health_check() -> dict:
    db_connected = check_database_connection()
    using_sqlite = settings.database_url.startswith("sqlite")
    return {
        "status": "ok",
        "app": settings.app_name,
        "database": "connected" if db_connected else "disconnected",
        "persistence": "ephemeral" if using_sqlite else "postgres",
        "ai": "openai" if settings.openai_api_key else "mock",
        "mapbox": "configured" if settings.mapbox_access_token else "not_configured",
    }


@app.get("/")
def root():
    index_html = _STATIC_DIR / "index.html"
    if index_html.is_file():
        return FileResponse(index_html)
    return {"message": "NestMatch AI API", "docs": "/docs"}


def _mount_frontend(app: FastAPI) -> None:
    if not _STATIC_DIR.is_dir():
        return

    assets_dir = _STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_html = _STATIC_DIR / "index.html"
    if not index_html.is_file():
        return

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def serve_spa(spa_path: str):
        if spa_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        if spa_path in ("docs", "openapi.json", "redoc"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = _STATIC_DIR / spa_path
        if spa_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_html)


_mount_frontend(app)
