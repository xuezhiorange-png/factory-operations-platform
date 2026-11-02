"""Aily's documented per-request identity JWT, independent of Feishu OAuth."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import jwt

from factory_ops.application.errors import IdentityUnavailable, Unauthenticated
from factory_ops.application.identity import ExternalIdentity

# Adapter namespace, NOT an invented required JWT issuer claim.
AILY_IDENTITY_SOURCE = "https://aily.feishu.cn"


@dataclass(frozen=True)
class DoubaoMcpConfig:
    tenant_id: str
    agent_ids: frozenset[str]
    signing_secret: str = field(repr=False)

    def __post_init__(self):
        if (
            not re.fullmatch(r"[1-9][0-9]{0,39}", self.tenant_id)
            or not self.agent_ids
            or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", a) for a in self.agent_ids)
            or len(self.signing_secret.encode()) < 32
        ):
            raise ValueError("Invalid controlled Aily tenant, agent scope or signing key")


class DoubaoMcpIdentityProvider:
    def __init__(self, config: DoubaoMcpConfig | None = None):
        self.config = config

    def authenticate(self, credential: str) -> ExternalIdentity:
        if self.config is None:
            raise IdentityUnavailable
        if not isinstance(credential, str) or not 1 <= len(credential) <= 8192:
            raise Unauthenticated
        try:
            claims = jwt.decode(
                credential,
                self.config.signing_secret,  # Official key is a raw string, never base64 decoded.
                algorithms=["HS256"],
                options={
                    "require": ["exp", "tenant_id", "user_id", "agent_id"],
                    "verify_aud": False,  # Official protocol defines neither aud nor iss.
                },
            )
            # Official user_id/tenant_id are JSON numbers. Python preserves the full integer;
            # never round through JS/float, or accept bool/string/coerced identity values.
            now = datetime.now(UTC).timestamp()
            if (
                type(claims["user_id"]) is not int
                or not 0 < claims["user_id"] < 10**40
                or type(claims["tenant_id"]) is not int
                or str(claims["tenant_id"]) != self.config.tenant_id
                or not isinstance(claims["agent_id"], str)
                or claims["agent_id"] not in self.config.agent_ids
                or type(claims["exp"]) is not int
                or not now < claims["exp"] <= now + 86400
            ):
                raise Unauthenticated
        except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
            raise Unauthenticated from None
        # agent_id is an independently authorized identity namespace, not a factory grant.
        return ExternalIdentity(
            "doubao_mcp",
            AILY_IDENTITY_SOURCE,
            self.config.tenant_id,
            claims["agent_id"],
            str(claims["user_id"]),
        )
