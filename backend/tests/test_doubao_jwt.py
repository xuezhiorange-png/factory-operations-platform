"""Official Aily claim shape; synthetic keys only, never real tenant credentials."""

import secrets
import time

import jwt
import pytest

from factory_ops.application.errors import Unauthenticated
from factory_ops.infrastructure.identity.doubao import DoubaoMcpConfig, DoubaoMcpIdentityProvider

TENANT = 7280000000000000001
SUBJECT = 7620000000000000001
AGENT = "agent_synthetic"


@pytest.fixture
def jwt_identity():
    key = secrets.token_urlsafe(48)
    provider = DoubaoMcpIdentityProvider(DoubaoMcpConfig(str(TENANT), frozenset({AGENT}), key))

    def token(**changes):
        return jwt.encode(
            {
                "tenant_id": TENANT,
                "user_id": SUBJECT,
                "agent_id": AGENT,
                "exp": int(time.time()) + 3600,
                **changes,
            },
            key,
            algorithm="HS256",
        )

    return provider, token, key


def test_official_claims_without_issuer_audience_and_precision(jwt_identity):
    provider, token, key = jwt_identity
    identity = provider.authenticate(
        token(email="ignored@example.invalid", department_ids=["group_lead"], role="group_lead")
    )
    assert identity.provider == "doubao_mcp"
    assert identity.subject_id == str(SUBJECT)
    assert identity.tenant_id == str(TENANT)
    assert identity.app_id == AGENT
    assert identity.display_name is None
    assert key not in repr(provider.config)


@pytest.mark.parametrize(
    "changes",
    [
        {"tenant_id": TENANT + 1},
        {"tenant_id": str(TENANT)},
        {"tenant_id": True},
        {"user_id": str(SUBJECT)},
        {"user_id": float(SUBJECT)},
        {"user_id": True},
        {"user_id": 0},
        {"user_id": -1},
        {"user_id": None},
        {"agent_id": "wrong_agent"},
        {"agent_id": None},
        {"agent_id": [AGENT]},
        {"exp": 1},
        {"exp": None},
        {"exp": "9999999999"},
        {"exp": True},
        {"exp": 9999999999},
    ],
)
def test_untrusted_or_expired_claims_rejected(jwt_identity, changes):
    provider, token, _ = jwt_identity
    with pytest.raises(Unauthenticated):
        provider.authenticate(token(**changes))


@pytest.mark.parametrize("field", ["exp", "tenant_id", "user_id", "agent_id"])
def test_required_official_claim(jwt_identity, field):
    provider, token, key = jwt_identity
    payload = jwt.decode(token(), key, algorithms=["HS256"])
    del payload[field]
    with pytest.raises(Unauthenticated):
        provider.authenticate(jwt.encode(payload, key, algorithm="HS256"))


def test_algorithm_confusion_bad_signature_and_malformed(jwt_identity):
    provider, token, key = jwt_identity
    payload = {
        "tenant_id": TENANT,
        "user_id": SUBJECT,
        "agent_id": AGENT,
        "exp": int(time.time()) + 100,
    }
    for credential in [
        "",
        "unsigned",
        "Bearer " + token(),
        "x" * 8193,
        jwt.encode(payload, key + "wrong", algorithm="HS256"),
        jwt.encode(payload, key, algorithm="HS384"),
        jwt.encode(payload, "", algorithm="none"),
    ]:
        with pytest.raises(Unauthenticated):
            provider.authenticate(credential)
