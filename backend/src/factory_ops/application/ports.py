"""Ports owned by the application. Channels share one query service and authorization path."""

from collections.abc import Callable
from typing import Literal, Protocol, Self
from uuid import UUID

from factory_ops.application.identity import IdentityReference
from factory_ops.domain.assets import Asset, AssetPage, Factory
from factory_ops.domain.authorization import Principal

Channel = Literal["api", "doubao_mcp"]


class ReadUnitOfWork(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...
    def resolve_identity(self, identity: IdentityReference) -> UUID | None: ...
    def load_principal(self, user_id: UUID) -> Principal | None: ...
    def factories(self, principal: Principal) -> tuple[Factory, ...]: ...
    def factory_exists(self, factory_id: UUID) -> bool: ...
    def search_assets(
        self,
        factory_id: UUID,
        q: str,
        category: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> AssetPage: ...
    def get_asset(self, factory_id: UUID, asset_id: UUID) -> Asset | None: ...
    def audit(
        self,
        actor_id: UUID,
        factory_id: UUID | None,
        resource_id: UUID | None,
        action: str,
        outcome: str,
        channel: Channel,
    ) -> None: ...
    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], ReadUnitOfWork]
