"""Deliberately unavailable until official identity verification is implemented and authorized."""

from factory_ops.application.errors import IdentityUnavailable
from factory_ops.application.identity import ExternalIdentity


class FeishuIdentityProvider:
    def authenticate(self, credential: str) -> ExternalIdentity:
        # Future: official server-side exchange, tenant/app binding, replay/expiry checks.
        raise IdentityUnavailable


class DoubaoMcpIdentityProvider:
    def authenticate(self, credential: str) -> ExternalIdentity:
        # Future: verify x-aily-jwt signature, trusted issuer/JWKS, audience, expiry and source.
        # Parsing claims alone or trusting x-aily-user-id would NOT authenticate a caller.
        raise IdentityUnavailable
