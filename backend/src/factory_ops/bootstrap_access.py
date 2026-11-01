"""Explicit offline first-lead initialization, never exposed/imported by the web application."""

import argparse
import os
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from factory_ops.application.access import AccessService
from factory_ops.application.errors import ApplicationError
from factory_ops.infrastructure.database.access import SqlAccessUnitOfWork


def main():
    parser = argparse.ArgumentParser(
        description="Promote an existing verified pending account once"
    )
    parser.add_argument("user_id", type=UUID)
    parser.add_argument("--expected-version", required=True, type=int)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--confirm-first-group-lead", required=True, action="store_true")
    args = parser.parse_args()
    if os.environ.get("FACTORY_OPS_ALLOW_OFFLINE_BOOTSTRAP") != "1":
        parser.exit(2, "Offline bootstrap must be explicitly enabled by the database operator.\n")
    url, app, tenant = (
        os.environ.get(key) for key in ("DATABASE_URL", "FEISHU_APP_ID", "FEISHU_TENANT_KEY")
    )
    try:
        valid_url = bool(url) and make_url(url).drivername == "postgresql+psycopg"
    except (ValueError, SQLAlchemyError):
        valid_url = False
    if not valid_url or not app or not tenant:
        parser.exit(
            2, "Dedicated PostgreSQL and trusted Feishu app/tenant configuration required.\n"
        )
    engine = None
    try:
        engine = create_engine(url, echo=False)
        AccessService(lambda: SqlAccessUnitOfWork(engine)).bootstrap(
            args.user_id, args.expected_version, args.reason, app, tenant
        )
    except (ApplicationError, SQLAlchemyError):
        parser.exit(
            1, "Bootstrap rejected; verify account state and consult protected audit records.\n"
        )
    finally:
        if engine is not None:
            engine.dispose()
    print("First group lead initialized. Reauthenticate; no credentials are printed.")


if __name__ == "__main__":
    main()
