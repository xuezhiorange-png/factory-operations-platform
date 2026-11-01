"""Run explicit PostgreSQL migrations; connection settings come from env, not the repository."""

import os

from alembic import context
from sqlalchemy import create_engine, pool

from factory_ops.infrastructure.database.models import Base

config = context.config


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


connection = config.attributes.get("connection")
if connection is not None:
    run(connection)
else:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required; no default database is selected")
    engine = create_engine(url, poolclass=pool.NullPool, echo=False)
    with engine.connect() as connection:
        run(connection)
    engine.dispose()
