"""Read-only native-portal links, protected by existing personal/factory authorization."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from factory_ops.api.assets import identity, queries, reject_unknown_query, source
from factory_ops.application.assets import AssetQueries
from factory_ops.application.identity import IdentityReference
from factory_ops.application.monitor_links import current_links

router = APIRouter(prefix="/portal", tags=["monitor-portal-read"])
Actor = Annotated[IdentityReference, Depends(identity)]
Service = Annotated[AssetQueries, Depends(queries)]


@router.get("/asset-link")
def asset_link(request: Request, factory_id: UUID, asset_id: UUID, actor: Actor, service: Service):
    reject_unknown_query(request, frozenset({"factory_id", "asset_id"}))
    # A map never grants access. Validate the actual asset and current grants first.
    service.get_asset_detail(actor, factory_id, asset_id)
    link = next(
        (
            item
            for item in current_links(request.app.state.monitor_links)
            if item.factory_id == factory_id and item.asset_id == asset_id
        ),
        None,
    )
    return {
        "status": "linked" if link else "unlinked",
        "link": link,
        "data_source": source(request),
    }


@router.get("/resolve")
def resolve(
    request: Request,
    actor: Actor,
    service: Service,
    monitor_factory_id: Annotated[str, Query(pattern=r"^FAC_[A-Z0-9_]{1,100}$")],
    monitor_device_id: Annotated[str, Query(pattern=r"^[A-Za-z0-9_:-]{1,200}$")],
):
    reject_unknown_query(request, frozenset({"monitor_factory_id", "monitor_device_id"}))
    # Even an absent mapping requires a real session; there is no anonymous lookup.
    service.list_factories(actor)
    link = next(
        (
            item
            for item in current_links(request.app.state.monitor_links)
            if item.monitor_factory_id == monitor_factory_id
            and item.monitor_device_id == monitor_device_id
        ),
        None,
    )
    if link:
        service.get_asset_detail(actor, link.factory_id, link.asset_id)
    return {
        "status": "linked" if link else "unlinked",
        "link": link,
        "data_source": source(request),
    }
