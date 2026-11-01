"""Official response verification, one-time login, cookie/CSRF and stale-session tests."""

import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from db_support import seed_synthetic
from fastapi.testclient import TestClient
from feishu_support import ORIGIN, auth_fixture, login
from sqlalchemy import func, inspect, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from factory_ops.api.auth import CSRF, FLOW, SESSION
from factory_ops.application.auth import digest, safe_return
from factory_ops.application.errors import IdentityUnavailable, InvalidLogin, InvalidRequest
from factory_ops.infrastructure.database.models import (
    AuditRow,
    ExternalIdentityRow,
    OAuthFlowRow,
    SessionRow,
    UserRow,
)
from factory_ops.infrastructure.identity.feishu import (
    TOKEN_URL,
    FeishuConfig,
    FeishuIdentityProvider,
)


@pytest.fixture
def authenticated(db):
    data = seed_synthetic(db.engine)
    app, service, codes, subjects = auth_fixture(db, data)
    with TestClient(app, base_url=ORIGIN) as http:
        yield http, service, codes, subjects, data, db


@pytest.mark.parametrize("bad", ["error", "expired", "tenant", "app", "client", "subject", "type"])
def test_official_identity_response_must_be_trusted(bad):
    def transport(request):
        if str(request.url) == TOKEN_URL:
            body = json.loads(request.content)
            assert body["client_id"] == "SYNTH-APP" and body["code_verifier"]
            token = {
                "code": 0,
                "access_token": secrets.token_urlsafe(32),
                "expires_in": 3600,
                "token_type": "Bearer",
            }
            if bad == "error":
                token["code"] = 20024
            if bad == "expired":
                token["expires_in"] = 0
            if bad == "type":
                token["token_type"] = "invalid"
            if bad == "client":
                token["client_id"] = "WRONG-APP"
            return httpx.Response(200, json=token)
        info = {"open_id": "SYNTH-SUBJECT", "tenant_key": "SYNTH-TENANT", "app_id": "SYNTH-APP"}
        if bad == "tenant":
            info["tenant_key"] = "WRONG-TENANT"
        if bad == "app":
            info["app_id"] = "WRONG-APP"
        if bad == "subject":
            info["open_id"] = ""
        return httpx.Response(200, json={"code": 0, "data": info})

    provider = FeishuIdentityProvider(
        FeishuConfig(
            "SYNTH-APP",
            "SYNTH-TENANT",
            ORIGIN + "/api/v1/auth/feishu/callback",
            secrets.token_urlsafe(32),
        ),
        transport=httpx.MockTransport(transport),
    )
    with pytest.raises(InvalidLogin):
        provider.authenticate("SYNTH-CODE", code_verifier=secrets.token_urlsafe(32))


def test_unconfigured_channel_never_connects_or_claims_login(client):
    assert client.get("/api/v1/auth/config").json()["configured"] is False
    assert client.post("/api/v1/auth/feishu/start", json={}).status_code == 503
    with pytest.raises(IdentityUnavailable):
        FeishuIdentityProvider().authenticate("SYNTH")


@pytest.mark.parametrize(
    "destination",
    [
        "https://evil.invalid",
        "//evil.invalid",
        "/\\evil",
        "/assets%0d%0a",
        "/api/v1/auth/feishu/callback",
        "/assets#//evil",
        "/login",
        "/assets?next=https://evil.invalid",
    ],
)
def test_callback_targets_are_internal_routes_only(destination):
    with pytest.raises(InvalidRequest):
        safe_return(destination)


