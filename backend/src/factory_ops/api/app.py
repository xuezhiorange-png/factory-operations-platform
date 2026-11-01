"""FastAPI app factory. M0 exposes only a public liveness endpoint."""

from fastapi import FastAPI

from factory_ops.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Factory Operations Platform",
        version="0.1.0",
        description="M0 engineering skeleton: no business or production data API implemented.",
    )
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()
