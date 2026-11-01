# M1-02 变更文件清单

A：`codex/m1-02a-feishu-session`（基于 PR #5）；B：`codex/m1-02b-access-lifecycle`（基于 A）。
本文件列出各自依赖基线以上的变更，不重复计算前置 M1-01。
最终 HEAD 和 CI 见各 Draft PR 描述；不修改 PR #5 或 M0.6 冻结版本。

## 数据库迁移

- A 新增 `backend/migrations/versions/0002_feishu_sessions.py`，依赖 `0001_m1_foundation`。
- B 新增 `backend/migrations/versions/0003_access_lifecycle.py`，依赖 0002。
- 未修改 0001；迁移不插入人员/设备。0003 有审计详情时拒绝破坏性降级，详见 ADR-0007。

## A（57 个文件）

```text
.env.example
.github/workflows/ci.yml
.gitignore
README.md
backend/migrations/versions/0002_feishu_sessions.py
backend/pyproject.toml
backend/src/factory_ops/api/app.py
backend/src/factory_ops/api/assets.py
backend/src/factory_ops/api/auth.py
backend/src/factory_ops/application/auth.py
backend/src/factory_ops/application/errors.py
backend/src/factory_ops/application/identity.py
backend/src/factory_ops/bootstrap.py
backend/src/factory_ops/domain/errors.py
backend/src/factory_ops/infrastructure/database/auth.py
backend/src/factory_ops/infrastructure/database/models.py
backend/src/factory_ops/infrastructure/database/uow.py
backend/src/factory_ops/infrastructure/identity/feishu.py
backend/src/factory_ops/infrastructure/identity/providers.py
backend/tests/feishu_support.py
backend/tests/test_feishu_auth.py
backend/tests/test_health.py
docs/api/M1_02_IDENTITY_ACCESS.md
docs/architecture/ADR-0006-feishu-platform-sessions.md
docs/architecture/IDENTITY_ADAPTERS_M1.md
docs/delivery/M1_02A_VERIFICATION.md
docs/delivery/screenshots/m1-02/README.md
docs/delivery/screenshots/m1-02/h5-authenticated-detail.png
docs/delivery/screenshots/m1-02/h5-pending-account.png
docs/delivery/screenshots/m1-02/pc-authenticated-assets.png
docs/delivery/screenshots/m1-02/pc-login.png
frontend/identity-tests/auth.spec.ts
frontend/identity-tests/fixture.ts
frontend/package.json
frontend/playwright.identity.config.ts
frontend/src/app/features.ts
frontend/src/app/router.ts
frontend/src/modules/assets/AssetLiveDetail.vue
frontend/src/modules/assets/AssetReadState.vue
frontend/src/modules/assets/AssetsLivePage.vue
frontend/src/modules/dashboard/WorkbenchPage.vue
frontend/src/modules/identity/IdentityNotice.vue
frontend/src/modules/identity/IdentityPanel.vue
frontend/src/modules/identity/LoginPage.vue
frontend/src/modules/identity/account.ts
frontend/src/modules/mobile/MobileHomePage.vue
frontend/src/modules/mobile/MobileMePage.vue
frontend/src/modules/settings/SettingsPage.vue
frontend/src/shared/components/ShellNotice.vue
frontend/src/shared/components/SidebarNavigation.vue
frontend/src/shared/layouts/DesktopLayout.vue
frontend/src/shared/layouts/MobileLayout.vue
frontend/src/style.css
frontend/tsconfig.e2e.json
frontend/vite.config.ts
scripts/check_docs.py
scripts/serve_identity_test_api.py
```

## B（41 个文件）

```text
README.md
backend/migrations/versions/0003_access_lifecycle.py
backend/src/factory_ops/api/access.py
backend/src/factory_ops/api/app.py
backend/src/factory_ops/application/access.py
backend/src/factory_ops/bootstrap.py
backend/src/factory_ops/bootstrap_access.py
backend/src/factory_ops/infrastructure/database/access.py
backend/src/factory_ops/infrastructure/database/auth.py
backend/src/factory_ops/infrastructure/database/models.py
backend/tests/db_support.py
backend/tests/feishu_support.py
backend/tests/test_access_lifecycle.py
backend/tests/test_asset_api.py
backend/tests/test_feishu_auth.py
backend/tests/test_health.py
docs/TECH_DEBT.md
docs/api/M1_02_IDENTITY_ACCESS.md
docs/architecture/ADR-0007-access-lifecycle.md
docs/architecture/data-model.md
docs/architecture/permissions.md
docs/delivery/M1_02B_VERIFICATION.md
docs/delivery/M1_02_CHANGED_FILES.md
docs/delivery/M1_02_NEXT_TASKS.md
docs/delivery/screenshots/m1-02/README.md
docs/delivery/screenshots/m1-02/h5-pending-account.png
docs/delivery/screenshots/m1-02/h5-personnel.png
docs/delivery/screenshots/m1-02/pc-access-drawer.png
docs/delivery/screenshots/m1-02/pc-access-history.png
docs/delivery/screenshots/m1-02/pc-authenticated-assets.png
docs/delivery/screenshots/m1-02/pc-login.png
docs/delivery/screenshots/m1-02/pc-personnel.png
frontend/identity-tests/auth.spec.ts
frontend/identity-tests/fixture.ts
frontend/identity-tests/people.spec.ts
frontend/src/modules/settings/SettingsPage.vue
frontend/src/modules/settings/people/PeopleManagement.vue
frontend/src/modules/settings/people/api.ts
frontend/src/style.css
scripts/check_docs.py
scripts/serve_identity_test_api.py
```
