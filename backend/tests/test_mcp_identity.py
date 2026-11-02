"""MCP contracts delegate to the same application service; real channels fail closed."""

import json

import pytest
from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from factory_ops.application.assets import AssetQueries
from factory_ops.application.errors import (
    AccessDenied,
    IdentityUnavailable,
    InvalidRequest,
    NotFound,
    Unauthenticated,
)
from factory_ops.application.identity import ExternalIdentity
from factory_ops.application.mcp import TOOLS, ReadOnlyAssetMcp
from factory_ops.infrastructure.database.models import ExternalIdentityRow, FactoryAccessRow
from factory_ops.infrastructure.database.uow import SqlReadUnitOfWork
from factory_ops.infrastructure.identity.providers import (
    DoubaoMcpIdentityProvider,
    FeishuIdentityProvider,
)


@pytest.mark.parametrize("provider", [FeishuIdentityProvider, DoubaoMcpIdentityProvider])
def test_unconfigured_identity_channels_never_claim_success(provider):
    with pytest.raises(IdentityUnavailable):
        provider().authenticate("unsigned.synthetic.claims")


def test_only_three_read_tools_and_no_client_user_identity_in_contract():
    assert {tool["name"] for tool in TOOLS} == {
        "list_factories", "search_assets", "get_asset_detail"
    }
    assert all(
        tool["annotations"]["readOnlyHint"] and not tool["inputSchema"]["additionalProperties"]
        for tool in TOOLS
    )
    assert all("user_id" not in tool["inputSchema"]["properties"] for tool in TOOLS)


def test_mcp_same_authorization_service_and_binding_revocation(business):
    _, data, db = business

    class SyntheticVerifiedProvider:
        # Explicit test double, never wired in bootstrap or exposed over HTTP.
        def authenticate(self, credential):
            return ExternalIdentity(
                "doubao_mcp", "synthetic-test-issuer", "SYNTH-TENANT", "SYNTH-APP", "SYNTH-SUBJECT"
            )

    tool = ReadOnlyAssetMcp(
        SyntheticVerifiedProvider(), AssetQueries(lambda: SqlReadUnitOfWork(db.engine))
    )
    args = {"factory_id": str(data.factories["A"])}
    page = tool.call("search_assets", args, "test-only")
    assert page["total"] == 2
    assert json.loads(json.dumps(page)) == page
    assert all(item["factory_id"] == args["factory_id"] for item in page["items"])
    assert isinstance(page["items"][0]["created_at"], str)
    assert (
        tool.call("get_asset_detail", {**args, "asset_id": str(data.assets["A"])}, "test-only")[
            "name"
        ]
        == "SYNTH-设备-A"
    )
    with pytest.raises(AccessDenied):
        tool.call("search_assets", {"factory_id": str(data.factories["B"])}, "test-only")
    with pytest.raises(NotFound):
        tool.call("get_asset_detail", {**args, "asset_id": str(data.assets["B"])}, "test-only")
    with pytest.raises(InvalidRequest):
        tool.call("search_assets", {**args, "user_id": str(data.users["group"])}, "test-only")
    with pytest.raises(InvalidRequest):
        tool.call("search_assets", {**args, "limit": True}, "test-only")
    with pytest.raises(InvalidRequest):
        tool.call("write_asset", args, "test-only")
    with Session(db.engine) as session:
        session.execute(
            delete(FactoryAccessRow).where(FactoryAccessRow.user_id == data.users["engineer"])
        )
        session.commit()
    with pytest.raises(AccessDenied):
        tool.call("search_assets", args, "test-only")
    with Session(db.engine) as session:
        session.execute(update(ExternalIdentityRow).values(active=False))
        session.commit()
    with pytest.raises(Unauthenticated):
        tool.call("search_assets", args, "test-only")
