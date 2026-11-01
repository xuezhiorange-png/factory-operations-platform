"""Personnel persistence, with trigger-enforced scope and session invalidation."""

from sqlalchemy import delete, func, select, update

from factory_ops.application.access import AccessChange
from factory_ops.domain.assets import Factory
from factory_ops.infrastructure.database.auth import SqlAuthUnitOfWork
from factory_ops.infrastructure.database.models import (
    AuditRow,
    ExternalIdentityRow,
    FactoryAccessRow,
    FactoryRow,
    UserRow,
)


class SqlAccessUnitOfWork(SqlAuthUnitOfWork):
    def authenticated_user(self, token):
        return self.session_record(token).user_id

    def person(self, user_id):
        user = self.session.scalar(
            select(UserRow).where(UserRow.id == user_id).execution_options(populate_existing=True)
        )
        if user is None:
            return None
        factories = tuple(
            Factory(row.id, row.code, row.name)
            for row in self.session.scalars(
                select(FactoryRow)
                .join(FactoryAccessRow)
                .where(FactoryAccessRow.user_id == user_id)
                .order_by(FactoryRow.code)
            )
        )
        bindings = self.session.scalars(
            select(ExternalIdentityRow).where(
                ExternalIdentityRow.user_id == user_id, ExternalIdentityRow.provider == "feishu"
            )
        ).all()
        return {
            "id": user.id,
            "display_name": user.display_name or "账号 " + str(user.id)[:8],
            "role": user.role,
            "active": user.active,
            "factories": factories,
            "feishu_binding": "bound"
            if any(row.active for row in bindings)
            else "unbound"
            if bindings
            else "none",
            "version": user.version,
        }

    def people(self, limit, offset):
        ids = self.session.scalars(
            select(UserRow.id).order_by(UserRow.created_at, UserRow.id).limit(limit).offset(offset)
        )
        return {
            "items": [self.person(uid) for uid in ids],
            "total": self.session.scalar(select(func.count()).select_from(UserRow)),
            "limit": limit,
            "offset": offset,
        }

    def persist_access(self, user_id, change: AccessChange):
        self.session.execute(delete(FactoryAccessRow).where(FactoryAccessRow.user_id == user_id))
        self.session.execute(
            update(UserRow)
            .where(UserRow.id == user_id)
            .values(role=change.role, active=change.active)
        )
        self.session.add_all(
            FactoryAccessRow(user_id=user_id, factory_id=factory) for factory in change.factory_ids
        )
        self.session.flush()

    def active_group_count(self):
        return self.session.scalar(
            select(func.count())
            .select_from(UserRow)
            .where(UserRow.active.is_(True), UserRow.role == "group_lead")
        )

    def access_history(self, user_id, limit, offset):
        scope = [
            AuditRow.resource_id == user_id,
            AuditRow.action.startswith("access."),
            AuditRow.outcome == "allowed",
        ]
        rows = self.session.scalars(
            select(AuditRow)
            .where(*scope)
            .order_by(AuditRow.occurred_at.desc(), AuditRow.id)
            .limit(limit)
            .offset(offset)
        )
        return {
            "items": [
                {
                    "id": row.id,
                    "actor_id": row.actor_id,
                    "action": row.action,
                    "occurred_at": row.occurred_at,
                    "details": row.details,
                }
                for row in rows
            ],
            "total": self.session.scalar(select(func.count()).select_from(AuditRow).where(*scope)),
            "limit": limit,
            "offset": offset,
        }

    def revoke_all(self, user_id):
        self.session.execute(
            update(UserRow)
            .where(UserRow.id == user_id)
            .values(auth_version=UserRow.auth_version + 1, version=UserRow.version + 1)
        )

    def unbind_feishu(self, user_id):
        self.session.execute(
            update(ExternalIdentityRow)
            .where(
                ExternalIdentityRow.user_id == user_id,
                ExternalIdentityRow.provider == "feishu",
                ExternalIdentityRow.active.is_(True),
            )
            .values(active=False)
        )

    def has_verified_feishu(self, user_id, app, tenant):
        return (
            self.session.scalar(
                select(ExternalIdentityRow.id).where(
                    ExternalIdentityRow.user_id == user_id,
                    ExternalIdentityRow.provider == "feishu",
                    ExternalIdentityRow.issuer == "https://open.feishu.cn",
                    ExternalIdentityRow.app_id == app,
                    ExternalIdentityRow.tenant_id == tenant,
                    ExternalIdentityRow.active.is_(True),
                )
            )
            is not None
        )

    def audit_access(self, actor, target, action, before, after, reason):
        def snapshot(person):
            return {
                "role": person["role"],
                "active": person["active"],
                "factory_ids": [str(f.id) for f in person["factories"]],
                "feishu_binding": person["feishu_binding"],
                "version": person["version"],
            }

        self.session.add(
            AuditRow(
                actor_id=actor,
                resource_id=target,
                action=action,
                outcome="allowed",
                channel="api",
                details={"before": snapshot(before), "after": snapshot(after), "reason": reason},
            )
        )
