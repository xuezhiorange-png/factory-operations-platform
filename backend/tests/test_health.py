"""M0 liveness and intentionally absent production features."""

from fastapi.testclient import TestClient


def test_public_health_only_reports_process_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "factory-operations", "stage": "M0"}


def test_business_endpoints_not_exposed_in_m0(client: TestClient) -> None:
    assert client.get("/api/v1/assets").status_code == 404
    assert client.post("/api/v1/work-orders", json={}).status_code == 404


def test_openapi_exposes_liveness_and_only_scoped_business_reads(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/api/v1/health",
        "/api/v1/factories",
        "/api/v1/factories/{factory_id}/assets",
        "/api/v1/factories/{factory_id}/assets/{asset_id}",
        "/api/v1/auth/config",
        "/api/v1/auth/feishu/start",
        "/api/v1/auth/feishu/callback",
        "/api/v1/auth/me",
        "/api/v1/auth/logout",
    }
    assert all(
        set(methods)
        == ({"post"} if path in {"/api/v1/auth/logout", "/api/v1/auth/feishu/start"} else {"get"})
        for path, methods in schema["paths"].items()
    )
    assert set(schema["paths"]["/api/v1/health"]) == {"get"}
    health = schema["components"]["schemas"]["HealthResponse"]
    assert set(health["required"]) == {"status", "service", "stage"}
    for name, value in {"status": "ok", "service": "factory-operations", "stage": "M0"}.items():
        assert health["properties"][name]["const"] == value
