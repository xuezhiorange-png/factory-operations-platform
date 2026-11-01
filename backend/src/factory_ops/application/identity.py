"""Identity proof boundaries. Client user/factory IDs never constitute authentication."""

import hashlib
import re
from dataclasses import dataclass
from typing import Literal, Protocol

from factory_ops.application.errors import Unauthenticated


@dataclass(frozen=True, repr=False)
class SessionIdentity:
    token_hash: str


@dataclass(frozen=True, repr=False)
class ExternalIdentity:
    provider: Literal["feishu", "doubao_mcp"]
    issuer: str
    tenant_id: str
    app_id: str
    subject_id: str


IdentityReference = SessionIdentity | ExternalIdentity


class IdentityProvider(Protocol):
    def authenticate(self, credential: str) -> IdentityReference: ...


class SessionIdentityProvider:
    """Parse opaque server-issued credentials; database resolution still validates the session."""

    def authenticate(self, credential: str) -> SessionIdentity:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", credential):
            raise Unauthenticated
        return SessionIdentity(hashlib.sha256(credential.encode("ascii")).hexdigest())
