"""Real PostgreSQL access changes, stale sessions, audit rollback and concurrency."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from db_support import seed_synthetic
from fastapi.testclient import TestClient
from feishu_support import ORIGIN, auth_fixture, login
from sqlalchemy import delete, func, inspect, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from factory_ops.api.auth import CSRF, SESSION
from factory_ops.application.access import AccessChange
from factory_ops.application.errors import Conflict
from factory_ops.infrastructure.database.access import SqlAccessUnitOfWork
from factory_ops.infrastructure.database.models import (
    AuditRow,
    FactoryAccessRow,
    SessionRow,
    UserRow,
)


@pytest.fixture
def personnel(db):
    data = seed_synthetic(db.engine)
    app, auth, codes, subjects = auth_fixture(db, data)
    with TestClient(app, base_url=ORIGIN) as manager, TestClient(app, base_url=ORIGIN) as employee:
        login(manager, codes, subjects["group"])
        login(employee, codes, subjects["engineer"])
        yield manager, employee, app.state.access_service, auth, codes, subjects, data, db


def headers(http):
    return {"Origin": ORIGIN, "X-CSRF-Token": http.cookies.get(CSRF)}


def person(http, uid):
    return next(
        row for row in http.get("/api/v1/access/users").json()["items"] if row["id"] == str(uid)
    )


def change_body(row, factories, *, role="engineer", active=True):
    return {
        "expected_version": row["version"],
        "role": role,
        "active": active,
        "factory_ids": [str(uid) for uid in factories],
        "reason": "SYNTH-受控人员变更",
    }


def test_only_group_lead_can_see_personnel_and_change_access(personnel):
    manager, employee, _, _, _, _, data, _ = personnel
    assert employee.get("/api/v1/access/users").status_code == 403
    assert employee.get(f"/api/v1/access/users/{data.users['group']}/changes").status_code == 403
    row = person(manager, data.users["engineer"])
    url = f"/api/v1/access/users/{row['id']}"
    payload = change_body(row, [data.factories["A"], data.factories["B"]])
    assert employee.patch(url, json=payload, headers=headers(employee)).status_code == 403
    assert manager.patch(url, json=payload).status_code == 403
    assert (
        manager.patch(
            url, json=payload, headers={**headers(manager), "Origin": "https://evil.invalid"}
        ).status_code
        == 403
    )
    assert (
        manager.patch(
            url, json={**payload, "user_id": str(data.users["group"])}, headers=headers(manager)
        ).status_code
        == 422
    )
    assert not {"token_hash", "open_id", "subject_id", "email", "mobile"} & set(row)


def test_cross_factory_grant_invalidates_old_cookie_and_preserves_audit(personnel):
    manager, employee, _, _, codes, subjects, data, db = personnel
    row = person(manager, data.users["engineer"])
    response = manager.patch(
        f"/api/v1/access/users/{row['id']}",
        json=change_body(row, [data.factories["A"], data.factories["B"]]),
        headers=headers(manager),
    )
    assert response.status_code == 200
    assert employee.get("/api/v1/auth/me").status_code == 401
    b = f"/api/v1/factories/{data.factories['B']}/assets/{data.assets['B']}"
    assert employee.get(b).status_code == 401
    login(employee, codes, subjects["engineer"])
    assert employee.get(b).status_code == 200
    records = manager.get(f"/api/v1/access/users/{row['id']}/changes").json()["items"]
    assert records[0]["details"]["before"]["factory_ids"] == [str(data.factories["A"])]
    assert set(records[0]["details"]["after"]["factory_ids"]) == {
        str(data.factories["A"]),
        str(data.factories["B"]),
    }
    with Session(db.engine) as session:
        old = session.scalars(
            select(SessionRow).where(SessionRow.user_id == data.users["engineer"])
        ).all()
        assert any(row.revoked_at for row in old)


@pytest.mark.parametrize("operation", ["disable", "remove_role", "transfer", "revoke", "unbind"])
def test_lifecycle_operations_reject_old_session_and_direct_asset_uuid(personnel, operation):
    manager, employee, _, _, codes, subjects, data, _ = personnel
    row = person(manager, data.users["engineer"])
    url = f"/api/v1/access/users/{row['id']}"
    if operation in {"revoke", "unbind"}:
        result = manager.post(
            url + ("/revoke-sessions" if operation == "revoke" else "/unbind-feishu"),
            json={"expected_version": row["version"], "reason": "SYNTH-受控撤销"},
            headers=headers(manager),
        )
    else:
        payload = change_body(
            row,
            [data.factories["B"]]
            if operation == "transfer"
            else []
            if operation == "remove_role"
            else [data.factories["A"]],
            role=None if operation == "remove_role" else "engineer",
            active=operation != "disable",
        )
        result = manager.patch(url, json=payload, headers=headers(manager))
    assert result.status_code == 200
    assert employee.get("/api/v1/auth/me").status_code == 401
    assert (
        employee.get(
            f"/api/v1/factories/{data.factories['A']}/assets/{data.assets['A']}"
        ).status_code
        == 401
    )
    if operation in {"disable", "unbind"}:
        assert (
            "permission_denied" in login(employee, codes, subjects["engineer"]).headers["location"]
        )
    else:
        login(employee, codes, subjects["engineer"])
        if operation in {"transfer", "remove_role"}:
            assert (
                employee.get(
                    f"/api/v1/factories/{data.factories['A']}/assets/{data.assets['A']}"
                ).status_code
                == 403
            )


def test_version_conflict_last_group_guard_and_admin_single_scope(personnel):
    manager, _, _, _, _, _, data, _ = personnel
    row = person(manager, data.users["engineer"])
    url = f"/api/v1/access/users/{row['id']}"
    assert (
        manager.patch(
            url,
            json=change_body(
                row, [data.factories["A"], data.factories["B"]], role="factory_equipment_admin"
            ),
            headers=headers(manager),
        ).status_code
        == 422
    )
    assert (
        manager.patch(
            url,
            json={
                **change_body(row, [data.factories["B"]]),
                "expected_version": row["version"] - 1,
            },
            headers=headers(manager),
        ).status_code
        == 409
    )
    group = person(manager, data.users["group"])
    assert (
        manager.patch(
            f"/api/v1/access/users/{group['id']}",
            json=change_body(group, [], role=None),
            headers=headers(manager),
        ).status_code
        == 409
    )
    assert manager.get("/api/v1/auth/me").status_code == 200
    assert (
        manager.patch(url, json=change_body(row, [uuid4()]), headers=headers(manager)).status_code
        == 422
    )


def test_concurrent_edits_allow_one_version_and_one_audit_fact(personnel):
    manager, _, service, _, _, _, data, db = personnel
    row = person(manager, data.users["engineer"])
    token, nonce = manager.cookies.get(SESSION), manager.cookies.get(CSRF)
    barrier = Barrier(2)

    def modify(factory):
        barrier.wait(timeout=5)
        try:
            service.change(
                token,
                nonce,
                data.users["engineer"],
                AccessChange(row["version"], "engineer", True, (factory,), "SYNTH-并发测试"),
            )
            return True
        except Conflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(modify, [data.factories["B"], data.factories["EMPTY"]]))
    assert sorted(results) == [False, True]
    with Session(db.engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditRow)
                .where(AuditRow.action == "access.changed")
            )
            == 1
        )


def test_database_concurrent_grants_cannot_create_multi_factory_admin(db):
    data = seed_synthetic(db.engine)
    with Session(db.engine) as session:
        user = UserRow(role="factory_equipment_admin")
        session.add(user)
        session.commit()
        uid = user.id
    barrier = Barrier(2)

    def grant(factory):
        with Session(db.engine) as session:
            barrier.wait(timeout=5)
            session.add(FactoryAccessRow(user_id=uid, factory_id=factory))
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(grant, [data.factories["A"], data.factories["B"]])) == [False, True]
    with Session(db.engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(FactoryAccessRow)
                .where(FactoryAccessRow.user_id == uid)
            )
            == 1
        )
        with pytest.raises(IntegrityError):
            session.execute(update(UserRow).where(UserRow.id == uid).values(auth_version=0))
            session.commit()


def test_failed_audit_rolls_back_permissions_versions_and_revocation(personnel):
    manager, employee, _, _, _, _, data, db = personnel
    row = person(manager, data.users["engineer"])
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_access_audit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'synthetic failure'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER fail_access_audit BEFORE INSERT ON audit_events "
                "FOR EACH ROW EXECUTE FUNCTION fail_access_audit()"
            )
        )
    response = manager.patch(
        f"/api/v1/access/users/{row['id']}",
        json=change_body(row, [data.factories["B"]]),
        headers=headers(manager),
    )
    assert response.status_code == 503 and "synthetic failure" not in response.text
    assert employee.get("/api/v1/auth/me").status_code == 200
    assert person(manager, data.users["engineer"])["version"] == row["version"]


def test_initial_group_bootstrap_is_offline_verified_once_and_audited(personnel):
    _, _, service, _, _, _, data, db = personnel
    with db.engine.begin() as connection:
        connection.execute(
            update(UserRow)
            .where(UserRow.id.in_([data.users["group"], data.users["ungranted"]]))
            .values(role=None)
        )
    with SqlAccessUnitOfWork(db.engine) as uow:
        row = uow.person(data.users["ungranted"])
    with pytest.raises(Conflict):
        service.bootstrap(
            data.users["ungranted"], row["version"], "SYNTH-初始化", "WRONG-APP", "SYNTH-TENANT"
        )
    service.bootstrap(
        data.users["ungranted"], row["version"], "SYNTH-初始化", "SYNTH-APP", "SYNTH-TENANT"
    )
    with pytest.raises(Conflict):
        service.bootstrap(
            data.users["ungranted"], row["version"], "SYNTH-重放", "SYNTH-APP", "SYNTH-TENANT"
        )
    with Session(db.engine) as session:
        assert session.get(UserRow, data.users["ungranted"]).role == "group_lead"
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditRow)
                .where(AuditRow.action == "access.bootstrap")
            )
            == 1
        )


def test_scope_migration_rejects_inconsistent_old_rows_and_can_retry(db):
    db.migration("downgrade", "0002_feishu_sessions")
    data = seed_synthetic(db.engine)
    with Session(db.engine) as session:
        session.add(FactoryAccessRow(user_id=data.users["admin"], factory_id=data.factories["B"]))
        session.commit()
    with pytest.raises(DBAPIError):
        db.migration("upgrade", "head")
    assert "details" not in {
        column["name"] for column in inspect(db.engine).get_columns("audit_events")
    }
    with db.engine.begin() as connection:
        connection.execute(
            delete(FactoryAccessRow).where(
                FactoryAccessRow.user_id == data.users["admin"],
                FactoryAccessRow.factory_id == data.factories["B"],
            )
        )
    db.migration("upgrade", "head")
    assert "details" in {
        column["name"] for column in inspect(db.engine).get_columns("audit_events")
    }


def test_reenable_never_resurrects_the_old_cookie(personnel):
    manager, employee, _, _, codes, subjects, data, _ = personnel
    original_cookie = employee.cookies.get(SESSION)
    row = person(manager, data.users["engineer"])
    url = f"/api/v1/access/users/{row['id']}"
    assert (
        manager.patch(
            url,
            json=change_body(row, [data.factories["A"]], active=False),
            headers=headers(manager),
        ).status_code
        == 200
    )
    disabled = person(manager, data.users["engineer"])
    assert (
        manager.patch(
            url, json=change_body(disabled, [data.factories["A"]]), headers=headers(manager)
        ).status_code
        == 200
    )
    assert (
        employee.get(
            "/api/v1/auth/me", headers={"Cookie": SESSION + "=" + original_cookie}
        ).status_code
        == 401
    )
    login(employee, codes, subjects["engineer"])
    assert employee.get("/api/v1/auth/me").status_code == 200


def test_database_role_change_cannot_make_a_multi_factory_engineer_an_admin(business):
    http, data, db = business
    with Session(db.engine) as session:
        session.execute(
            update(UserRow)
            .where(UserRow.id == data.users["multi"])
            .values(role="factory_equipment_admin")
        )
        with pytest.raises(IntegrityError):
            session.commit()
    response = http.get(
        f"/api/v1/factories/{data.factories['B']}/assets",
        headers={"Authorization": "Bearer " + data.tokens["multi"]},
    )
    assert response.status_code == 200


def test_mcp_reuses_managed_account_and_factory_revocation(personnel):
    from factory_ops.application.assets import AssetQueries
    from factory_ops.application.errors import AccessDenied, Unauthenticated
    from factory_ops.application.identity import ExternalIdentity
    from factory_ops.application.mcp import ReadOnlyAssetMcp
    from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork

    manager, _, _, _, _, _, data, db = personnel

    class SyntheticProof:
        def authenticate(self, credential):
            return ExternalIdentity(
                "doubao_mcp", "synthetic-test-issuer", "SYNTH-TENANT", "SYNTH-APP", "SYNTH-SUBJECT"
            )

    tool = ReadOnlyAssetMcp(SyntheticProof(), AssetQueries(lambda: SqlReadUnitOfWork(db.engine)))
    assert (
        tool.call("search_assets", {"factory_id": str(data.factories["A"])}, "synthetic")["total"]
        == 2
    )
    row = person(manager, data.users["engineer"])
    url = f"/api/v1/access/users/{row['id']}"
    assert (
        manager.patch(
            url, json=change_body(row, [data.factories["B"]]), headers=headers(manager)
        ).status_code
        == 200
    )
    with pytest.raises(AccessDenied):
        tool.call("search_assets", {"factory_id": str(data.factories["A"])}, "synthetic")
    assert (
        tool.call("search_assets", {"factory_id": str(data.factories["B"])}, "synthetic")["total"]
        == 1
    )
    row = person(manager, data.users["engineer"])
    assert (
        manager.patch(
            url,
            json=change_body(row, [data.factories["B"]], active=False),
            headers=headers(manager),
        ).status_code
        == 200
    )
    with pytest.raises(Unauthenticated):
        tool.call("search_assets", {"factory_id": str(data.factories["B"])}, "synthetic")


def test_bootstrap_has_no_public_route_and_requires_operator_flag(client, monkeypatch):
    import sys

    from factory_ops.bootstrap_access import main

    assert client.post("/api/v1/access/bootstrap", json={}).status_code == 404
    assert client.post("/api/v1/auth/register", json={}).status_code == 404
    monkeypatch.delenv("FACTORY_OPS_ALLOW_OFFLINE_BOOTSTRAP", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bootstrap",
            str(uuid4()),
            "--expected-version",
            "1",
            "--reason",
            "SYNTH-初始化",
            "--confirm-first-group-lead",
        ],
    )
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 2


def test_simultaneous_first_lead_initialization_allows_only_one(personnel):
    _, _, service, _, _, _, data, db = personnel
    targets = [data.users["engineer"], data.users["ungranted"]]
    with db.engine.begin() as connection:
        connection.execute(
            update(UserRow).where(UserRow.id.in_([data.users["group"], *targets])).values(role=None)
        )
    with SqlAccessUnitOfWork(db.engine) as uow:
        versions = {uid: uow.person(uid)["version"] for uid in targets}
    barrier = Barrier(2)

    def promote(uid):
        barrier.wait(timeout=5)
        try:
            service.bootstrap(uid, versions[uid], "SYNTH-并发初始化", "SYNTH-APP", "SYNTH-TENANT")
            return True
        except Conflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(promote, targets)) == [False, True]
    with Session(db.engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(UserRow)
                .where(UserRow.role == "group_lead", UserRow.active.is_(True))
            )
            == 1
        )


def test_downgrade_refuses_to_erase_populated_access_audit(personnel):
    manager, _, _, _, _, _, data, db = personnel
    row = person(manager, data.users["engineer"])
    response = manager.patch(
        f"/api/v1/access/users/{row['id']}",
        json=change_body(row, [data.factories["B"]]),
        headers=headers(manager),
    )
    assert response.status_code == 200
    with pytest.raises(DBAPIError):
        db.migration("downgrade", "0002_feishu_sessions")
    assert "details" in {
        column["name"] for column in inspect(db.engine).get_columns("audit_events")
    }
    with Session(db.engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditRow)
                .where(AuditRow.action == "access.changed")
            )
            == 1
        )


def test_invalid_database_configuration_does_not_echo_credentials(monkeypatch):
    from factory_ops.bootstrap import configured_app

    private_value = "SYNTH-private-configuration-value"
    monkeypatch.setenv("DATABASE_URL", "invalid " + private_value)
    with pytest.raises(ValueError) as result:
        configured_app()
    exposed = private_value in str(result.value)
    assert not exposed
