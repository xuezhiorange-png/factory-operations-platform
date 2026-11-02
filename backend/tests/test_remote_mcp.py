"""Real SDK Streamable HTTP and isolated PostgreSQL; no external connection or credentials."""

import asyncio
import json
import socket
import ssl
import subprocess
import threading
import time

import httpx2
import pytest
import uvicorn
from fastapi.testclient import TestClient
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from sqlalchemy import delete, event, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from factory_ops.api.app import create_app
from factory_ops.application.assets import AssetQueries
from factory_ops.application.mcp import ReadOnlyAssetMcp
from factory_ops.infrastructure.database.models import (
    AuditRow,
    ExternalIdentityRow,
    FactoryAccessRow,
    UserRow,
)
from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork


@pytest.fixture
def remote(business, signed_identity):
    _, data, db = business
    provider, token, key = signed_identity
    with Session(db.engine) as session:
        identity = provider.authenticate(token())
        session.add(
            ExternalIdentityRow(
                user_id=data.users["engineer"],
                provider=identity.provider,
                issuer=identity.issuer,
                tenant_id=identity.tenant_id,
                app_id=identity.app_id,
                subject_id=identity.subject_id,
            )
        )
        session.commit()
    service = ReadOnlyAssetMcp(provider, AssetQueries(lambda: SqlReadUnitOfWork(db.engine)))
    app = create_app(mcp_service=service, mcp_public_origin="https://mcp.test")
    with TestClient(app, base_url="https://mcp.test") as client:
        client.headers.update(
            {
                "x-aily-jwt": token(),
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-11-25",
            }
        )
        yield client, data, db, service, token


def rpc(http, method, params=None, *, request_id=1):
    body = {"jsonrpc": "2.0", "method": method, "id": request_id}
    if params is not None:
        body["params"] = params
    return http.post("/mcp", json=body)


def call(http, name, arguments=None):
    response = rpc(http, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200
    return response.json()["result"]


def error_code(result):
    assert result["isError"] is True
    assert "structuredContent" not in result
    return json.loads(result["content"][0]["text"])["error"]["code"]


def test_discovery_initialize_queries_and_minimal_dtos(remote):
    http, data, db, _, _ = remote
    init = rpc(
        http,
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "synthetic", "version": "1"},
        },
    )
    assert init.status_code == 200
    assert init.json()["result"]["protocolVersion"] == "2025-11-25"
    assert "mcp-session-id" not in init.headers
    tools = rpc(http, "tools/list").json()["result"]["tools"]
    assert {t["name"] for t in tools} == {"list_factories", "search_assets", "get_asset_detail"}
    assert all(t["annotations"]["readOnlyHint"] for t in tools)
    factories = call(http, "list_factories")["structuredContent"]["items"]
    assert factories == [
        {"id": str(data.factories["A"]), "code": "SYNTH-A", "name": "合成测试工厂 A"}
    ]
    page = call(http, "search_assets", {"factory_id": factories[0]["id"], "q": "EQ-001"})
    asset = page["structuredContent"]["items"][0]
    assert page["structuredContent"]["total"] == 1
    detail = call(
        http, "get_asset_detail", {"factory_id": asset["factory_id"], "asset_id": asset["id"]}
    )
    assert detail["structuredContent"] == asset
    assert not {"attachments", "users", "email", "external_identities"} & set(asset)
    assert (
        http.post(
            "/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}
        ).status_code
        == 202
    )
    assert init.headers["cache-control"] == "no-store"
    with Session(db.engine) as session:
        actions = set(
            session.scalars(select(AuditRow.action).where(AuditRow.channel == "doubao_mcp"))
        )
        assert {"assets.search", "assets.get", "factories.list"} <= actions


@pytest.mark.parametrize("operation", ["missing", "invalid", "expired", "tenant", "signature"])
def test_http_identity_rejected_on_every_request(remote, operation):
    http, _, _, _, token = remote
    credential = {
        "missing": None,
        "invalid": "malformed",
        "expired": token(exp=1),
        "tenant": token(tenant_id=99),
        "signature": token()[:-8] + "invalid!",
    }[operation]
    if credential is None:
        del http.headers["x-aily-jwt"]
    else:
        http.headers["x-aily-jwt"] = credential
    for method in ["tools/list", "initialize", "tools/call"]:
        assert rpc(http, method).status_code == 401
    assert http.get("/mcp").status_code == 401
    assert http.delete("/mcp").status_code == 401


