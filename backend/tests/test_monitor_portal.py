"""Native portal uses the real query service, isolated PostgreSQL and synthetic IDs."""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from factory_ops.application.monitor_links import parse_monitor_links
from factory_ops.infrastructure.database.models import AuditRow, SessionRow


def definition(data, key="A", **overrides):
    return {
        "factory_id": str(data.factories[key]),
        "asset_id": str(data.assets[key]),
        "monitor_factory_id": "FAC_SYNTH_" + key,
        "monitor_gateway_id": "101" if key == "A" else "102",
        "monitor_device_id": "SYNTH_DEVICE_" + key,
        "valid_from": "2020-01-01T00:00:00Z",
        **overrides,
    }


def authenticate(http, data, role="engineer"):
    http.cookies.set("factory_ops_session", data.tokens[role])


def install(http, data):
    http.app.state.monitor_links = parse_monitor_links(
        json.dumps(
            [
                definition(data),
                definition(data, "B"),
            ]
        )
    )


def test_empty_links_fail_closed():
    assert parse_monitor_links("[]") == ()


@pytest.mark.parametrize("raw", ["{}", "[{}]", "null", '[{"factory_id": "name"}]'])
def test_invalid_configuration(raw):
    with pytest.raises(ValueError, match="Invalid explicit"):
        parse_monitor_links(raw)


def test_mapping_time_and_ambiguity(business):
    _, data, _ = business
    row = definition(data)
    links = parse_monitor_links(json.dumps([row]))
    assert links[0].active(datetime(2026, 1, 1, tzinfo=UTC))
    for changed in [
        {"valid_from": "2020-01-01"},
        {"valid_to": "2019-01-01T00:00:00Z"},
        {"monitor_factory_id": "same factory name"},
        {"monitor_device_id": "../other"},
        {"extra_authority": "admin"},
    ]:
        with pytest.raises(ValueError):
            parse_monitor_links(json.dumps([{**row, **changed}]))
    with pytest.raises(ValueError):
        parse_monitor_links(json.dumps([row, row]))
    retired = {**row, "valid_to": "2021-01-01T00:00:00Z"}
    assert (
        len(parse_monitor_links(json.dumps([retired, {**row, "valid_from": retired["valid_to"]}])))
        == 2
    )


def test_portal_requires_independent_session(business):
    http, data, _ = business
    install(http, data)
    path = "/api/v1/portal/resolve?monitor_factory_id=FAC_SYNTH_A&monitor_device_id=SYNTH_DEVICE_A"
    assert http.get(path).status_code == 401
    assert http.get(path, headers={"Authorization": "Bearer " + "a" * 48}).status_code == 401
    assert http.get(path, headers={"X-User-ID": str(data.users["group"])}).status_code == 401


@pytest.mark.parametrize("role", ["group", "engineer", "admin"])
def test_link_roundtrip_in_authorized_factory(business, role):
    http, data, database = business
    install(http, data)
    authenticate(http, data, role)
    params = {"factory_id": str(data.factories["A"]), "asset_id": str(data.assets["A"])}
    response = http.get("/api/v1/portal/asset-link", params=params)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["link"]["monitor_device_id"] == "SYNTH_DEVICE_A"
    result = http.get(
        "/api/v1/portal/resolve",
        params={
            "monitor_factory_id": "FAC_SYNTH_A",
            "monitor_device_id": "SYNTH_DEVICE_A",
        },
    )
    assert result.status_code == 200
    assert result.json()["link"]["asset_id"] == str(data.assets["A"])
    with Session(database.engine) as session:
        assert session.scalar(select(AuditRow).where(AuditRow.action == "assets.get"))


def test_cross_factory_tampering_revocation_and_missing(business):
    http, data, database = business
    install(http, data)
    authenticate(http, data)
    foreign = {"factory_id": str(data.factories["B"]), "asset_id": str(data.assets["B"])}
    denied = http.get("/api/v1/portal/asset-link", params=foreign)
    assert denied.status_code == 403
    assert str(data.assets["B"]) not in denied.text
    assert (
        http.get(
            "/api/v1/portal/resolve",
            params={
                "monitor_factory_id": "FAC_SYNTH_B",
                "monitor_device_id": "SYNTH_DEVICE_B",
            },
        ).status_code
        == 403
    )
    # A same-name asset in another factory cannot satisfy the exact tuple.
    assert (
        http.get(
            "/api/v1/portal/asset-link",
            params={
                "factory_id": str(data.factories["A"]),
                "asset_id": str(data.assets["B"]),
            },
        ).status_code
        == 404
    )
    missing = http.get(
        "/api/v1/portal/resolve",
        params={
            "monitor_factory_id": "FAC_UNKNOWN",
            "monitor_device_id": "SYNTH_DEVICE_A",
        },
    )
    assert missing.status_code == 200
    assert missing.json()["status"] == "unlinked" and missing.json()["link"] is None
    with Session(database.engine) as session:
        session.execute(update(SessionRow).values(revoked_at=datetime.now(UTC)))
        session.commit()
    assert http.get("/api/v1/portal/asset-link", params=foreign).status_code == 401


def test_expired_unmapped_and_read_only(business):
    http, data, _ = business
    authenticate(http, data)
    http.app.state.monitor_links = parse_monitor_links(
        json.dumps(
            [
                definition(data, valid_to="2021-01-01T00:00:00Z"),
            ]
        )
    )
    params = {"factory_id": str(data.factories["A"]), "asset_id": str(data.assets["A"])}
    response = http.get("/api/v1/portal/asset-link", params=params)
    assert response.json()["status"] == "unlinked"
    assert http.post("/api/v1/portal/asset-link", json=params).status_code == 405
    assert (
        http.get("/api/v1/portal/asset-link", params={**params, "user_id": "admin"}).status_code
        == 422
    )