@pytest.mark.parametrize("role", ["group", "engineer", "multi", "admin"])
def test_verified_login_uses_existing_internal_grants(authenticated, role):
    http, _, codes, subjects, data, db = authenticated
    destination = "/m/assets/" + str(data.assets["A"]) + "?factory=" + str(data.factories["A"])
    result = login(http, codes, subjects[role], destination, "h5")
    assert result.status_code == 303 and result.headers["location"] == ORIGIN + "/#" + destination
    assert all("Secure" in c and "SameSite=lax" in c for c in result.headers.get_list("set-cookie"))
    assert "HttpOnly" in next(
        c for c in result.headers.get_list("set-cookie") if c.startswith(SESSION + "=")
    )
    me = http.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["id"] == str(data.users[role])
    assert len(me.json()["factories"]) == {"group": 3, "engineer": 1, "multi": 2, "admin": 1}[role]
    token = http.cookies.get(SESSION)
    credential_leaked = token in me.text
    assert not credential_leaked
    with Session(db.engine) as session:
        row = session.scalar(select(SessionRow).where(SessionRow.token_hash == digest(token)))
        assert row.external_identity_id is not None and len(row.token_hash) == 64
    path = f"/api/v1/factories/{data.factories['A']}/assets/{data.assets['A']}"
    assert http.get(path).status_code == 200


def test_first_seen_and_existing_ungranted_accounts_stay_pending(authenticated):
    http, _, codes, subjects, data, db = authenticated
    login(http, codes, "SYNTH-NEW-SUBJECT")
    me = http.get("/api/v1/auth/me").json()
    assert me["status"] == "pending" and me["role"] is None and me["factories"] == []
    assert http.get(f"/api/v1/factories/{data.factories['A']}/assets").status_code == 403
    login(http, codes, subjects["ungranted"])
    assert http.get("/api/v1/auth/me").json()["status"] == "pending"
    with Session(db.engine) as session:
        assert session.scalar(select(func.count()).select_from(UserRow)) == 6


def test_state_browser_binding_expiry_and_replay(authenticated):
    http, service, codes, subjects, _, db = authenticated
    start = service.start("/assets", "pc")
    query = parse_qs(urlsplit(start.url).query)
    state = query["state"][0]
    assert query["code_challenge_method"] == ["S256"]
    code = secrets.token_urlsafe(32)
    codes[code] = subjects["engineer"]
    with pytest.raises(InvalidLogin):
        service.complete(state, code, secrets.token_urlsafe(32))
    result = service.complete(state, code, start.browser_secret)
    assert result.return_to == "/assets"
    with pytest.raises(InvalidLogin):
        service.complete(state, code, start.browser_secret)
    another = service.start("/assets", "pc")
    state2 = parse_qs(urlsplit(another.url).query)["state"][0]
    with pytest.raises(InvalidLogin):
        service.complete(state2, code, another.browser_secret)
    expired = service.start("/assets", "pc")
    state3 = parse_qs(urlsplit(expired.url).query)["state"][0]
    with Session(db.engine) as session:
        session.execute(
            update(OAuthFlowRow)
            .where(OAuthFlowRow.state_hash == digest(state3))
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        session.commit()
    with pytest.raises(InvalidLogin):
        service.complete(state3, "SYNTH-OTHER-CODE", expired.browser_secret)


def test_csrf_origin_logout_rotation_and_binding_revocation(authenticated):
    http, _, codes, subjects, _, db = authenticated
    login(http, codes, subjects["engineer"])
    old_token = http.cookies.get(SESSION)
    login(http, codes, subjects["engineer"])
    with Session(db.engine) as session:
        assert (
            session.scalar(
                select(SessionRow).where(SessionRow.token_hash == digest(old_token))
            ).revoked_at
            is not None
        )
    assert http.post("/api/v1/auth/logout").status_code == 403
    assert (
        http.post(
            "/api/v1/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": "forged"}
        ).status_code
        == 403
    )
    assert (
        http.post(
            "/api/v1/auth/logout",
            headers={"Origin": "https://evil.invalid", "X-CSRF-Token": http.cookies.get(CSRF)},
        ).status_code
        == 403
    )
    assert (
        http.post(
            "/api/v1/auth/logout",
            headers={"Origin": ORIGIN, "X-CSRF-Token": http.cookies.get(CSRF)},
        ).status_code
        == 204
    )
    assert http.get("/api/v1/auth/me").status_code == 401
    login(http, codes, subjects["engineer"])
    with Session(db.engine) as session:
        session.execute(
            update(ExternalIdentityRow)
            .where(ExternalIdentityRow.subject_id == subjects["engineer"])
            .values(active=False)
        )
        session.commit()
    assert http.get("/api/v1/auth/me").json()["error"]["code"] == "session_expired"
    result = login(http, codes, subjects["engineer"])
    assert "permission_denied" in result.headers["location"]


