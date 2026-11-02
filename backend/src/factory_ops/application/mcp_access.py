"""Controlled offline enrollment/authorization; never exposed as an HTTP or MCP tool."""

from typing import Protocol
from uuid import UUID

from factory_ops.application.access import AccessChange, AccessService, AccessUnitOfWork
from factory_ops.application.errors import AccessDenied, Conflict, InvalidRequest, Unauthenticated
from factory_ops.application.identity import ExternalIdentity
from factory_ops.domain.authorization import can_manage_access


class McpAccessUnitOfWork(AccessUnitOfWork, Protocol):
    def bind_mcp(self, identity: ExternalIdentity, target: UUID | None, expected: int | None): ...
    def unbind_mcp(self, target: UUID): ...
    def audit_mcp_binding(self, actor: UUID, target: UUID, binding: UUID, reason: str): ...


class McpAccessService:
    def __init__(self, uow):
        self.uow = uow

    @staticmethod
    def _actor(uow, identity):
        actor = uow.resolve_identity(identity)
        if actor is None:
            raise Unauthenticated
        principal = uow.load_principal(actor)
        if principal is None or not can_manage_access(principal):
            raise AccessDenied
        return actor

    @staticmethod
    def _reason(reason):
        if not isinstance(reason, str) or not 2 <= len(reason.strip()) <= 300:
            raise InvalidRequest

    def bind(self, identity, reason, *, actor_identity=None, target=None, expected=None):
        self._reason(reason)
        if not isinstance(identity, ExternalIdentity) or identity.provider != "doubao_mcp":
            raise InvalidRequest
        with self.uow() as uow:
            uow.lock_lifecycle()
            # Before a first lead exists, the privileged operator may enroll ONLY a new pending
            # account. Existing users cannot be taken over by this initialization exception.
            if actor_identity is None:
                if uow.active_group_count() or target is not None:
                    raise AccessDenied
                actor = None
            else:
                actor = self._actor(uow, actor_identity)
            uid, binding = uow.bind_mcp(identity, target, expected)
            uow.audit_mcp_binding(actor or uid, uid, binding, reason.strip())
            result = uow.person(uid)
            uow.commit()
            return result

    def bootstrap(self, identity, expected, reason):
        self._reason(reason)
        if not isinstance(identity, ExternalIdentity) or identity.provider != "doubao_mcp":
            raise InvalidRequest
        with self.uow() as uow:
            uow.lock_lifecycle()
            uid = uow.resolve_identity(identity)
            before = uow.person(uid) if uid else None
            if (
                not before
                or before["role"] is not None
                or not before["active"]
                or before["version"] != expected
                or uow.active_group_count()
            ):
                raise Conflict
            uow.persist_access(uid, AccessChange(expected, "group_lead", True, (), reason))
            after = uow.person(uid)
            uow.audit_access(uid, uid, "access.bootstrap_mcp", before, after, reason.strip())
            uow.commit()
            return after

    def grant(self, actor_identity, target, change: AccessChange):
        with self.uow() as uow:
            uow.lock_lifecycle()
            actor = self._actor(uow, actor_identity)
            return AccessService.apply_change(uow, actor, target, change)

    def unbind(self, actor_identity, target, expected, reason):
        self._reason(reason)
        with self.uow() as uow:
            uow.lock_lifecycle()
            actor = self._actor(uow, actor_identity)
            before = uow.person(target)
            if (
                not before
                or before["version"] != expected
                or before["role"] == "group_lead"
                and before["active"]
                and uow.active_group_count() <= 1
            ):
                raise Conflict
            uow.unbind_mcp(target)
            after = uow.person(target)
            uow.audit_access(actor, target, "access.mcp_unbound", before, after, reason.strip())
            uow.commit()
            return after
