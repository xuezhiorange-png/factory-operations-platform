"""Composition root. No connection or migration occurs just by importing the application."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from factory_ops.api.app import create_app
from factory_ops.application.assets import AssetQueries
from factory_ops.application.auth import AuthService, AuthSettings
from factory_ops.infrastructure.database.auth import SqlAuthUnitOfWork
from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork
from factory_ops.infrastructure.identity.feishu import FeishuConfig, FeishuIdentityProvider


def configured_app():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return create_app()
    if make_url(url).drivername != "postgresql+psycopg":
        raise ValueError("DATABASE_URL must select PostgreSQL with psycopg")
    engine = create_engine(url, pool_pre_ping=True, echo=False)
    origin = os.environ.get("FACTORY_OPS_PUBLIC_ORIGIN")
    auth = None
    if origin:
        settings = AuthSettings(origin, os.environ.get("FEISHU_APP_ID", ""))
        secret, tenant = os.environ.get("FEISHU_APP_SECRET"), os.environ.get("FEISHU_TENANT_KEY")
        provider = (
            FeishuIdentityProvider(FeishuConfig(settings.app_id, tenant, settings.callback, secret))
            if settings.app_id and secret and tenant
            else None
        )
        auth = AuthService(lambda: SqlAuthUnitOfWork(engine), settings, provider)
    return create_app(lambda: AssetQueries(lambda: SqlReadUnitOfWork(engine)), auth_service=auth)


app = configured_app()
