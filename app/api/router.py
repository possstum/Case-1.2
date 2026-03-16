from fastapi import APIRouter

from app.api.routes.artists import router as artists_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.releases import router as releases_router
from app.api.routes.search import router as search_router
from app.api.routes.sync import router as sync_router
from app.api.routes.tracks import router as tracks_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(search_router, tags=["search"])
api_router.include_router(artists_router, tags=["artists"])
api_router.include_router(releases_router, tags=["releases"])
api_router.include_router(tracks_router, tags=["tracks"])
api_router.include_router(sync_router, tags=["sync"])
api_router.include_router(jobs_router, tags=["jobs"])
