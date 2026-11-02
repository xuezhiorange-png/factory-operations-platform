"""Operator-only, value-free JWT diagnostics; no HTTP endpoint or capture facility."""

import json
import sys
import time

import jwt
from factory_ops.application.errors import ApplicationError
from factory_ops.bootstrap_mcp_access import private_credential
from factory_ops.infrastructure.identity.doubao import DoubaoMcpIdentityProvider
from factory_ops.mcp_config import identity_config


def main():
    try:
        token = private_credential(sys.argv[1])
        config = identity_config()
        DoubaoMcpIdentityProvider(config).authenticate(token)
        claims = jwt.decode(
            token,
            config.signing_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        result = {
            "status": "PASS",
            "alg": "HS256",
            "signature_and_scope_verified": True,
            "claim_types": {
                field: type(claims[field]).__name__
                for field in ("tenant_id", "user_id", "agent_id", "exp")
            },
            "remaining_seconds": max(0, claims["exp"] - int(time.time())),
        }
    except (
        ApplicationError,
        jwt.InvalidTokenError,
        ValueError,
        KeyError,
        IndexError,
        OSError,
    ):
        print('{"status":"FAIL","reason":"credential_or_scope_rejected"}')
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
