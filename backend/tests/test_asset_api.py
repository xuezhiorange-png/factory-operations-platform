"""Real PostgreSQL queries, real opaque sessions and fresh server authorization."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from factory_ops.infrastructure.database.models import (
    AuditRow,
    FactoryAccessRow,
    SessionRow,
    UserRow,
)


def auth(data, role="engineer"):
    return {"Authorization": "Bearer " + data.tokens[role]}


def path(data, factory="A", asset=None):
    result = f"/api/v1/factories/{data.factories[factory]}/assets"
    return result + (f"/{data.assets[asset]}" if asset else "")


@pytest.mark.parametrize(
    "role,expected", [("group", 3), ("engineer", 1), ("multi", 2), ("admin", 1), ("ungranted", 0)]
)
def test_factory_scope_is_server_derived(business, role, expected):
    http, data, _ = business
    result = http.get("/api/v1/factories", headers=auth(data, role))
    assert result.status_code == 200
    assert len(result.json()["items"]) == expected
    assert result.json()["data_source"] == "synthetic_test"
    assert result.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("role", ["group", "engineer", "multi", "admin"])
def test_authorized_asset_query_and_detail(business, role):
    http, data, _ = business
    page = http.get(path(data), headers=auth(data, role)).json()
    assert page["total"] == 2
    assert {item["factory_id"] for item in page["items"]} == {str(data.factories["A"])}
    detail = http.get(path(data, asset="A"), headers=auth(data, role))
    assert detail.status_code == 200
    assert detail.json()["asset"]["name"] == "SYNTH-设备-A"
    assert (
        not {"attachments", "token_hash", "user_id", "external_identities"}
        & detail.json()["asset"].keys()
    )


@pytest.mark.parametrize("role", ["engineer", "admin", "ungranted"])
def test_cross_factory_list_search_and_direct_uuid_denied(business, role):
    http, data, _ = business
    for target in [path(data, "B"), path(data, "B") + "?q=SYNTH", path(data, "B", "B")]:
        response = http.get(target, headers=auth(data, role))
        assert response.status_code == 403
        assert "SYNTH-设备-B" not in response.text
    # Forging A scope around a B UUID cannot make the B resource belong to A.
    response = http.get(path(data, "A", "B"), headers=auth(data, role))
    assert response.status_code in {403, 404}
    assert "SYNTH-设备-B" not in response.text


def test_literal_search_filter_pagination_and_no_cross_scope_counts(business):
    http, data, _ = business
    for query, expected in [
        ("q=%25", 1),
        ("q=_", 1),
        ("q=SYNTH-设备-B", 0),
        ("status=retired", 0),
        ("category=utilities", 1),
        ("q=%27%20OR%201%3D1", 0),
    ]:
        result = http.get(path(data) + "?" + query, headers=auth(data)).json()
        assert result["total"] == expected
    result = http.get(path(data) + "?limit=1&offset=1", headers=auth(data)).json()
    assert result["total"] == 2 and len(result["items"]) == 1


@pytest.mark.parametrize(
    "change",
    [
        "revoke_grant",
        "remove_role",
        "change_group_to_engineer",
        "disable_user",
        "revoke_session",
        "expire_session",
        "future_session",
    ],
)
def test_old_session_does_not_keep_stale_permissions(business, change):
    http, data, db = business
    role = "group" if change == "change_group_to_engineer" else "engineer"
    factory = "B" if role == "group" else "A"
    assert http.get(path(data, factory), headers=auth(data, role)).status_code == 200
    uid = data.users[role]
    with Session(db.engine) as session:
        if change == "revoke_grant":
            session.execute(delete(FactoryAccessRow).where(FactoryAccessRow.user_id == uid))
        elif change == "remove_role":
            session.execute(update(UserRow).where(UserRow.id == uid).values(role=None))
        elif change == "change_group_to_engineer":
            session.execute(update(UserRow).where(UserRow.id == uid).values(role="engineer"))
        elif change == "disable_user":
            session.execute(update(UserRow).where(UserRow.id == uid).values(active=False))
        elif change == "revoke_session":
            session.execute(
                update(SessionRow)
                .where(SessionRow.user_id == uid)
                .values(revoked_at=datetime.now(UTC))
            )
        elif change == "future_session":
            session.execute(
                update(SessionRow)
                .where(SessionRow.user_id == uid)
                .values(
                    issued_at=datetime.now(UTC) + timedelta(hours=1),
                    expires_at=datetime.now(UTC) + timedelta(hours=2),
                )
            )
        else:
            session.execute(
                update(SessionRow)
                .where(SessionRow.user_id == uid)
                .values(
                    issued_at=datetime.now(UTC) - timedelta(hours=2),
                    expires_at=datetime.now(UTC) - timedelta(hours=1),
                )
            )
        session.commit()
    expected = (
        401
        if change in {"disable_user", "revoke_session", "expire_session", "future_session"}
        else 403
    )
    assert http.get(path(data, factory), headers=auth(data, role)).status_code == expected
    assert (
        http.get(
            path(data, factory, "B" if factory == "B" else "A"), headers=auth(data, role)
        ).status_code
        == expected
    )


def test_unknown_identity_claims_and_unexposed_attachments_cannot_authorize(business):
    http, data, _ = business
    assert http.get(path(data), headers={"X-User-Id": str(data.users["group"])}).status_code == 401
    assert http.get(path(data), headers={"Authorization": "Bearer " + "x" * 43}).status_code == 401
    assert (
        http.get(
            path(data, "B"), headers={**auth(data), "X-User-Id": str(data.users["group"])}
        ).status_code
        == 403
    )
    for query in [
        "user_id=" + str(data.users["group"]),
        "factory_id=" + str(data.factories["B"]),
        "q=a&q=b",
        "limit=101",
        "offset=-1",
    ]:
        assert http.get(path(data) + "?" + query, headers=auth(data)).status_code == 422
    assert http.get(path(data, asset="A") + "/attachments", headers=auth(data)).status_code == 404
    assert http.post(path(data), json={}, headers=auth(data)).status_code == 405


def test_conflicting_cookie_and_bearer_denied(business):
    http, data, _ = business
    http.cookies.set("factory_ops_session", data.tokens["admin"])
    assert http.get(path(data), headers=auth(data)).status_code == 401


def test_multi_factory_admin_misconfiguration_fails_closed(business):
    http, data, db = business
    with Session(db.engine) as session:
        session.add(FactoryAccessRow(user_id=data.users["admin"], factory_id=data.factories["B"]))
        session.commit()
    assert http.get(path(data), headers=auth(data, "admin")).status_code == 403


def test_absent_and_empty_resources_do_not_leak(business):
    http, data, _ = business
    assert http.get(path(data, "EMPTY"), headers=auth(data, "group")).json()["items"] == []
    assert http.get(path(data) + f"/{uuid4()}", headers=auth(data)).status_code == 404


def test_audit_records_success_and_denial_without_search_or_credentials(business):
    http, data, db = business
    http.get(path(data) + "?q=private-search-term", headers=auth(data))
    http.get(path(data, "B"), headers=auth(data))
    with Session(db.engine) as session:
        rows = session.scalars(select(AuditRow)).all()
        assert {row.outcome for row in rows} == {"allowed", "denied"}
        assert all(row.actor_id == data.users["engineer"] and row.channel == "api" for row in rows)
        assert "private-search-term" not in repr(rows)


def test_audit_failure_rolls_back_and_does_not_return_data(business):
    http, data, db = business
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'synthetic failure'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER fail_audit BEFORE INSERT ON audit_events "
                "FOR EACH ROW EXECUTE FUNCTION fail_audit()"
            )
        )
    response = http.get(path(data), headers=auth(data))
    assert response.status_code == 503
    assert "SYNTH-设备-A" not in response.text and "synthetic failure" not in response.text
    with Session(db.engine) as session:
        assert session.scalar(select(func.count()).select_from(AuditRow)) == 0
