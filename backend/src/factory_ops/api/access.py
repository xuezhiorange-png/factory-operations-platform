"""Small group-lead-only API; no arbitrary role editor, registration or bootstrap route."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from factory_ops.api.assets import reject_unknown_query
from factory_ops.api.auth import Service, credential, csrf
from factory_ops.application.access import AccessChange, AccessService
from factory_ops.application.errors import StorageUnavailable

router = APIRouter(prefix="/access", tags=["personnel"])


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: StrictInt = Field(ge=1)
    reason: str = Field(min_length=2, max_length=300)


class ChangeRequest(VersionRequest):
    role: Literal["group_lead", "engineer", "factory_equipment_admin"] | None
    active: StrictBool
    factory_ids: list[UUID] = Field(max_length=100)


def access_service(request: Request) -> AccessService:
    if request.app.state.access_service is None:
        raise StorageUnavailable
    return request.app.state.access_service


Access = Annotated[AccessService, Depends(access_service)]


@router.get("/users")
def users(
    request: Request,
    service: Access,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    reject_unknown_query(request, frozenset({"limit", "offset"}))
    return service.list_people(credential(request), limit, offset)


@router.get("/users/{user_id}/changes")
def changes(
    user_id: UUID,
    request: Request,
    service: Access,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    reject_unknown_query(request, frozenset({"limit", "offset"}))
    return service.history(credential(request), user_id, limit, offset)


@router.patch("/users/{user_id}")
def change(user_id: UUID, body: ChangeRequest, request: Request, service: Access, auth: Service):
    reject_unknown_query(request, frozenset())
    token, nonce = csrf(request, auth)
    return service.change(
        token,
        nonce,
        user_id,
        AccessChange(
            body.expected_version, body.role, body.active, tuple(body.factory_ids), body.reason
        ),
    )


@router.post("/users/{user_id}/revoke-sessions")
def revoke(user_id: UUID, body: VersionRequest, request: Request, service: Access, auth: Service):
    reject_unknown_query(request, frozenset())
    token, nonce = csrf(request, auth)
    return service.lifecycle(token, nonce, user_id, body.expected_version, body.reason)


@router.post("/users/{user_id}/unbind-feishu")
def unbind(user_id: UUID, body: VersionRequest, request: Request, service: Access, auth: Service):
    reject_unknown_query(request, frozenset())
    token, nonce = csrf(request, auth)
    return service.lifecycle(token, nonce, user_id, body.expected_version, body.reason, unbind=True)
