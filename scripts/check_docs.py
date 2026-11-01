"""Read-only M0 document baseline check. No network or secrets required."""

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
]
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
    f"M0 documentation baseline OK ({len(REQUIRED)} required files, "
    f"{checked_links} local links checked; external URLs/anchors not verified)"
)
