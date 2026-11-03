"""Loopback-only integration fixture. Synthetic records; never a deployment entrypoint."""

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs

import uvicorn
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tests"))
from db_support import isolated_database, seed_synthetic
from factory_ops.api.app import create_app
from factory_ops.application.access import AccessService
from factory_ops.application.assets import AssetQueries
from factory_ops.application.auth import AuthService, AuthSettings
from factory_ops.infrastructure.database.access import SqlAccessUnitOfWork
from factory_ops.infrastructure.database.auth import SqlAuthUnitOfWork
from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork


def main():
    if os.environ.get("FACTORY_OPS_SYNTHETIC_PORTAL_TEST") != "1":
        raise RuntimeError("Explicit synthetic-only opt-in required")
    database = isolated_database()
    try:
        data = seed_synthetic(database.engine)
        auth = AuthService(
            lambda: SqlAuthUnitOfWork(database.engine),
            AuthSettings("https://localhost:5195"),
        )
        app = create_app(
            lambda: AssetQueries(lambda: SqlReadUnitOfWork(database.engine)),
            auth_service=auth,
            access_service=AccessService(lambda: SqlAccessUnitOfWork(database.engine)),
            data_source="synthetic_test",
        )

        @app.middleware("http")
        async def synthetic_cookie(request, call_next):
            # HTTP loopback fixture only. Production keeps its __Host Secure cookie.
            token = request.cookies.get("portal_synthetic_test")
            if token and request.client.host in {"127.0.0.1", "::1", "testclient"}:
                headers = [
                    (key, value)
                    for key, value in request.scope["headers"]
                    if key.lower() != b"cookie"
                ]
                cookie = (
                    request.headers.get("cookie", "")
                    + "; __Host-factory_ops_session="
                    + token
                )
                request.scope["headers"] = headers + [(b"cookie", cookie.encode())]
            return await call_next(request)

        @app.get("/__portal_test__", response_class=HTMLResponse)
        def personas():
            buttons = "".join(
                f'<button name="persona" value="{key}">{label}</button>'
                for key, label in [
                    ("engineer", "合成工程师（工厂 A）"),
                    ("admin", "合成加工厂管理员（工厂 A）"),
                    ("group", "合成集团负责人"),
                    ("none", "无运维身份"),
                ]
            )
            return (
                '<h1>仅限本机：合成测试身份</h1><form method="post" action="/__portal_test__">'
                + buttons
                + "</form>"
            )

        @app.get("/__portal_test__/ids")
        def synthetic_ids():
            return {"factories": data.factories, "assets": data.assets}

        @app.post("/__portal_test__")
        async def persona(request: Request):
            if request.headers.get("origin") not in {
                "http://127.0.0.1:5195",
                "http://localhost:5195",
            }:
                return JSONResponse({"error": "loopback test only"}, status_code=403)
            key = parse_qs((await request.body()).decode()).get("persona", [""])[0]
            response = RedirectResponse("/operations/assets", status_code=303)
            if key == "none":
                response.delete_cookie("portal_synthetic_test")
            elif key in {"engineer", "admin", "group"}:
                response.set_cookie(
                    "portal_synthetic_test",
                    data.tokens[key],
                    httponly=True,
                    samesite="strict",
                    max_age=3600,
                )
            else:
                return JSONResponse(
                    {"error": "invalid synthetic persona"}, status_code=400
                )
            return response

        # Only the real monitor frontend is served by Vite. Its network fixture is
        # empty/read-only and cannot authenticate monitor control-capable accounts.
        @app.post("/api/login")
        async def monitor_login(request: Request):
            body = await request.json()
            if body != {"username": "guest", "password": ""}:
                return JSONResponse({"error": "Synthetic guest only"}, status_code=401)
            return {"success": True, "token": "1" * 48, "role": "guest"}

        @app.get("/api/session")
        def monitor_session(request: Request):
            if request.headers.get("authorization") != "Bearer " + "1" * 48:
                return JSONResponse({"error": "Not signed in"}, status_code=401)
            return {"success": True, "username": "合成监控访客", "role": "guest"}

        @app.post("/api/logout")
        def monitor_logout():
            return {"success": True}

        @app.get("/api")
        def monitor_data():
            return JSONResponse({"devices": []}, headers={"X-Data-Acquired-At": "0"})

        @app.get("/api/{path:path}")
        def monitor_empty(path: str):
            if path.startswith("v1/"):
                return JSONResponse({"error": "Not found"}, status_code=404)
            return []

        uvicorn.run(
            app, host="127.0.0.1", port=8016, access_log=False, log_level="warning"
        )
    finally:
        database.cleanup()


if __name__ == "__main__":
    main()
