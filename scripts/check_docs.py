"""Read-only platform document baseline check. No network or secrets required."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "AGENTS.md",
    "backend/pyproject.toml",
    "backend/src/factory_ops/api/app.py",
    "backend/src/factory_ops/application/__init__.py",
    "backend/src/factory_ops/infrastructure/__init__.py",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/.nvmrc",
    "frontend/src/App.vue",
    ".github/workflows/ci.yml",
    "docs/product/PRD_V1.3.md",
    "docs/architecture/overview.md",
    "docs/architecture/data-model.md",
    "docs/architecture/permissions.md",
    "docs/architecture/integrations.md",
    "docs/architecture/ADR-0001-modular-monolith.md",
    "docs/architecture/ADR-0002-auth-and-factory-scope.md",
    "docs/architecture/M0_REVIEW.md",
    "docs/api/README.md",
    "docs/data/ASSET_BASELINE.md",
    "docs/acceptance/M1_ASSETS.md",
    "docs/operations/M0_RUNBOOK.md",
    "docs/delivery/M0_CHECKLIST.md",
    "docs/delivery/PILOT_CHECKLIST.md",
    "docs/delivery/CODEX_TASK_M0.md",
    "docs/delivery/LOCAL_VERIFICATION.md",
    "docs/architecture/ADR-0003-platform-shell.md",
    "docs/architecture/FRONTEND_SHELL.md",
    "docs/delivery/M0_5_VERIFICATION.md",
    "docs/delivery/M0_5_RESILIENCE.md",
    "frontend/src/app/RouteLoadFailure.vue",
    "frontend/src/shared/components/SidebarNavigation.vue",
    "docs/delivery/screenshots/m0-5/README.md",
    "frontend/src/app/router.ts",
    "frontend/src/shared/layouts/DesktopLayout.vue",
    "frontend/src/shared/layouts/MobileLayout.vue",
    "frontend/src/tokens.css",
    "frontend/playwright.config.ts",
    "frontend/tests/shell.spec.ts",
    "frontend/tests/screenshots.spec.ts",
    "backend/alembic.ini",
    "backend/migrations/versions/0001_m1_foundation_m1_01_minimum_business_foundation.py",
    "backend/src/factory_ops/application/assets.py",
    "backend/src/factory_ops/application/mcp.py",
    "backend/src/factory_ops/infrastructure/identity/providers.py",
    "backend/tests/test_database.py",
    "backend/tests/test_asset_api.py",
    "backend/tests/test_mcp_identity.py",
    "backend/src/factory_ops/api/mcp.py",
    "backend/src/factory_ops/infrastructure/identity/doubao.py",
    "backend/src/factory_ops/application/mcp_access.py",
    "backend/src/factory_ops/infrastructure/database/mcp_access.py",
    "backend/src/factory_ops/bootstrap_mcp_access.py",
    "backend/src/factory_ops/mcp_config.py",
    "backend/tests/test_remote_mcp.py",
    "backend/tests/test_doubao_jwt.py",
    "backend/tests/test_mcp_access.py",
    "docs/architecture/ADR-0008-remote-mcp-readonly.md",
    "docs/api/M1_03A_REMOTE_MCP.md",
    "docs/operations/M1_03A_MCP_RUNBOOK.md",
    "docs/delivery/M1_03A_VERIFICATION.md",
    "deploy/mcp-test/compose.yaml",
    "deploy/mcp-test/compose.public-review.example.yaml",
    "deploy/mcp-test/Dockerfile",
    "deploy/mcp-test/Dockerfile.dockerignore",
    "deploy/mcp-test/nginx.conf.template",
    "deploy/mcp-test/init-db.sh",
    "deploy/mcp-test/entrypoint.py",
    "deploy/mcp-test/database.py",
    "deploy/mcp-test/inspect_identity.py",
    "scripts/mcp_gateway_test.py",
    "docs/architecture/ADR-0009-isolated-mcp-gateway.md",
    "docs/operations/M1_03B_MCP_INTEGRATION.md",
    "docs/delivery/M1_03B_VERIFICATION.md",
    "frontend/src/modules/assets/AssetsLivePage.vue",
    "frontend/src/modules/assets/AssetLiveDetail.vue",
    "frontend/src/modules/assets/api.ts",
    "frontend/playwright.business.config.ts",
    "frontend/business-tests/assets.spec.ts",
    "scripts/serve_business_test_api.py",
    "docs/architecture/ADR-0005-minimal-business-foundation.md",
    "docs/architecture/IDENTITY_ADAPTERS_M1.md",
    "docs/api/M1_01_ASSET_READ.md",
    "docs/delivery/M1_01_VERIFICATION.md",
    "docs/delivery/M1_NEXT_TASKS.md",
    "backend/migrations/versions/0002_feishu_sessions.py",
    "backend/src/factory_ops/application/auth.py",
    "backend/src/factory_ops/infrastructure/identity/feishu.py",
    "frontend/playwright.identity.config.ts",
    "frontend/identity-tests/auth.spec.ts",
    "docs/architecture/ADR-0006-feishu-platform-sessions.md",
    "docs/api/M1_02_IDENTITY_ACCESS.md",
    "docs/delivery/M1_02A_VERIFICATION.md",
    "docs/delivery/screenshots/m1-02/README.md",
    "backend/migrations/versions/0003_access_lifecycle.py",
    "backend/src/factory_ops/application/access.py",
    "backend/src/factory_ops/bootstrap_access.py",
    "backend/tests/test_access_lifecycle.py",
    "frontend/src/modules/settings/people/PeopleManagement.vue",
    "frontend/identity-tests/people.spec.ts",
    "docs/architecture/ADR-0007-access-lifecycle.md",
    "docs/delivery/M1_02B_VERIFICATION.md",
    "docs/delivery/M1_02_NEXT_TASKS.md",
    "docs/delivery/M1_02_CHANGED_FILES.md",
]
REQUIRED.extend(
    f"docs/delivery/screenshots/m0-5/{name}.png"
    for name in (
        "pc-workbench", "pc-assets", "pc-asset-detail", "pc-work-order", "pc-roles",
        "pc-integrations", "mobile-home", "mobile-tasks", "mobile-scan", "mobile-messages",
        "mobile-me", "mobile-asset-detail", "narrow-navigation", "route-load-failure",
    )
)
missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
if missing:
    raise SystemExit("Missing required files:\n" + "\n".join(missing))

permissions = (ROOT / "docs/architecture/permissions.md").read_text(encoding="utf-8")
for role in ("集团负责人", "工程师", "加工厂设备管理员"):
    if role not in permissions:
        raise SystemExit(f"Missing management role in permissions: {role}")

broken_links = []
checked_links = 0
documents = [ROOT / "README.md", ROOT / "AGENTS.md", *sorted((ROOT / "docs").rglob("*.md"))]
for document in documents:
    for destination in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", document.read_text(encoding="utf-8")):
        url = urlsplit(destination)
        if url.scheme or url.netloc or not url.path:
            continue
        checked_links += 1
        path = (document.parent / unquote(url.path)).resolve()
        if not path.is_relative_to(ROOT) or not path.exists():
            broken_links.append(f"{document.relative_to(ROOT)} -> {destination}")
if broken_links:
    raise SystemExit("Broken local document links:\n" + "\n".join(broken_links))

print(
    f"Platform documentation baseline OK ({len(REQUIRED)} required files, "
    f"{checked_links} local links checked; external URLs/anchors not verified)"
)
