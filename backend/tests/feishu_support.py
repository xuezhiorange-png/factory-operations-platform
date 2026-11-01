"""Explicit synthetic official-endpoint fixture, never imported by runtime bootstrap."""

import json
import secrets
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from factory_ops.api.app import create_app
from factory_ops.application.access import AccessService
from factory_ops.application.assets import AssetQueries
from factory_ops.application.auth import AuthService, AuthSettings
from factory_ops.infrastructure.database.access import SqlAccessUnitOfWork
from factory_ops.infrastructure.database.auth import SqlAuthUnitOfWork
from factory_ops.infrastructure.database.models import ExternalIdentityRow, UserRow
from factory_ops.infrastructure.identity.feishu import (
    TOKEN_URL,
    USERINFO_URL,
    FeishuConfig,
    FeishuIdentityProvider,
)

ORIGIN = "https://platform.test"


class SyntheticCodePool(dict):
    def __repr__(self):
        return "<synthetic authorization codes redacted>"


def auth_fixture(db, data, origin=ORIGIN):
    settings = AuthSettings(origin, "SYNTH-APP")
    secret = secrets.token_urlsafe(32)
    codes = SyntheticCodePool()
    identities = {role: "SYNTH-SUBJECT-" + role for role in data.users}
    with Session(db.engine) as session:
        for role, uid in data.users.items():
            session.get(UserRow, uid).display_name = "SYNTH-人员-" + role
            session.add(
                ExternalIdentityRow(
                    user_id=uid,
                    provider="feishu",
                    issuer="https://open.feishu.cn",
                    tenant_id="SYNTH-TENANT",
                    app_id="SYNTH-APP",
                    subject_id=identities[role],
                )
            )
        session.commit()

    def transport(request):
        if str(request.url) == TOKEN_URL:
            body = json.loads(request.content)
            if (
                body.get("client_id") != settings.app_id
                or body.get("client_secret") != secret
                or body.get("redirect_uri") != settings.callback
                or not body.get("code_verifier")
            ):
                raise AssertionError("Synthetic client exchange contract mismatch")
            subject = codes.get(body.get("code"))
            if not subject:
                return httpx.Response(400, json={"code": 20004})
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "access_token": subject,
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        if str(request.url) == USERINFO_URL:
            value = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if value not in codes.values():
                return httpx.Response(401, json={"code": 99991663})
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "open_id": value,
                        "tenant_key": "SYNTH-TENANT",
                        "name": "SYNTH-已验证用户",
                    },
                },
            )
        raise AssertionError("Unexpected external request")

    provider = FeishuIdentityProvider(
        FeishuConfig(settings.app_id, "SYNTH-TENANT", settings.callback, secret),
        transport=httpx.MockTransport(transport),
    )
    service = AuthService(lambda: SqlAuthUnitOfWork(db.engine), settings, provider)
    app = create_app(
        lambda: AssetQueries(lambda: SqlAuthUnitOfWork(db.engine)),
        auth_service=service,
        access_service=AccessService(lambda: SqlAccessUnitOfWork(db.engine)),
        data_source="synthetic_test",
    )
    return app, service, codes, identities


def login(http: TestClient, codes, subject, return_to="/assets", channel="pc"):
    code = secrets.token_urlsafe(32)
    codes[code] = subject
    start = http.post(
        "/api/v1/auth/feishu/start",
        json={"return_to": return_to, "channel": channel},
        headers={"Origin": str(http.base_url).rstrip("/")},
    )
    state = parse_qs(urlsplit(start.json()["authorization_url"]).query)["state"][0]
    return http.get(
        "/api/v1/auth/feishu/callback",
        params={"state": state, "code": code},
        follow_redirects=False,
    )
