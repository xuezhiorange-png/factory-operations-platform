"""Cookie-only authentication routes. No credentials in JSON responses."""

from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from factory_ops.application.auth import AuthService, LoginFailure
from factory_ops.application.errors import (
    ApplicationError,
    CsrfRejected,
    IdentityUnavailable,
    InvalidRequest,
    Unauthenticated,
)

router = APIRouter(prefix="/auth", tags=["identity"])
SESSION = "__Host-factory_ops_session"
CSRF = "__Host-factory_ops_csrf"
FLOW = "__Host-factory_ops_oauth"


class StartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    return_to: str = Field(default="/workbench", max_length=600)
    channel: Literal["pc", "h5"] = "pc"


def auth_service(request: Request) -> AuthService:
    service = request.app.state.auth_service
    if service is None:
        raise IdentityUnavailable
    return service


Service = Annotated[AuthService, Depends(auth_service)]


def credential(request: Request) -> str:
    value = request.cookies.get(SESSION)
    if not value:
        raise Unauthenticated
    return value


def csrf(request: Request, service: AuthService) -> tuple[str, str]:
    service.settings.check_origin(request.headers.get("origin"))
    cookie, header = request.cookies.get(CSRF), request.headers.get("x-csrf-token")
    if not cookie or cookie != header:
        raise CsrfRejected
    return credential(request), cookie


def set_cookie(
    response: Response, name: str, value: str, lifetime: int, *, http_only=True, path="/"
):
    response.set_cookie(
        name, value, max_age=lifetime, secure=True, httponly=http_only, samesite="lax", path=path
    )


def clear_session(response: Response):
    for name in (SESSION, CSRF):
        response.delete_cookie(
            name, secure=True, httponly=name == SESSION, samesite="lax", path="/"
        )


@router.get("/config")
def config(request: Request) -> dict:
    service = request.app.state.auth_service
    return {
        "configured": bool(service and service.provider),
        "data_source": request.app.state.data_source,
        "h5_method": "oauth_redirect",
    }


@router.post("/feishu/start")
def start(body: StartRequest, request: Request, response: Response, service: Service) -> dict:
    service.settings.check_origin(request.headers.get("origin"))
    result = service.start(body.return_to, body.channel)
    set_cookie(response, FLOW, result.browser_secret, 300)
    return {"authorization_url": result.url}


@router.get("/feishu/callback")
def callback(request: Request, service: Service) -> Response:
    query = request.query_params
    destination = service.settings.origin + "/#/login?status=failed"
    result = None
    try:
        if set(query) != {"state", "code"} or len(query.multi_items()) != 2:
            raise InvalidRequest
        result = service.complete(
            query.get("state", ""),
            query.get("code", ""),
            request.cookies.get(FLOW),
            request.cookies.get(SESSION),
        )
        destination = service.settings.origin + "/#" + result.return_to
    except ApplicationError as error:
        if isinstance(error, LoginFailure):
            page = "/m/login" if error.destination.startswith("/m/") else "/login"
            destination = (
                service.settings.origin
                + "/#"
                + page
                + "?"
                + urlencode({"status": "failed", "return_to": error.destination})
            )
        destination += "&" + urlencode({"reason": error.code})
    response = RedirectResponse(destination, status_code=303)
    response.delete_cookie(FLOW, path="/", secure=True, httponly=True, samesite="lax")
    if result:
        set_cookie(response, SESSION, result.token, service.settings.session_seconds)
        set_cookie(response, CSRF, result.csrf, service.settings.session_seconds, http_only=False)
    return response


@router.get("/me")
def me(request: Request, service: Service):
    return service.me(credential(request))


@router.post("/logout", status_code=204)
def logout(request: Request, service: Service) -> Response:
    token, nonce = csrf(request, service)
    service.logout(token, nonce)
    response = Response(status_code=204)
    clear_session(response)
    return response
