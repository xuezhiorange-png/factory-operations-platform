"""Composition root. No connection or migration occurs just by importing the application."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from factory_ops.api.app import create_app
from factory_ops.application.assets import AssetQueries
from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork


def configured_app():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return create_app()
    if make_url(url).drivername != "postgresql+psycopg":
        raise ValueError("DATABASE_URL must select PostgreSQL with psycopg")
    engine = create_engine(url, pool_pre_ping=True, echo=False)
    return create_app(lambda: AssetQueries(lambda: SqlReadUnitOfWork(engine)))


app = configured_app()