def test_no_cookie_plain_header_duplicate_or_shared_token_fallback(remote):
    http, data, _, _, token = remote
    del http.headers["x-aily-jwt"]
    response = http.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        headers={
            "Authorization": "Bearer " + data.tokens["group"],
            "x-aily-user": "group_lead",
            "x-aily-token": "shared",
        },
    )
    assert response.status_code == 401
    assert (
        http.get("/mcp", headers=[("x-aily-jwt", token()), ("x-aily-jwt", token())]).status_code
        == 401
    )


def test_unbound_pending_and_inactive_users_cannot_read(remote):
    http, data, db, _, token = remote
    http.headers["x-aily-jwt"] = token(user_id=7620000000000000099)
    assert error_code(call(http, "list_factories")) == "authentication_required"
    assert rpc(http, "tools/list").json()["error"]["message"] == "authentication_required"
    http.headers["x-aily-jwt"] = token()
    for values, expected in [
        ({"role": None}, "permission_denied"),
        ({"active": False}, "authentication_required"),
    ]:
        with Session(db.engine) as session:
            session.execute(
                update(UserRow).where(UserRow.id == data.users["engineer"]).values(**values)
            )
            session.commit()
        assert error_code(call(http, "list_factories")) == expected


def test_cross_factory_uuid_and_immediate_revocation(remote):
    http, data, db, _, _ = remote
    a = {"factory_id": str(data.factories["A"])}
    b = {"factory_id": str(data.factories["B"])}
    assert error_code(call(http, "search_assets", b)) == "permission_denied"
    assert (
        error_code(call(http, "get_asset_detail", {**a, "asset_id": str(data.assets["B"])}))
        == "not_found"
    )
    assert (
        error_code(call(http, "get_asset_detail", {**b, "asset_id": str(data.assets["B"])}))
        == "permission_denied"
    )
    assert call(http, "search_assets", a)["structuredContent"]["total"] == 2
    with Session(db.engine) as session:
        session.execute(
            delete(FactoryAccessRow).where(FactoryAccessRow.user_id == data.users["engineer"])
        )
        session.commit()
    assert call(http, "list_factories")["structuredContent"]["items"] == []
    assert error_code(call(http, "search_assets", a)) == "permission_denied"
    with Session(db.engine) as session:
        session.execute(
            update(ExternalIdentityRow)
            .where(ExternalIdentityRow.user_id == data.users["engineer"])
            .values(active=False)
        )
        session.commit()
    assert error_code(call(http, "list_factories")) == "authentication_required"


@pytest.mark.parametrize(
    "role, count", [("group", 3), ("multi", 2), ("admin", 1), ("ungranted", 0)]
)
def test_all_three_roles_and_ungranted_scope(remote, role, count):
    http, data, db, _, _ = remote
    with Session(db.engine) as session:
        session.execute(
            update(ExternalIdentityRow)
            .where(ExternalIdentityRow.issuer == "https://aily.feishu.cn")
            .values(user_id=data.users[role])
        )
        session.commit()
    factories = call(http, "list_factories")["structuredContent"]["items"]
    assert len(factories) == count
    result = call(http, "search_assets", {"factory_id": str(data.factories["B"])})
    if role in {"group", "multi"}:
        assert result["structuredContent"]["total"] == 1
    else:
        assert error_code(result) == "permission_denied"


