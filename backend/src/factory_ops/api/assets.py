"""Allowlisted, factory-scoped HTTP read contracts. No business mutation routes."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from factory_ops.application.assets import AssetQueries, AssetSearch
from factory_ops.application.errors import StorageUnavailable, Unauthenticated
from factory_ops.application.identity import IdentityReference, SessionIdentityProvider

router = APIRouter(tags=["assets-read"])
bearer_scheme = HTTPBearer(auto_error=False, scheme_name="OpaqueSessionBearer")
cookie_scheme = APIKeyCookie(
    name="factory_ops_session", auto_error=False, scheme_name="PlatformSession"
)


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class FactoryResponse(PublicModel):
    id: UUID
    code: str
    name: str


class FactoryListResponse(PublicModel):
    items: list[FactoryResponse]
    data_source: Literal["configured_database", "synthetic_test"]


class AssetResponse(PublicModel):
    id: UUID
    factory_id: UUID
    asset_code: str
    name: str
    category: Literal["refrigeration", "processing", "utilities", "other"]
    location: str | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    status: Literal["pending", "in_use", "inactive", "retired"]
    version: int
    created_at: datetime
    updated_at: datetime


class AssetListResponse(PublicModel):
    items: list[AssetResponse]
    total: int
    limit: int
    offset: int
    data_source: Literal["configured_database", "synthetic_test"]


class AssetDetailResponse(PublicModel):
    asset: AssetResponse
    data_source: Literal["configured_database", "synthetic_test"]


def identity(
    request: Request,
    parsed_bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session_cookie: Annotated[str | None, Depends(cookie_scheme)],
) -> IdentityReference:
    header = request.headers.get("authorization")
    cookie = session_cookie
    bearer = None
    if header:
        scheme, _, bearer = header.partition(" ")
        if scheme.lower() != "bearer" or not bearer or parsed_bearer is None:
            raise Unauthenticated
    if bearer and cookie and bearer != cookie:
        raise Unauthenticated
    credential = bearer or cookie
    if credential is None:
        raise Unauthenticated
    return SessionIdentityProvider().authenticate(credential)


def queries(request: Request) -> AssetQueries:
    factory: Callable[[], AssetQueries] | None = request.app.state.asset_queries
    if factory is None:
        raise StorageUnavailable
    return factory()


def source(request: Request) -> str:
    return request.app.state.data_source


def reject_unknown_query(request: Request, allowed: frozenset[str]) -> None:
    from factory_ops.application.errors import InvalidRequest

    if set(request.query_params) - allowed or len(request.query_params.multi_items()) != len(
        set(request.query_params)
    ):
        raise InvalidRequest


@router.get("/factories", response_model=FactoryListResponse)
def factories(
    request: Request,
    actor: Annotated[IdentityReference, Depends(identity)],
    service: Annotated[AssetQueries, Depends(queries)],
) -> dict:
    reject_unknown_query(request, frozenset())
    return {"items": service.list_factories(actor), "data_source": source(request)}


@router.get("/factories/{factory_id}/assets", response_model=AssetListResponse)
def search_assets(
    request: Request,
    factory_id: UUID,
    actor: Annotated[IdentityReference, Depends(identity)],
    service: Annotated[AssetQueries, Depends(queries)],
    q: Annotated[str, Query(max_length=100)] = "",
    category: Literal["refrigeration", "processing", "utilities", "other"] | None = None,
    status: Literal["pending", "in_use", "inactive", "retired"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> dict:
    reject_unknown_query(request, frozenset({"q", "category", "status", "limit", "offset"}))
    page = service.search_assets(actor, factory_id, AssetSearch(q, category, status, limit, offset))
    return {
        "items": page.items,
        "total": page.total,
        "limit": page.limit,
        "offset": page.offset,
        "data_source": source(request),
    }


@router.get("/factories/{factory_id}/assets/{asset_id}", response_model=AssetDetailResponse)
def get_asset_detail(
    request: Request,
    factory_id: UUID,
    asset_id: UUID,
    actor: Annotated[IdentityReference, Depends(identity)],
    service: Annotated[AssetQueries, Depends(queries)],
) -> dict:
    reject_unknown_query(request, frozenset())
    return {
        "asset": service.get_asset_detail(actor, factory_id, asset_id),
        "data_source": source(request),
    }
