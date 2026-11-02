"""Controlled initialization, shared IAM constraints, audit rollback and concurrency."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from factory_ops.application.access import AccessChange
from factory_ops.application.errors import (
    AccessDenied,
    Conflict,
    InvalidRequest,
    StorageUnavailable,
)
from factory_ops.application.mcp_access import McpAccessService
from factory_ops.infrastructure.database.mcp_access import SqlMcpAccessUnitOfWork
from factory_ops.infrastructure.database.models import AuditRow, ExternalIdentityRow, UserRow


@pytest.fixture
def controlled(db, signed_identity):
    provider, token, _ = signed_identity
    service = McpAccessService(lambda: SqlMcpAccessUnitOfWork(db.engine))
    return service, provider, token, db


def test_first_lead_pending_duplicate_authorization_unbinding(controlled):
    service, provider, token, db = controlled
    lead = provider.authenticate(token())
    pending = service.bind(lead, "SYNTH-受控人员核对")
    assert pending["role"] is None
    assert not pending["factories"]
    with pytest.raises(Conflict):
        service.bind(lead, "SYNTH-禁止重复绑定")
    first = service.bootstrap(lead, pending["version"], "SYNTH-首位负责人")
    assert first["role"] == "group_lead"
    with pytest.raises(Conflict):
        service.bootstrap(lead, first["version"], "SYNTH-禁止第二次初始化")
    employee = provider.authenticate(token(user_id=7620000000000000099))
    with pytest.raises(AccessDenied):
        service.bind(employee, "SYNTH-已有负责人后拒绝无审批绑定")
    second = service.bind(employee, "SYNTH-负责人核对身份", actor_identity=lead)
    granted = service.grant(
        lead,
        second["id"],
        AccessChange(second["version"], "engineer", True, (), "SYNTH-授予工程师无工厂"),
    )
    assert granted["user"]["role"] == "engineer"
    with pytest.raises(AccessDenied):
        service.grant(
            employee,
            first["id"],
            AccessChange(first["version"], "engineer", True, (), "SYNTH-非负责人拒绝"),
        )
    unbound = service.unbind(lead, second["id"], granted["user"]["version"], "SYNTH-身份解绑")
    with SqlMcpAccessUnitOfWork(db.engine) as uow:
        assert uow.resolve_identity(employee) is None
    with pytest.raises(Conflict):
        service.bind(employee, "SYNTH-不可自动恢复解绑", actor_identity=lead)
    with pytest.raises(Conflict):
        service.unbind(lead, first["id"], first["version"], "SYNTH-保留最后负责人")
    assert unbound["version"] > granted["user"]["version"]
    with Session(db.engine) as session:
        rows = session.scalars(select(AuditRow).where(AuditRow.action.startswith("access."))).all()
        assert {
            "access.mcp_bound",
            "access.bootstrap_mcp",
            "access.changed",
            "access.mcp_unbound",
        } <= {r.action for r in rows}
        assert all(r.details for r in rows)


def test_attach_requires_existing_lead_approval_and_expected_version(controlled):
    service, provider, token, db = controlled
    lead = provider.authenticate(token())
    pending = service.bind(lead, "SYNTH-初始化")
    first = service.bootstrap(lead, pending["version"], "SYNTH-负责人")
    identity = provider.authenticate(token(user_id=7620000000000000099))
    with pytest.raises(AccessDenied):
        service.bind(
            identity, "SYNTH-拒绝无审批接管", target=first["id"], expected=first["version"]
        )
    with pytest.raises(Conflict):
        service.bind(
            identity, "SYNTH-拒绝旧版本", actor_identity=lead, target=first["id"], expected=1
        )
    attached = service.bind(
        identity,
        "SYNTH-核对两个身份为同一人",
        actor_identity=lead,
        target=first["id"],
        expected=first["version"],
    )
    assert attached["id"] == first["id"]
    with SqlMcpAccessUnitOfWork(db.engine) as uow:
        assert uow.resolve_identity(identity) == first["id"]
    assert attached["version"] > first["version"]


def test_first_lead_concurrency_serializes(controlled):
    service, provider, token, db = controlled
    identities = [provider.authenticate(token(user_id=7620000000000000001 + i)) for i in range(2)]
    pending = [service.bind(identity, "SYNTH-待授权") for identity in identities]
    barrier = Barrier(2)

    def promote(index):
        barrier.wait(timeout=5)
        try:
            service.bootstrap(identities[index], pending[index]["version"], "SYNTH-并发首位初始化")
            return True
        except Conflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(promote, range(2))) == [False, True]
    with Session(db.engine) as session:
        assert (
            session.scalar(
                select(func.count()).select_from(UserRow).where(UserRow.role == "group_lead")
            )
            == 1
        )


def test_offline_grant_uses_same_factory_constraints_and_disable(business, signed_identity):
    _, data, db = business
    provider, token, _ = signed_identity
    service = McpAccessService(lambda: SqlMcpAccessUnitOfWork(db.engine))
    lead, engineer = [
        provider.authenticate(token(user_id=7620000000000000001 + i)) for i in range(2)
    ]
    with Session(db.engine) as session:
        for identity, uid in [(lead, data.users["group"]), (engineer, data.users["engineer"])]:
            session.add(
                ExternalIdentityRow(
                    user_id=uid,
                    provider=identity.provider,
                    issuer=identity.issuer,
                    tenant_id=identity.tenant_id,
                    app_id=identity.app_id,
                    subject_id=identity.subject_id,
                )
            )
        session.commit()
    with SqlMcpAccessUnitOfWork(db.engine) as uow:
        person = uow.person(data.users["engineer"])
    with pytest.raises(InvalidRequest):
        AccessChange(
            person["version"],
            "factory_equipment_admin",
            True,
            (data.factories["A"], data.factories["B"]),
            "SYNTH-拒绝管理员跨厂",
        )
    change = AccessChange(
        person["version"],
        "engineer",
        True,
        (data.factories["A"], data.factories["B"]),
        "SYNTH-工程师跨厂审批",
    )
    granted = service.grant(lead, person["id"], change)["user"]
    assert len(granted["factories"]) == 2
    with pytest.raises(Conflict):
        service.grant(lead, person["id"], change)
    service.grant(
        lead,
        person["id"],
        AccessChange(
            granted["version"], "engineer", False, (data.factories["A"],), "SYNTH-人员离职停用"
        ),
    )
    with SqlMcpAccessUnitOfWork(db.engine) as uow:
        assert uow.resolve_identity(engineer) is None


def test_bind_and_audit_rollback_together(controlled):
    service, provider, token, db = controlled

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO audit_events"):
            raise OperationalError("synthetic failure", {}, Exception())

    event.listen(db.engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(StorageUnavailable):
            service.bind(provider.authenticate(token()), "SYNTH-审计故障")
    finally:
        event.remove(db.engine, "before_cursor_execute", fail)
    with Session(db.engine) as session:
        assert session.scalar(select(func.count()).select_from(UserRow)) == 0
        assert session.scalar(select(func.count()).select_from(ExternalIdentityRow)) == 0


def test_private_credential_file_and_operator_flag(tmp_path, monkeypatch):
    import sys

    from factory_ops.bootstrap_mcp_access import main, private_credential

    path = tmp_path / "credential"
    path.write_text("synthetic-placeholder")
    path.chmod(0o644)
    with pytest.raises(ValueError):
        private_credential(path)
    path.chmod(0o600)
    assert private_credential(path) == "synthetic-placeholder"
    link = tmp_path / "symlink"
    link.symlink_to(path)
    with pytest.raises(OSError):
        private_credential(link)
    monkeypatch.delenv("FACTORY_OPS_ALLOW_OFFLINE_BOOTSTRAP", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "offline",
            "bind",
            "--identity-file",
            str(path),
            "--reason",
            "SYNTH-拒绝未授权操作",
            "--confirm-offline-change",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_bootstrap_web_configuration_is_independent_and_fail_closed(monkeypatch, client):
    from factory_ops.bootstrap import configured_app

    assert client.post("/mcp", json={}).status_code == 503
    assert client.post("/api/v1/access/mcp/register", json={}).status_code == 404
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://invalid.invalid/test")
    monkeypatch.setenv("FACTORY_OPS_MCP_ENABLED", "1")
    monkeypatch.setenv("FACTORY_OPS_MCP_PUBLIC_ORIGIN", "http://unsafe.invalid")
    with pytest.raises(ValueError, match="HTTPS origin"):
        configured_app()
    monkeypatch.setenv("FACTORY_OPS_MCP_PUBLIC_ORIGIN", "https://ops.example.invalid")
    with pytest.raises(ValueError, match="controlled Aily"):
        configured_app()
