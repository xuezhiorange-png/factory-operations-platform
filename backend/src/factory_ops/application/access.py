"""Three-role personnel management, using only server-verified actors and current grants."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from factory_ops.application.auth import AuthUnitOfWork
from factory_ops.application.errors import AccessDenied, Conflict, InvalidRequest, NotFound
from factory_ops.domain.authorization import ManagementRole, can_manage_access


@dataclass(frozen=True)
class AccessChange:
    expected_version: int
    role: str | None
    active: bool
    factory_ids: tuple[UUID, ...]
    reason: str

    def __post_init__(self):
        if (
            type(self.expected_version) is not int
            or self.expected_version < 1
            or type(self.active) is not bool
            or self.role not in {None, *ManagementRole}
            or len(set(self.factory_ids)) != len(self.factory_ids)
            or len(self.factory_ids) > 100
            or not 2 <= len(self.reason.strip()) <= 300
            or self.role in {None, ManagementRole.GROUP_LEAD}
            and self.factory_ids
            or self.role == ManagementRole.FACTORY_EQUIPMENT_ADMIN
            and len(self.factory_ids) > 1
        ):
            raise InvalidRequest


class AccessUnitOfWork(AuthUnitOfWork, Protocol):
    def lock_lifecycle(self) -> None: ...
    def authenticated_user(self, token: str) -> UUID: ...
    def people(self, limit: int, offset: int) -> dict: ...
    def person(self, user_id: UUID) -> dict | None: ...
    def persist_access(self, user_id: UUID, change: AccessChange) -> None: ...
    def active_group_count(self) -> int: ...
    def access_history(self, user_id: UUID, limit: int, offset: int) -> dict: ...
    def revoke_all(self, user_id: UUID) -> None: ...
    def unbind_feishu(self, user_id: UUID) -> None: ...
    def has_verified_feishu(self, user_id: UUID, app: str, tenant: str) -> bool: ...
    def audit_access(
        self, actor: UUID, target: UUID, action: str, before: dict, after: dict, reason: str
    ) -> None: ...


class AccessService:
    def __init__(self, uow: Callable[[], AccessUnitOfWork]):
        self.uow = uow

    @staticmethod
    def _actor(uow: AccessUnitOfWork, token: str) -> UUID:
        uid = uow.authenticated_user(token)
        principal = uow.load_principal(uid)
        if principal is None or not can_manage_access(principal):
            uow.audit(uid, None, None, "access.manage", "denied", "api")
            uow.commit()
            raise AccessDenied
        return uid

    def list_people(self, token: str, limit: int, offset: int) -> dict:
        with self.uow() as uow:
            self._actor(uow, token)
            return uow.people(limit, offset)

    def history(self, token: str, target: UUID, limit: int, offset: int) -> dict:
        with self.uow() as uow:
            self._actor(uow, token)
            if not uow.person(target):
                raise NotFound
            return uow.access_history(target, limit, offset)

    def change(self, token: str, csrf: str, target: UUID, change: AccessChange) -> dict:
        with self.uow() as uow:
            uow.lock_lifecycle()
            uow.require_csrf(token, csrf)
            actor = self._actor(uow, token)
            before = uow.person(target)
            if before is None:
                raise NotFound
            if before["version"] != change.expected_version:
                raise Conflict
            for factory in change.factory_ids:
                if not uow.factory_exists(factory):
                    raise InvalidRequest
            if (
                before["role"] == "group_lead"
                and before["active"]
                and (change.role != "group_lead" or not change.active)
                and uow.active_group_count() <= 1
            ):
                raise Conflict
            previous_ids = {factory.id for factory in before["factories"]}
            if (
                before["role"] == change.role
                and before["active"] == change.active
                and previous_ids == set(change.factory_ids)
            ):
                raise Conflict
            uow.persist_access(target, change)
            after = uow.person(target)
            uow.audit_access(actor, target, "access.changed", before, after, change.reason.strip())
            uow.commit()
            return {"user": after, "reauthentication_required": actor == target}

    def lifecycle(
        self, token: str, csrf: str, target: UUID, expected: int, reason: str, *, unbind=False
    ) -> dict:
        if type(expected) is not int or expected < 1 or not 2 <= len(reason.strip()) <= 300:
            raise InvalidRequest
        with self.uow() as uow:
            uow.lock_lifecycle()
            uow.require_csrf(token, csrf)
            actor = self._actor(uow, token)
            before = uow.person(target)
            if before is None:
                raise NotFound
            if before["version"] != expected:
                raise Conflict
            if unbind:
                if before["feishu_binding"] != "bound":
                    raise Conflict
                uow.unbind_feishu(target)
            else:
                uow.revoke_all(target)
            after = uow.person(target)
            uow.audit_access(
                actor,
                target,
                "access.feishu_unbound" if unbind else "access.sessions_revoked",
                before,
                after,
                reason.strip(),
            )
            uow.commit()
            return {"user": after, "reauthentication_required": actor == target}

    def bootstrap(self, target: UUID, expected: int, reason: str, app: str, tenant: str):
        """Offline operator use only, with an existing verified pending identity; no HTTP route."""
        with self.uow() as uow:
            uow.lock_lifecycle()
            before = uow.person(target)
            if before is None:
                raise NotFound
            if (
                uow.active_group_count()
                or before["role"] is not None
                or not before["active"]
                or before["version"] != expected
                or not uow.has_verified_feishu(target, app, tenant)
            ):
                raise Conflict
            uow.persist_access(target, AccessChange(expected, "group_lead", True, (), reason))
            after = uow.person(target)
            uow.audit_access(target, target, "access.bootstrap", before, after, reason.strip())
            uow.commit()
