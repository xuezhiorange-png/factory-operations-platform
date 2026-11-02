"""File-secret loader for the isolated stack; never prints configuration or credentials."""

import json
import os
import sys
from pathlib import Path

from sqlalchemy.engine import URL


def configure():
    role = os.environ.get("MCP_DB_ROLE")
    if role == "probe":
        return
    if role not in {"runtime", "migrator", "operator"}:
        raise ValueError
    password = Path(f"/run/secrets/{role}_password").read_text().strip()
    if not password:
        raise ValueError
    os.environ["DATABASE_URL"] = URL.create(
        "postgresql+psycopg",
        username="factory_ops_" + role,
        password=password,
        host="db",
        database="factory_ops_mcp_synthetic",
        query={"connect_timeout": "3"},
    ).render_as_string(hide_password=False)
    # This stack deliberately has no Feishu application or web session channel.
    for key in (
        "FACTORY_OPS_PUBLIC_ORIGIN",
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_TENANT_KEY",
    ):
        os.environ.pop(key, None)
    if role in {"runtime", "operator"}:
        settings = json.loads(Path("/run/secrets/identity_settings").read_text())
        os.environ.update(
            {
                "FACTORY_OPS_MCP_ENABLED": "1",
                "FACTORY_OPS_MCP_PUBLIC_ORIGIN": settings["public_origin"],
                "AILY_TENANT_ID": settings["tenant_id"],
                "AILY_ALLOWED_AGENT_IDS": settings["agent_ids"],
                "AILY_IDENTITY_JWT_SECRET": Path("/run/secrets/aily_signing_key")
                .read_text()
                .strip(),
            }
        )


if __name__ == "__main__":
    try:
        configure()
        os.execvp(sys.argv[1], sys.argv[1:])
    except (ValueError, KeyError, OSError, IndexError):
        sys.exit(
            "Isolated stack configuration rejected; inspect private configuration locally."
        )
