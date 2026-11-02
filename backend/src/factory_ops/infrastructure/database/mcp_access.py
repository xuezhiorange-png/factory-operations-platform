"""MCP bindings use the existing users, identity uniqueness, lifecycle lock and audit tables."""

from sqlalchemy import select, update

from factory_ops.application.errors import Conflict
from factory_ops.infrastructure.database.access import SqlAccessUnitOfWork
from factory_ops.infrastructure.database.models import AuditRow, ExternalIdentityRow, UserRow


class SqlMcpAccessUnitOfWork(SqlAccessUnitOfWork):
    def bind_mcp(self, identity, target, expected):
        binding = self.session.scalar(
            select(ExternalIdentityRow).where(
                ExternalIdentityRow.provider == identity.provider,
                ExternalIdentityRow.issuer == identity.issuer,
                ExternalIdentityRow.tenant_id == identity.tenant_id,
                ExternalIdentityRow.app_id == identity.app_id,
                ExternalIdentityRow.subject_id == identity.subject_id,
            )
        )
        # Never silently move/reactivate/rebind an identity, including a previously unbound row.
        if binding is not None:
            raise Conflict
        if target is None:
            user = UserRow(role=None)
            self.session.add(user)
            self.session.flush()
        else:
            user = self.session.scalar(
                select(UserRow).where(UserRow.id == target).with_for_update()
            )
            if user is None or not user.active or user.version != expected:
                raise Conflict
        binding = ExternalIdentityRow(
            user_id=user.id,
            provider=identity.provider,
            issuer=identity.issuer,
            tenant_id=identity.tenant_id,
            app_id=identity.app_id,
            subject_id=identity.subject_id,
        )
        self.session.add(binding)
        self.session.flush()
        # An INSERT binding does not invoke the historical update/delete trigger. Explicitly
        # invalidate any existing sessions and advance the optimistic version on attachment.
        self.revoke_all(user.id)
        return user.id, binding.id

    def unbind_mcp(self, target):
        result = self.session.execute(
            update(ExternalIdentityRow)
            .where(
                ExternalIdentityRow.user_id == target,
                ExternalIdentityRow.provider == "doubao_mcp",
                ExternalIdentityRow.active.is_(True),
            )
            .values(active=False)
        )
        if not result.rowcount:
            raise Conflict

    def audit_mcp_binding(self, actor, target, binding, reason):
        self.session.add(
            AuditRow(
                actor_id=actor,
                resource_id=target,
                action="access.mcp_bound",
                outcome="allowed",
                channel="doubao_mcp",
                details={"binding_id": str(binding), "provider": "doubao_mcp", "reason": reason},
            )
        )
