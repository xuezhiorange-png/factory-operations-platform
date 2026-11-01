"""M0 API test fixtures."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from factory_ops.api.app import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
