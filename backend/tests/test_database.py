"""Reversible PostgreSQL migrations, real constraints and append-only audit."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from db_support import BACKEND
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from factory_ops.infrastructure.database.models import AssetRow, UserRow


def test_upgrade_downgrade_repeat_and_metadata_match(db):
    required = {
        "factories",
        "users",
        "user_factory_access",
        "assets",
        "external_identities",
        "auth_sessions",
        "audit_events",
    }
    assert required <= set(inspect(db.engine).get_table_names())
    with db.engine.begin() as connection:
        config = Config(str(BACKEND / "alembic.ini"))
        config.attributes["connection"] = connection
        command.check(config)
    for _ in range(2):
        db.migration("downgrade", "base")
        assert not required & set(inspect(db.engine).get_table_names())
        db.migration("upgrade", "head")
        assert required <= set(inspect(db.engine).get_table_names())


def test_constraints_reject_invalid_role_duplicate_code_and_unknown_factory(business):
    _, data, db = business
    with Session(db.engine) as session:
        session.add(UserRow(role="fourth_manager"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(
            AssetRow(
                factory_id=data.factories["A"],
                asset_code="EQ-001",
                name="duplicate",
                category="other",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.add(
            AssetRow(factory_id=uuid4(), asset_code="NEW", name="synthetic", category="other")
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        assert session.get(UserRow, data.users["engineer"]) is not None


def test_audit_cannot_be_updated_or_deleted(business):
    http, data, db = business
    http.get("/api/v1/factories", headers={"Authorization": "Bearer " + data.tokens["engineer"]})
    for statement in ["UPDATE audit_events SET outcome='denied'", "DELETE FROM audit_events"]:
        with db.engine.connect() as connection:
            with pytest.raises(DBAPIError):
                connection.execute(text(statement))
            connection.rollback()


def test_failed_migration_rolls_back_partial_ddl_and_can_be_retried(db):
    db.migration("downgrade", "base")
    with db.engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id integer PRIMARY KEY)"))
    with pytest.raises(DBAPIError):
        db.migration("upgrade", "head")
    assert "factories" not in inspect(db.engine).get_table_names()
    with db.engine.begin() as connection:
        connection.execute(text("DROP TABLE users"))
    db.migration("upgrade", "head")
    assert "assets" in inspect(db.engine).get_table_names()
