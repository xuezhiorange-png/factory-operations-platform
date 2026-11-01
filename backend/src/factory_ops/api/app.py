"""HTTP composition boundary: accepts application factories, never imports infrastructure."""

from collections.abc import Callable
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from factory_ops.api.assets import router as assets_router
from factory_ops.api.health import router as health_router
from factory_ops.application.assets import AssetQueries
from factory_ops.application.errors import ApplicationError


def create_app(
    asset_queries: Callable[[], AssetQueries] | None = None,
    *,
    data_source: Literal["configured_database", "synthetic_test"] = "configured_database",
) -> FastAPI:
    app = FastAPI(
        title="Factory Operations Platform",
        version="0.2.0",
        description="M1-01: authenticated factory-scoped asset reads; no business write APIs.",
    )
    app.state.asset_queries = asset_queries
    app.state.data_source = data_source

    @app.exception_handler(ApplicationError)
    def application_error(request: Request, error: ApplicationError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status == 401 else None
        return JSONResponse(
            status_code=error.status,
            content={
                "error": {
                    "code": error.code,
                    "message": error.message,
                }
            },
            headers=headers,
        )

    @app.middleware("http")
    async def private_response(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1/factories"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Vary"] = "Cookie, Authorization"
        return response

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(assets_router, prefix="/api/v1")
    return app


# Backward-compatible liveness entry. Use factory_ops.bootstrap:app for configured database reads.
app = create_app()
