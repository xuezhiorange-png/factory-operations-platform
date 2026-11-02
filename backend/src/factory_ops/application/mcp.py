"""Read-only tool contracts and delegation; no transport or second authorization system."""

import json
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from factory_ops.application.assets import AssetQueries, AssetSearch
from factory_ops.application.errors import InvalidRequest
from factory_ops.application.identity import IdentityProvider

TOOLS = (
    {
        "name": "list_factories",
        "description": (
            "先调用本工具获取本人有权访问的加工厂（id、编号、名称）。"
            "按用户描述匹配工厂名称；重名或不明确时先澄清，不要求用户记忆 UUID。"
            "然后将返回的 id 传给 search_assets。无权访问的工厂不会返回。"
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}},
    },
    {
        "name": "search_assets",
        "description": (
            "在 list_factories 已返回并明确匹配的工厂中，按设备编号或名称搜索基础档案。"
            "q 为空则分页列出；精确对象不明时先展示候选并澄清，"
            "用返回的 factory_id 和设备 id 调用 get_asset_detail。仅返回本人当前授权范围。"
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
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
        "description": (
            "读取 search_assets 已明确定位的设备基础档案；"
            "factory_id、asset_id 使用前序工具结果，不猜测 UUID。"
            "不返回附件、人员、监控或其他工厂数据，无写入或设备控制能力。"
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
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
        if name not in {"list_factories", "search_assets", "get_asset_detail"}:
            raise InvalidRequest
        allowed = (
            {"factory_id", "asset_id"}
            if name == "get_asset_detail"
            else {"factory_id", "q", "limit", "offset"}
            if name == "search_assets"
            else set()
        )
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise InvalidRequest
        try:
            factory_id = UUID(arguments["factory_id"]) if name != "list_factories" else None
            if name == "list_factories":
                result = {
                    "items": [
                        asdict(f) for f in self.queries.list_factories(identity, "doubao_mcp")
                    ]
                }
            elif name == "get_asset_detail":
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

        return json.loads(
            json.dumps(result if isinstance(result, dict) else asdict(result), default=scalar)
        )
