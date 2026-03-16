from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import install_http_middleware
from app.web.routes import web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    install_http_middleware(application, settings)
    application.mount(
        "/static",
        StaticFiles(directory=Path(__file__).resolve().parent / "web" / "static"),
        name="static",
    )
    application.include_router(web_router)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
