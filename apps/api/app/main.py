"""Main FastAPI application factory and entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager handling startup and shutdown events."""
    setup_logging()
    logger.info(
        "Starting %s v%s in %s mode",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
    logger.info("SSRF Protection enforced: %s", settings.ENFORCE_SSRF_PROTECTION)
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """Builds and configures the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Evidence-based Technical SEO Diagnosis and Code Resolution Platform API",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Domain exception handler
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("Application domain error: %s (code: %s)", exc.message, exc.code)
        return JSONResponse(
            status_code=400,
            content={"code": exc.code, "message": exc.message, "details": exc.details},
        )

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
