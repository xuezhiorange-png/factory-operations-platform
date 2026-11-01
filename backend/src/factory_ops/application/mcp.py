"""Two read-only MCP tool contracts. No MCP network listener or identity bypass."""

import json
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from factory_ops.application.assets import AssetQueries, AssetSearch
from factory_ops.application.errors import InvalidRequest
from factory_ops.application.identity import IdentityProvider

TOOLS = (
    {
        "name": "search_assets",
        "description": "Search assets in a server-authorized factory",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["factory_id"],
            "properties": {
                "factory_id": {"type": "string", "format": "uuid"},
                "q": {"type": "string", "maxLength": 100},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "offset": {"type": "integer", "minimum": 0, "maximum": 100000, "default": 0},
            },
        },
    },
    {
        "name": "get_asset_detail",
        "description": "Read one asset in a server-authorized factory",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["factory_id", "asset_id"],
            "properties": {
                "factory_id": {"type": "string", "format": "uuid"},
                "asset_id": {"type": "string", "format": "uuid"},
            },
        },
    },
)


class ReadOnlyAssetMcp:
    def __init__(self, provider: IdentityProvider, queries: AssetQueries) -> None:
        self.provider, self.queries = provider, queries

    def call(self, name: str, arguments: dict, credential: str) -> dict:
        identity = self.provider.authenticate(credential)
        if name not in {"search_assets", "get_asset_detail"}:
            raise InvalidRequest
        allowed = (
            {"factory_id", "asset_id"}
            if name == "get_asset_detail"
            else {"factory_id", "q", "limit", "offset"}
        )
        if set(arguments) - allowed:
            raise InvalidRequest
        try:
            factory_id = UUID(arguments["factory_id"])
            if name == "get_asset_detail":
                result = self.queries.get_asset_detail(
                    identity, factory_id, UUID(arguments["asset_id"]), "doubao_mcp"
                )
            else:
                result = self.queries.search_assets(
                    identity,
                    factory_id,
                    AssetSearch(
                        q=arguments.get("q", ""),
                        limit=arguments.get("limit", 20),
                        offset=arguments.get("offset", 0),
                    ),
                    "doubao_mcp",
                )
        except (KeyError, ValueError, TypeError, AttributeError):
            raise InvalidRequest from None

        def scalar(value):
            if isinstance(value, UUID):
                return str(value)
            if isinstance(value, datetime):
                return value.isoformat()
            raise TypeError("Unsupported public DTO type")

        return json.loads(json.dumps(asdict(result), default=scalar))
