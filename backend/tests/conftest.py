"""M0 API test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from test_doubao_jwt import jwt_identity as signed_identity  # noqa: F401

from factory_ops.api.app import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def db():
    import os

    from db_support import isolated_database

    if not os.environ.get("FACTORY_OPS_TEST_DATABASE_URL"):
        pytest.skip("Requires dedicated loopback PostgreSQL test database; mandatory in CI")
    database = isolated_database()
    try:
        yield database
    finally:
        database.cleanup()


@pytest.fixture
def business(db):
    from db_support import seed_synthetic

    from factory_ops.application.assets import AssetQueries
    from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork

    data = seed_synthetic(db.engine)
    application = create_app(
        lambda: AssetQueries(lambda: SqlReadUnitOfWork(db.engine)), data_source="synthetic_test"
    )
    with TestClient(application) as http:
        yield http, data, db
