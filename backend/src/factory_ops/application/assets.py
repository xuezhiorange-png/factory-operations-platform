"""Read-only asset use cases, shared by HTTP and the future MCP adapter."""

from dataclasses import dataclass
from uuid import UUID

from factory_ops.application.errors import AccessDenied, InvalidRequest, NotFound, Unauthenticated
from factory_ops.application.identity import IdentityReference
from factory_ops.application.ports import Channel, ReadUnitOfWork, UnitOfWorkFactory
from factory_ops.domain.assets import Asset as Asset
from factory_ops.domain.assets import AssetPage as AssetPage
from factory_ops.domain.assets import Factory as Factory
from factory_ops.domain.authorization import Principal, can_access_factory

CATEGORIES = frozenset({"refrigeration", "processing", "utilities", "other"})
STATUSES = frozenset({"pending", "in_use", "inactive", "retired"})


@dataclass(frozen=True)
class AssetSearch:
    q: str = ""
    category: str | None = None
    status: str | None = None
    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.q, str)
            or len(self.q) > 100
            or self.category is not None
            and self.category not in CATEGORIES
            or self.status is not None
            and self.status not in STATUSES
            or type(self.limit) is not int
            or not 1 <= self.limit <= 100
            or type(self.offset) is not int
            or not 0 <= self.offset <= 100000
        ):
            raise InvalidRequest


class AssetQueries:
    def __init__(self, unit_of_work: UnitOfWorkFactory) -> None:
        self.unit_of_work = unit_of_work

    def _principal(
        self,
        uow: ReadUnitOfWork,
        identity: IdentityReference,
        factory_id: UUID | None,
        action: str,
        channel: Channel,
    ) -> Principal:
        actor_id = uow.resolve_identity(identity)
        if actor_id is None:
            raise Unauthenticated
        # Resolve role/grants on every call. Never reuse JWT roles or a cached Principal.
        principal = uow.load_principal(actor_id)
        if (
            principal is None
            or factory_id is not None
            and not can_access_factory(principal, factory_id)
        ):
            uow.audit(actor_id, factory_id, None, action, "denied", channel)
            uow.commit()
            raise AccessDenied
        return principal

    def list_factories(
        self,
        identity: IdentityReference,
        channel: Channel = "api",
    ) -> tuple[Factory, ...]:
        with self.unit_of_work() as uow:
            principal = self._principal(uow, identity, None, "factories.list", channel)
            result = uow.factories(principal)
            uow.audit(principal.user_id, None, None, "factories.list", "allowed", channel)
            uow.commit()
            return result

    def search_assets(
        self,
        identity: IdentityReference,
        factory_id: UUID,
        query: AssetSearch,
        channel: Channel = "api",
    ) -> AssetPage:
        with self.unit_of_work() as uow:
            principal = self._principal(uow, identity, factory_id, "assets.search", channel)
            if not uow.factory_exists(factory_id):
                raise NotFound
            result = uow.search_assets(
                factory_id,
                query.q.strip(),
                query.category,
                query.status,
                query.limit,
                query.offset,
            )
            uow.audit(principal.user_id, factory_id, None, "assets.search", "allowed", channel)
            uow.commit()
            return result

    def get_asset_detail(
        self,
        identity: IdentityReference,
        factory_id: UUID,
        asset_id: UUID,
        channel: Channel = "api",
    ) -> Asset:
        with self.unit_of_work() as uow:
            principal = self._principal(uow, identity, factory_id, "assets.get", channel)
            result = uow.get_asset(factory_id, asset_id)
            if result is None or not uow.factory_exists(factory_id):
                raise NotFound
            uow.audit(principal.user_id, factory_id, asset_id, "assets.get", "allowed", channel)
            uow.commit()
            return result
