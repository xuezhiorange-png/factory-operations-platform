"""Only isolated PostgreSQL test schemas and synthetic identities. Never log credentials."""

import hashlib
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from factory_ops.infrastructure.database.models import (
    AssetRow,
    ExternalIdentityRow,
    FactoryAccessRow,
    FactoryRow,
    SessionRow,
    UserRow,
)

BACKEND = Path(__file__).resolve().parents[1]


def test_database_url() -> str:
    value = os.environ.get("FACTORY_OPS_TEST_DATABASE_URL", "")
    url = make_url(value)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"127.0.0.1", "localhost"}
        or url.database != "factory_ops_test"
    ):
        raise RuntimeError(
            "Tests require the dedicated loopback PostgreSQL factory_ops_test database"
        )
    return value


@dataclass(repr=False)
class TestDatabase:
    admin: Engine
    engine: Engine
    schema: str

    def migration(self, direction: str, revision: str) -> None:
        with self.engine.begin() as connection:
            config = Config(str(BACKEND / "alembic.ini"))
            config.attributes["connection"] = connection
            getattr(command, direction)(config, revision)

    def cleanup(self) -> None:
        self.engine.dispose()
        with self.admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        self.admin.dispose()


def isolated_database() -> TestDatabase:
    url = test_database_url()
    schema = "m1_test_" + uuid4().hex
    admin = create_engine(url, echo=False)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"}, echo=False)
    db = TestDatabase(admin, engine, schema)
    try:
        db.migration("upgrade", "head")
    except BaseException:
        db.cleanup()
        raise
    return db


@dataclass
class SyntheticData:
    factories: dict[str, UUID] = field(default_factory=dict)
    users: dict[str, UUID] = field(default_factory=dict)
    assets: dict[str, UUID] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict, repr=False)


def seed_synthetic(engine: Engine) -> SyntheticData:
    data = SyntheticData()
    with Session(engine) as session:
        for key in ["A", "B", "EMPTY"]:
            row = FactoryRow(code="SYNTH-" + key, name="合成测试工厂 " + key)
            session.add(row)
            session.flush()
            data.factories[key] = row.id
        roles = {
            "group": "group_lead",
            "engineer": "engineer",
            "multi": "engineer",
            "admin": "factory_equipment_admin",
            "ungranted": "engineer",
        }
        for key, role in roles.items():
            user = UserRow(role=role)
            session.add(user)
            session.flush()
            data.users[key] = user.id
            token = secrets.token_urlsafe(32)
            session.add(
                SessionRow(
                    user_id=user.id,
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            data.tokens[key] = token
            for factory in (
                ["A", "B"] if key == "multi" else ["A"] if key in {"engineer", "admin"} else []
            ):
                session.add(FactoryAccessRow(user_id=user.id, factory_id=data.factories[factory]))
        for key, factory, code, category, status in [
            ("A", "A", "EQ-001", "processing", "in_use"),
            ("LITERAL", "A", "A%_LITERAL", "utilities", "pending"),
            ("B", "B", "EQ-001", "refrigeration", "inactive"),
        ]:
            row = AssetRow(
                factory_id=data.factories[factory],
                asset_code=code,
                name="SYNTH-设备-" + key,
                category=category,
                location="合成位置-" + factory,
                manufacturer="SYNTH-制造商",
                model="SYNTH-MODEL",
                serial_number=None,
                status=status,
            )
            session.add(row)
            session.flush()
            data.assets[key] = row.id
        session.add(
            ExternalIdentityRow(
                user_id=data.users["engineer"],
                provider="doubao_mcp",
                issuer="synthetic-test-issuer",
                tenant_id="SYNTH-TENANT",
                app_id="SYNTH-APP",
                subject_id="SYNTH-SUBJECT",
            )
        )
        session.flush()
        # Test sessions are issued only after initial grants have settled.
        for row in session.query(SessionRow).all():
            user = session.get(UserRow, row.user_id)
            session.refresh(user)
            row.auth_version = user.auth_version
            row.revoked_at = None
        session.commit()
    return data
