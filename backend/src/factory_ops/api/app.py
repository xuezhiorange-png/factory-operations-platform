"""HTTP composition boundary: accepts application factories, never imports infrastructure."""

from collections.abc import Callable
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from factory_ops.api.assets import router as assets_router
from factory_ops.api.auth import router as auth_router
from factory_ops.api.health import router as health_router
from factory_ops.application.assets import AssetQueries
from factory_ops.application.auth import AuthService
from factory_ops.application.errors import ApplicationError


def create_app(
    asset_queries: Callable[[], AssetQueries] | None = None,
    *,
    data_source: Literal["configured_database", "synthetic_test"] = "configured_database",
    auth_service: AuthService | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Factory Operations Platform",
        version="0.2.0",
        description="M1-01: authenticated factory-scoped asset reads; no business write APIs.",
    )
    app.state.asset_queries = asset_queries
    app.state.data_source = data_source
    app.state.auth_service = auth_service

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        if request.url.path.startswith("/api/v1/auth"):
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "invalid_request", "message": "请求参数无效"}},
            )
        return await request_validation_exception_handler(request, error)

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
        if request.url.path.startswith(("/api/v1/factories", "/api/v1/auth", "/api/v1/access")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Vary"] = "Cookie, Authorization"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(assets_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    return app


# Backward-compatible liveness entry. Use factory_ops.bootstrap:app for configured database reads.
app = create_app()
