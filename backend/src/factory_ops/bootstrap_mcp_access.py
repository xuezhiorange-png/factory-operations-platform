"""Privileged offline administration. No anonymous route or shared user token."""

import argparse
import json
import os
import stat
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from factory_ops.application.access import AccessChange
from factory_ops.application.errors import ApplicationError
from factory_ops.application.mcp_access import McpAccessService
from factory_ops.infrastructure.database.mcp_access import SqlMcpAccessUnitOfWork
from factory_ops.infrastructure.identity.doubao import DoubaoMcpIdentityProvider
from factory_ops.mcp_config import identity_config


def private_credential(path):
    """No tokens in argv, symlink reads or broadly readable files."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor) as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_uid != os.geteuid()
            or info.st_size > 8192
        ):
            raise ValueError("Credential file must be an owned, private, bounded regular file")
        return stream.read(8193).strip()


def main():
    parser = argparse.ArgumentParser(
        description="Controlled MCP identity and access administration"
    )
    parser.add_argument("operation", choices=["bind", "bootstrap", "grant", "unbind"])
    parser.add_argument(
        "--identity-file", required=True, help="Private file containing a verified JWT"
    )
    parser.add_argument("--actor-identity-file", help="Required group lead JWT for later bindings")
    parser.add_argument("--target", type=UUID)
    parser.add_argument("--expected-version", type=int)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--role", choices=["pending", "group_lead", "engineer", "factory_equipment_admin"]
    )
    parser.add_argument("--factory", type=UUID, action="append", default=[])
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--confirm-offline-change", required=True, action="store_true")
    args = parser.parse_args()
    if os.environ.get("FACTORY_OPS_ALLOW_OFFLINE_BOOTSTRAP") != "1":
        parser.exit(2, "Explicit operator enablement is required.\n")
    engine = None
    try:
        url = os.environ.get("DATABASE_URL", "")
        if make_url(url).drivername != "postgresql+psycopg":
            raise ValueError
        provider = DoubaoMcpIdentityProvider(identity_config())
        identity = provider.authenticate(private_credential(args.identity_file))
        actor = (
            provider.authenticate(private_credential(args.actor_identity_file))
            if args.actor_identity_file
            else None
        )
        if args.operation in {"grant", "unbind"} and not args.target:
            raise ValueError
        if (args.operation != "bind" or args.target) and not args.expected_version:
            raise ValueError
        if args.operation == "grant" and args.role is None:
            raise ValueError
        engine = create_engine(url, echo=False)
        service = McpAccessService(lambda: SqlMcpAccessUnitOfWork(engine))
        if args.operation == "bind":
            result = service.bind(
                identity,
                args.reason,
                actor_identity=actor,
                target=args.target,
                expected=args.expected_version,
            )
        elif args.operation == "bootstrap":
            result = service.bootstrap(identity, args.expected_version, args.reason)
        elif args.operation == "grant":
            result = service.grant(
                identity,
                args.target,
                AccessChange(
                    args.expected_version,
                    None if args.role == "pending" else args.role,
                    not args.disable,
                    tuple(args.factory),
                    args.reason,
                ),
            )["user"]
        else:
            result = service.unbind(identity, args.target, args.expected_version, args.reason)
    except (ApplicationError, SQLAlchemyError, ValueError, OSError):
        parser.exit(1, "Offline change rejected; inspect protected audit/account state.\n")
    finally:
        if engine is not None:
            engine.dispose()
    print(json.dumps({"user_id": str(result["id"]), "version": result["version"]}))


if __name__ == "__main__":
    main()
