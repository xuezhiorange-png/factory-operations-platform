"""Composition-only configuration shared by web and controlled offline commands."""

import os
from urllib.parse import urlsplit

from factory_ops.infrastructure.identity.doubao import DoubaoMcpConfig


def identity_config() -> DoubaoMcpConfig:
    return DoubaoMcpConfig(
        os.environ.get("AILY_TENANT_ID", ""),
        frozenset(
            a.strip() for a in os.environ.get("AILY_ALLOWED_AGENT_IDS", "").split(",") if a.strip()
        ),
        os.environ.get("AILY_IDENTITY_JWT_SECRET", ""),
    )


def mcp_origin() -> str:
    origin = os.environ.get("FACTORY_OPS_MCP_PUBLIC_ORIGIN", "")
    parts = urlsplit(origin)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.path
        or parts.query
        or parts.fragment
        or origin != f"https://{parts.netloc}"
    ):
        raise ValueError("FACTORY_OPS_MCP_PUBLIC_ORIGIN must be an exact HTTPS origin")
    return origin
