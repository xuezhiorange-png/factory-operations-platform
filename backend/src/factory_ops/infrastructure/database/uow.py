"""One fresh SQLAlchemy Session per use case, with fail-closed errors and audit commit."""

from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID

from sqlalchemy import Engine, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from factory_ops.application.errors import StorageUnavailable
from factory_ops.application.identity import ExternalIdentity, IdentityReference, SessionIdentity
from factory_ops.application.ports import Channel
from factory_ops.domain.assets import Asset, AssetPage, Factory
from factory_ops.domain.authorization import ManagementRole, Principal
from factory_ops.infrastructure.database.models import (
    AssetRow,
    AuditRow,
    ExternalIdentityRow,
    FactoryAccessRow,
    FactoryRow,
    SessionRow,
    UserRow,
)


def asset_dto(row: AssetRow) -> Asset:
    return Asset(**{field: getattr(row, field) for field in Asset.__dataclass_fields__})


class SqlReadUnitOfWork:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def __enter__(self) -> "SqlReadUnitOfWork":
        self.session = Session(self.engine, expire_on_commit=False)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self.session.rollback()
        finally:
            self.session.close()
        if isinstance(exc, SQLAlchemyError):
            # Never return SQL, connection strings, credential material or driver errors.
            raise StorageUnavailable from None

    def resolve_identity(self, identity: IdentityReference) -> UUID | None:
        if isinstance(identity, SessionIdentity):
            statement = (
                select(SessionRow.user_id)
                .join(UserRow)
                .where(
                    SessionRow.token_hash == identity.token_hash,
                    SessionRow.revoked_at.is_(None),
                    SessionRow.issued_at <= datetime.now(UTC),
                    SessionRow.expires_at > datetime.now(UTC),
                    UserRow.active.is_(True),
                )
            )
        elif isinstance(identity, ExternalIdentity):
            statement = (
                select(ExternalIdentityRow.user_id)
                .join(UserRow)
                .where(
                    ExternalIdentityRow.provider == identity.provider,
                    ExternalIdentityRow.issuer == identity.issuer,
                    ExternalIdentityRow.tenant_id == identity.tenant_id,
                    ExternalIdentityRow.app_id == identity.app_id,
                    ExternalIdentityRow.subject_id == identity.subject_id,
                    ExternalIdentityRow.active.is_(True),
                    UserRow.active.is_(True),
                )
            )
        else:
            return None
        return self.session.scalar(statement)

    def load_principal(self, user_id: UUID) -> Principal | None:
        user = self.session.get(UserRow, user_id)
        if user is None or not user.active or user.role is None:
            return None
        grants = frozenset(
            self.session.scalars(
                select(FactoryAccessRow.factory_id).where(
                    FactoryAccessRow.user_id == user_id,
                )
            )
        )
        try:
            return Principal(user_id, ManagementRole(user.role), grants)
        except ValueError:
            # Inconsistent multi-factory admin grants or unknown roles never broaden access.
            return None

    def factories(self, principal: Principal) -> tuple[Factory, ...]:
        statement = select(FactoryRow).where(FactoryRow.active.is_(True))
        if principal.role is not ManagementRole.GROUP_LEAD:
            statement = statement.where(FactoryRow.id.in_(principal.factory_ids))
        return tuple(
            Factory(r.id, r.code, r.name)
            for r in self.session.scalars(statement.order_by(FactoryRow.code))
        )

    def factory_exists(self, factory_id: UUID) -> bool:
        return (
            self.session.scalar(
                select(FactoryRow.id).where(
                    FactoryRow.id == factory_id,
                    FactoryRow.active.is_(True),
                )
            )
            is not None
        )

    def search_assets(
        self,
        factory_id: UUID,
        q: str,
        category: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> AssetPage:
        filters = [AssetRow.factory_id == factory_id]
        if q:
            filters.append(
                or_(
                    AssetRow.name.icontains(q, autoescape=True),
                    AssetRow.asset_code.icontains(q, autoescape=True),
                )
            )
        if category:
            filters.append(AssetRow.category == category)
        if status:
            filters.append(AssetRow.status == status)
        count = self.session.scalar(select(func.count()).select_from(AssetRow).where(*filters)) or 0
        rows = self.session.scalars(
            select(AssetRow)
            .where(*filters)
            .order_by(
                AssetRow.asset_code,
                AssetRow.id,
            )
            .limit(limit)
            .offset(offset)
        )
        return AssetPage(tuple(asset_dto(row) for row in rows), count, limit, offset)

    def get_asset(self, factory_id: UUID, asset_id: UUID) -> Asset | None:
        row = self.session.scalar(
            select(AssetRow).where(
                AssetRow.factory_id == factory_id,
                AssetRow.id == asset_id,
            )
        )
        return asset_dto(row) if row is not None else None

    def audit(
        self,
        actor_id: UUID,
        factory_id: UUID | None,
        resource_id: UUID | None,
        action: str,
        outcome: str,
        channel: Channel,
    ) -> None:
        self.session.add(
            AuditRow(
                actor_id=actor_id,
                factory_id=factory_id,
                resource_id=resource_id,
                action=action,
                outcome=outcome,
                channel=channel,
            )
        )

    def commit(self) -> None:
        self.session.commit()
