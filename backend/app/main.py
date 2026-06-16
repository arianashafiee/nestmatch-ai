from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, check_database_connection, engine
from app.migrate import run_migrations
from app.routers import apartments, config, parse, photos, profile, search


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

app.include_router(profile.router)
app.include_router(config.router)
app.include_router(apartments.router)
app.include_router(parse.router)
app.include_router(search.router)
app.include_router(photos.router)


@app.get("/api/health")
def health_check() -> dict:
    db_connected = check_database_connection()
    return {
        "status": "ok",
        "app": settings.app_name,
        "database": "connected" if db_connected else "disconnected",
        "ai": "openai" if settings.openai_api_key else "mock",
        "mapbox": "configured" if settings.mapbox_access_token else "not_configured",
    }


@app.get("/")
def root() -> dict:
    return {"message": "NestMatch AI API", "docs": "/docs"}
