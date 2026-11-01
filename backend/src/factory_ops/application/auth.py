"""OAuth/session orchestration. No HTTP, SDK or database dependencies."""

import base64
import hashlib
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode, urlsplit
from uuid import UUID

from factory_ops.application.errors import (
    ApplicationError,
    CsrfRejected,
    IdentityUnavailable,
    InvalidLogin,
    InvalidRequest,
)
from factory_ops.application.identity import ExternalIdentity
from factory_ops.application.ports import ReadUnitOfWork

AUTHORIZE_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def opaque() -> str:
    return secrets.token_urlsafe(32)


def valid_opaque(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[A-Za-z0-9_-]{43,128}", value))


def safe_return(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 600
        or not value.startswith("/")
        or value.startswith("//")
        or any(c in value for c in "\\\r\n#%")
        or not re.fullmatch(
            r"/(?:m/)?(?:workbench|home|tasks|scan|messages|me|assets|settings|inspections|issues|work-orders|maintenance|inventory|analytics)(?:[/?][A-Za-z0-9_?=&/.-]*)?",
            value,
        )
    ):
        raise InvalidRequest
    return value


@dataclass(frozen=True)
class AuthSettings:
    origin: str
    app_id: str = ""
    session_seconds: int = 28800

    def __post_init__(self):
        url = urlsplit(self.origin)
        if (
            url.scheme != "https"
            or not url.netloc
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "Auth origin must be an exact HTTPS origin without path or credentials"
            )
        if not 300 <= self.session_seconds <= 28800:
            raise ValueError("Platform session lifetime must be between 300 and 28800 seconds")

    @property
    def callback(self) -> str:
        return self.origin + "/api/v1/auth/feishu/callback"

    def check_origin(self, value: str | None):
        if value != self.origin:
            raise CsrfRejected


@dataclass(frozen=True)
class AccountView:
    id: UUID
    display_name: str
    role: str | None
    status: str
    factories: tuple


class AuthUnitOfWork(ReadUnitOfWork, Protocol):
    def add_flow(
        self, state: str, browser: str, destination: str, channel: str, expires: datetime
    ) -> None: ...
    def consume_flow(self, state: str, browser: str, code: str, now: datetime) -> str: ...
    def bind_and_issue(
        self,
        identity: ExternalIdentity,
        token_hash: str,
        csrf_hash: str,
        lifetime: int,
        previous: str | None,
    ) -> None: ...
    def account(self, token: str) -> AccountView: ...
    def require_csrf(self, token: str, csrf: str) -> object: ...
    def revoke_session(self, token: str) -> None: ...


AuthUnitOfWorkFactory = Callable[[], AuthUnitOfWork]


class CodeProvider(Protocol):
    def authenticate(self, credential: str, *, code_verifier: str) -> ExternalIdentity: ...


@dataclass(frozen=True, repr=False)
class LoginStart:
    url: str
    browser_secret: str


@dataclass(frozen=True, repr=False)
class LoginComplete:
    return_to: str
    token: str
    csrf: str


class LoginFailure(ApplicationError):
    def __init__(self, cause: ApplicationError, destination: str):
        self.code, self.message, self.status = cause.code, cause.message, cause.status
        self.destination = safe_return(destination)


class AuthService:
    def __init__(
        self,
        uow: AuthUnitOfWorkFactory,
        settings: AuthSettings,
        provider: CodeProvider | None = None,
    ):
        self.uow, self.settings, self.provider = uow, settings, provider

    def start(self, return_to: str, channel: str) -> LoginStart:
        if self.provider is None or not self.settings.app_id:
            raise IdentityUnavailable
        safe_return(return_to)
        if channel not in {"pc", "h5"}:
            raise InvalidRequest
        state, browser = opaque(), opaque()
        with self.uow() as uow:
            uow.add_flow(
                digest(state),
                digest(browser),
                return_to,
                channel,
                datetime.now(UTC) + timedelta(minutes=5),
            )
            uow.commit()
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(browser.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        url = (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "client_id": self.settings.app_id,
                    "response_type": "code",
                    "redirect_uri": self.settings.callback,
                    "state": state,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                }
            )
        )
        return LoginStart(url, browser)

    def complete(
        self, state: str, code: str, browser: str | None, old_token: str | None = None
    ) -> LoginComplete:
        if self.provider is None:
            raise IdentityUnavailable
        if (
            not valid_opaque(state)
            or not valid_opaque(browser)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,1024}", code)
        ):
            raise InvalidLogin
        # Reserve state/code before network I/O; failed exchanges also consume the challenge.
        with self.uow() as uow:
            destination = uow.consume_flow(
                digest(state), digest(browser), digest(code), datetime.now(UTC)
            )
            uow.commit()
        token, csrf = opaque(), opaque()
        try:
            external = self.provider.authenticate(code, code_verifier=browser)
            with self.uow() as uow:
                uow.bind_and_issue(
                    external,
                    digest(token),
                    digest(csrf),
                    self.settings.session_seconds,
                    digest(old_token) if old_token else None,
                )
                uow.commit()
        except ApplicationError as cause:
            raise LoginFailure(cause, destination) from None
        return LoginComplete(destination, token, csrf)

    def me(self, token: str) -> AccountView:
        with self.uow() as uow:
            return uow.account(token)

    def logout(self, token: str, csrf: str):
        with self.uow() as uow:
            uow.require_csrf(token, csrf)
            uow.revoke_session(token)
            uow.commit()