def test_duplicate_callback_and_failed_login_do_not_leak(authenticated):
    http, _, _, _, _, _ = authenticated
    result = http.get(
        "/api/v1/auth/feishu/callback?state=synthetic&state=other&code=private-value",
        follow_redirects=False,
    )
    assert result.headers["location"].startswith(ORIGIN + "/#/login?status=failed")
    assert "private-value" not in result.headers["location"]
    bad = http.post(
        "/api/v1/auth/feishu/start", headers={"Origin": ORIGIN}, json={"secret": "private-value"}
    )
    assert bad.status_code == 422 and "private-value" not in bad.text
    assert http.cookies.get(FLOW) is None


def test_login_audit_covers_verified_binding_and_session(authenticated):
    http, _, codes, _, _, db = authenticated
    login(http, codes, "SYNTH-NEW-USER")
    with Session(db.engine) as session:
        assert {r.action for r in session.scalars(select(AuditRow))} >= {
            "identity.first_seen",
            "auth.login",
        }


def test_login_identity_and_session_roll_back_when_audit_fails(authenticated):
    http, _, codes, _, _, db = authenticated
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_login_audit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'synthetic failure'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER fail_login_audit BEFORE INSERT ON audit_events "
                "FOR EACH ROW EXECUTE FUNCTION fail_login_audit()"
            )
        )
    result = login(http, codes, "SYNTH-FAILED-NEW-SUBJECT")
    assert "storage_unavailable" in result.headers["location"]
    with Session(db.engine) as session:
        assert session.scalar(select(func.count()).select_from(UserRow)) == 5
        assert session.scalar(select(func.count()).select_from(SessionRow)) == 5
        assert session.scalar(select(func.count()).select_from(AuditRow)) == 0
    with db.engine.begin() as connection:
        connection.execute(text("DROP TRIGGER fail_login_audit ON audit_events"))
    result = login(http, codes, "SYNTH-FAILED-NEW-SUBJECT")
    assert result.headers["location"] == ORIGIN + "/#/assets"


def test_same_oauth_challenge_concurrently_issues_only_one_session(authenticated):
    _, service, codes, subjects, _, db = authenticated
    flow = service.start("/assets", "pc")
    state = parse_qs(urlsplit(flow.url).query)["state"][0]
    code = secrets.token_urlsafe(32)
    codes[code] = subjects["engineer"]

    def complete():
        try:
            service.complete(state, code, flow.browser_secret)
            return True
        except InvalidLogin:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: complete(), range(2))) == [False, True]
    with Session(db.engine) as session:
        assert session.scalar(select(func.count()).select_from(SessionRow)) == 6


def test_new_migration_failure_rolls_back_and_preserves_old_schema(db):
    db.migration("downgrade", "0001_m1_foundation")
    with db.engine.begin() as connection:
        connection.execute(text("CREATE TABLE oauth_flows (id integer PRIMARY KEY)"))
    with pytest.raises(DBAPIError):
        db.migration("upgrade", "head")
    assert "auth_version" not in {
        column["name"] for column in inspect(db.engine).get_columns("users")
    }
    with db.engine.begin() as connection:
        connection.execute(text("DROP TABLE oauth_flows"))
    db.migration("upgrade", "head")
    assert "auth_version" in {column["name"] for column in inspect(db.engine).get_columns("users")}


def test_upstream_timeout_fails_closed_without_exposing_transport_error():
    def unavailable(request):
        raise httpx.ReadTimeout("private-upstream-detail")

    provider = FeishuIdentityProvider(
        FeishuConfig("SYNTH-APP", "SYNTH-TENANT", ORIGIN, secrets.token_urlsafe(32)),
        transport=httpx.MockTransport(unavailable),
    )
    with pytest.raises(IdentityUnavailable) as error:
        provider.authenticate("SYNTH-CODE", code_verifier=secrets.token_urlsafe(32))
    assert "private-upstream-detail" not in str(error.value)