def test_protocol_errors_scope_and_no_echo(remote):
    http, data, _, _, _ = remote
    assert rpc(http, "unknown/method").json()["error"]["code"] == -32601
    for arguments in [
        {"factory_id": "not-uuid"},
        {"factory_id": str(data.factories["A"]), "user_id": "SECRET-SENTINEL"},
    ]:
        result = call(http, "search_assets", arguments)
        assert error_code(result) == "invalid_request"
        assert "SECRET-SENTINEL" not in json.dumps(result)
    assert error_code(call(http, "delete_assets")) == "invalid_request"
    assert (
        http.post(
            "/mcp", content="{malformed", headers={"Content-Type": "application/json"}
        ).status_code
        == 400
    )
    assert (
        http.post(
            "/mcp", content="x" * 16385, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert rpc(http, "tools/list", request_id=2).status_code == 200
    assert http.get("/mcp", headers={"Origin": "https://attacker.invalid"}).status_code == 403
    assert http.get("/mcp", headers={"Host": "attacker.invalid"}).status_code == 421
    assert http.get("/mcp").status_code == 405
    assert http.delete("/mcp").status_code == 405
    assert http.post("http://mcp.test/mcp", json={}).status_code == 403


def test_configured_mcp_queries_without_feishu_login(remote, monkeypatch):
    from factory_ops import bootstrap

    _, data, db, service, token = remote
    for key in (
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_TENANT_KEY",
        "FACTORY_OPS_PUBLIC_ORIGIN",
    ):
        monkeypatch.delenv(key, raising=False)
    config = service.provider.config
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/factory_ops_test")
    monkeypatch.setenv("FACTORY_OPS_MCP_ENABLED", "1")
    monkeypatch.setenv("FACTORY_OPS_MCP_PUBLIC_ORIGIN", "https://mcp.test")
    monkeypatch.setenv("AILY_TENANT_ID", config.tenant_id)
    monkeypatch.setenv("AILY_ALLOWED_AGENT_IDS", ",".join(config.agent_ids))
    monkeypatch.setenv("AILY_IDENTITY_JWT_SECRET", config.signing_secret)
    # Composition under test gets the already isolated schema; never use the public DB schema.
    monkeypatch.setattr(bootstrap, "create_engine", lambda *args, **kwargs: db.engine)
    app = bootstrap.configured_app()
    assert app.state.auth_service is None
    with TestClient(app, base_url="https://mcp.test") as http:
        http.headers.update(
            {
                "x-aily-jwt": token(),
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-11-25",
            }
        )
        result = call(http, "search_assets", {"factory_id": str(data.factories["A"])})
        assert result["structuredContent"]["total"] == 2


@pytest.mark.parametrize("failure", ["database", "audit"])
def test_storage_failure_denies_without_data_or_secret_leak(remote, failure, caplog):
    http, data, db, _, token = remote

    def fail(conn, cursor, statement, parameters, context, executemany):
        if failure == "database" or statement.startswith("INSERT INTO audit_events"):
            raise OperationalError("SECRET-SENTINEL", {}, Exception("SECRET-SENTINEL"))

    event.listen(db.engine, "before_cursor_execute", fail)
    try:
        result = call(http, "search_assets", {"factory_id": str(data.factories["A"])})
        assert error_code(result) == "storage_unavailable"
        assert "SECRET-SENTINEL" not in json.dumps(result) + caplog.text
        assert token() not in caplog.text
    finally:
        event.remove(db.engine, "before_cursor_execute", fail)
    assert (
        call(http, "search_assets", {"factory_id": str(data.factories["A"])})["structuredContent"][
            "total"
        ]
        == 2
    )


def test_official_sdk_client_https_disconnect_reconnect(remote, tmp_path):
    _, data, db, service, token = remote
    cert, key = tmp_path / "localhost.crt", tmp_path / "localhost.key"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        check=True,
        capture_output=True,
    )
    key.chmod(0o600)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    origin = f"https://localhost:{port}"
    app = create_app(mcp_service=service, mcp_public_origin=origin)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            ssl_keyfile=str(key),
            ssl_certfile=str(cert),
            log_level="critical",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started

        async def round_trip():
            context = ssl.create_default_context(cafile=str(cert))
            # A fresh TLS connection/client after disconnect, no cached identity/session ID.
            for _ in range(2):
                async with httpx2.AsyncClient(
                    verify=context, trust_env=False, headers={"x-aily-jwt": token()}
                ) as http:
                    transport = streamable_http_client(origin + "/mcp", http_client=http)
                    async with Client(transport, mode="legacy", cache=None) as client:
                        assert len((await client.list_tools()).tools) == 3
                        result = await client.call_tool("list_factories", {})
                        assert result.structured_content["items"][0]["id"] == str(
                            data.factories["A"]
                        )
                        assets = await client.call_tool(
                            "search_assets", {"factory_id": str(data.factories["A"]), "q": "EQ-001"}
                        )
                        asset = assets.structured_content["items"][0]
                        detail = await client.call_tool(
                            "get_asset_detail",
                            {"factory_id": asset["factory_id"], "asset_id": asset["id"]},
                        )
                        assert detail.structured_content["id"] == asset["id"]

        asyncio.run(round_trip())
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
    assert not thread.is_alive()
