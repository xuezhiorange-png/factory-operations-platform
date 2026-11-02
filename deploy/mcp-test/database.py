"""Isolated-stack operations, not imported by the application or exposed over HTTP/MCP."""

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from alembic import command
from alembic.config import Config
from factory_ops.infrastructure.database.models import AssetRow, FactoryRow
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session

GRANTS = [
    (
        "GRANT SELECT ON factories, assets, users, user_factory_access, external_identities "
        "TO factory_ops_runtime"
    ),
    "GRANT INSERT ON audit_events TO factory_ops_runtime",
    (
        "GRANT SELECT ON factories, assets, users, user_factory_access, external_identities "
        "TO factory_ops_operator"
    ),
    "GRANT INSERT, UPDATE ON users, external_identities TO factory_ops_operator",
    "GRANT INSERT, DELETE ON user_factory_access TO factory_ops_operator",
    (
        "GRANT SELECT (user_id, revoked_at), UPDATE (revoked_at) ON auth_sessions "
        "TO factory_ops_operator"
    ),
    "GRANT INSERT ON audit_events TO factory_ops_operator",
]


def guarded_engine():
    url = os.environ.get("DATABASE_URL", "")
    if make_url(url).database != "factory_ops_mcp_synthetic":
        raise ValueError
    engine = create_engine(url, echo=False)
    with engine.connect() as conn:
        marker = conn.scalar(
            text(
                "SELECT shobj_description(oid, 'pg_database') "
                "FROM pg_database WHERE datname=current_database()"
            )
        )
        if marker != "FACTORY_OPS_M1_03B_SYNTHETIC_ONLY":
            raise ValueError
    return engine


def migrate(engine):
    config = Config("/app/backend/alembic.ini")
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
        for grant in GRANTS:
            conn.execute(text(grant))
    return {"migration": "0003_access_lifecycle", "grants": "applied"}


def seed(engine):
    # This command only seeds an EMPTY, explicitly marked, synthetic-only database.
    with Session(engine) as session:
        for table in ("factories", "assets", "users"):
            if session.scalar(text(f"SELECT count(*) FROM {table}")):
                raise ValueError
        result = {"factories": {}, "assets": {}}
        for suffix in ("A", "B"):
            factory_id, asset_id = uuid4(), uuid4()
            session.add(
                FactoryRow(
                    id=factory_id,
                    code="SYNTH-MCP-" + suffix,
                    name="合成加工厂 " + suffix,
                )
            )
            session.flush()
            session.add(
                AssetRow(
                    id=asset_id,
                    factory_id=factory_id,
                    asset_code="SYNTH-EQ-001",
                    name="合成设备 " + suffix,
                    category="processing",
                    location="SYNTH-LOCATION",
                    manufacturer="SYNTH-MAKER",
                    model="SYNTH-MODEL",
                    serial_number=None,
                    status="in_use",
                )
            )
            result["factories"][suffix] = str(factory_id)
            result["assets"][suffix] = str(asset_id)
        session.commit()
        return result


def verify_privileges(engine):
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT current_user")) == "factory_ops_runtime"
        assert conn.scalar(text("SHOW statement_timeout")) == "5s"
        read_tables = {
            "factories",
            "assets",
            "users",
            "user_factory_access",
            "external_identities",
        }
        for table in (
            *read_tables,
            "auth_sessions",
            "oauth_flows",
            "audit_events",
            "alembic_version",
        ):
            for privilege in (
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "TRUNCATE",
                "REFERENCES",
                "TRIGGER",
            ):
                allowed = (
                    privilege == "SELECT"
                    and table in read_tables
                    or privilege == "INSERT"
                    and table == "audit_events"
                )
                actual = conn.scalar(
                    text(
                        "SELECT has_table_privilege(current_user, :table, :privilege)"
                    ),
                    {"table": table, "privilege": privilege},
                )
                assert actual == allowed
        for sql in [
            "SELECT * FROM auth_sessions",
            "SELECT * FROM oauth_flows",
            "SELECT * FROM audit_events",
            "CREATE TABLE forbidden_probe(x int)",
            "UPDATE assets SET name='SYNTH-FORBIDDEN'",
            "DELETE FROM factories",
            "UPDATE users SET role='group_lead'",
            "DELETE FROM audit_events",
            "UPDATE audit_events SET outcome='allowed'",
            "TRUNCATE assets",
            "SET ROLE factory_ops_operator",
            "SET ROLE factory_ops_migrator",
        ]:
            try:
                with conn.begin_nested():
                    conn.execute(text(sql))
                    # Roll back even if a bad configuration incorrectly allows a write.
                    raise AssertionError(
                        "Runtime database privilege exceeds the allowlist"
                    )
            except DBAPIError as exc:
                if getattr(exc.orig, "sqlstate", None) != "42501":
                    raise ValueError from None
        assert conn.scalar(text("SELECT count(*) FROM factories")) == 2
    return {"runtime_privileges": "PASS", "denied_operations": 12}


def untrusted_proxy():
    # A different container on the gateway network is NOT an authorized forwarding proxy.
    token = Path("/run/identities/lead.jwt").read_text().strip()
    settings = json.loads(Path("/run/identities/public-settings.json").read_text())
    with httpx.Client(trust_env=False) as http:
        response = http.post(
            "http://api:8000/mcp",
            headers={
                "Host": settings["authority"],
                "X-Forwarded-Proto": "https",
                "x-aily-jwt": token,
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
    assert response.status_code == 403
    return {"untrusted_forwarded_headers": "PASS", "status": 403}


def main():
    engine = None
    try:
        operation = sys.argv[1]
        if operation == "untrusted-proxy":
            result = untrusted_proxy()
        else:
            engine = guarded_engine()
            if operation == "migrate":
                result = migrate(engine)
            elif operation == "seed" and sys.argv[2:] == ["--confirm-synthetic-only"]:
                result = seed(engine)
            elif operation == "privileges":
                result = verify_privileges(engine)
            elif operation in {"audit-off", "audit-on"}:
                grant = (
                    "REVOKE INSERT ON audit_events FROM factory_ops_runtime"
                    if operation == "audit-off"
                    else "GRANT INSERT ON audit_events TO factory_ops_runtime"
                )
                with engine.begin() as conn:
                    conn.execute(text(grant))
                result = {"audit_probe": operation}
            else:
                raise ValueError
        print(json.dumps(result))
    except (ValueError, AssertionError, SQLAlchemyError, OSError, IndexError) as error:
        print(
            json.dumps(
                {
                    "error": "isolated_operation_rejected",
                    "category": type(error).__name__,
                    "sqlstate": getattr(getattr(error, "orig", None), "sqlstate", None),
                }
            ),
            file=sys.stderr,
        )
        sys.exit(
            "Isolated database operation rejected; no configuration or SQL is printed."
        )
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
