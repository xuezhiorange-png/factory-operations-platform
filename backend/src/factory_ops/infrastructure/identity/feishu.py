"""Feishu authorization-code adapter. Fixed official endpoints; no token/profile logging."""

import re
from dataclasses import dataclass, field
from time import monotonic

import httpx

from factory_ops.application.errors import IdentityUnavailable, InvalidLogin
from factory_ops.application.identity import ExternalIdentity

TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
USERINFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"


@dataclass(frozen=True)
class FeishuConfig:
    app_id: str
    tenant_key: str
    redirect_uri: str
    app_secret: str = field(repr=False)


class FeishuIdentityProvider:
    def __init__(
        self, config: FeishuConfig | None = None, *, transport: httpx.BaseTransport | None = None
    ):
        self.config, self.transport = config, transport

    def authenticate(
        self, credential: str, *, code_verifier: str | None = None
    ) -> ExternalIdentity:
        cfg = self.config
        if cfg is None or not all((cfg.app_id, cfg.tenant_key, cfg.redirect_uri, cfg.app_secret)):
            raise IdentityUnavailable
        if (
            not re.fullmatch(r"[A-Za-z0-9_-]{1,1024}", credential)
            or not code_verifier
            or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", code_verifier)
        ):
            raise InvalidLogin
        try:
            with httpx.Client(
                transport=self.transport, timeout=8, follow_redirects=False
            ) as client:
                result = client.post(
                    TOKEN_URL,
                    json={
                        "grant_type": "authorization_code",
                        "client_id": cfg.app_id,
                        "client_secret": cfg.app_secret,
                        "code": credential,
                        "redirect_uri": cfg.redirect_uri,
                        "code_verifier": code_verifier,
                    },
                )
                token = self._body(result)
                if (
                    type(token.get("code")) is not int
                    or token.get("code") != 0
                    or token.get("token_type") != "Bearer"
                    or not isinstance(token.get("access_token"), str)
                    or not token["access_token"]
                    or type(token.get("expires_in")) is not int
                    or token["expires_in"] <= 0
                    or token.get("client_id", cfg.app_id) != cfg.app_id
                ):
                    raise InvalidLogin
                expires_at = monotonic() + token["expires_in"]
                info = self._body(
                    client.get(
                        USERINFO_URL, headers={"Authorization": "Bearer " + token["access_token"]}
                    )
                )
                data = info.get("data")
                if (
                    monotonic() >= expires_at
                    or type(info.get("code")) is not int
                    or info.get("code") != 0
                    or not isinstance(data, dict)
                    or data.get("tenant_key") != cfg.tenant_key
                    or data.get("app_id", cfg.app_id) != cfg.app_id
                ):
                    raise InvalidLogin
                subject = data.get("open_id")
                if not isinstance(subject, str) or not 1 <= len(subject) <= 200:
                    raise InvalidLogin
                name = data.get("name")
                if name is not None and (not isinstance(name, str) or len(name) > 200):
                    raise InvalidLogin
                return ExternalIdentity(
                    "feishu", "https://open.feishu.cn", cfg.tenant_key, cfg.app_id, subject, name
                )
        except (httpx.RequestError, ValueError, TypeError):
            raise IdentityUnavailable from None

    @staticmethod
    def _body(response: httpx.Response) -> dict:
        if response.status_code >= 500 or response.status_code == 429:
            raise IdentityUnavailable
        if response.status_code != 200:
            raise InvalidLogin
        if len(response.content) > 65536:
            raise IdentityUnavailable
        value = response.json()
        if not isinstance(value, dict):
            raise InvalidLogin
        return value
