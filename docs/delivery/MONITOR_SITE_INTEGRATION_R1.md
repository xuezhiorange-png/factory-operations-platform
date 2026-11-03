# FACTORY_OPS_MONITOR_SITE_INTEGRATION_R1

## Authorized Follow-Up: Navigation and Disconnected Entry

On 2026-11-03 the user requested consistent site navigation and authorized a
frontend release **including the operations entry in disconnected mode**, without
business data. This does not authorize backend deployment, personal SSO bypass,
new database/API services, Ready or Merge.

The native route factory now accepts `{ connected: false }`. That mode clears the
module's client identity state, renders `设备运维待接入`, mounts no business child,
and performs no identity, asset, personnel or link requests, even when a valid
personal cookie already exists. It is a release circuit breaker, not an
authorization substitute. Connected mode retains every original backend check.
Two additional browser tests cover list/module navigation and deep-link cases.
The synthetic-only fixture can also show 17 clearly named synthetic monitoring
rooms for factory navigation/fullscreen checks; it cannot authenticate a monitor
control-capable account. No such fixtures are part of the production bundle.

Original R1 evidence below remains a historical record. Updated exact-head CI and
the separately versioned navigation frontend release are reported on the PR.

## Authorization and Baseline

- User authorization: implement a native module in the existing monitoring site;
  commit the scoped changes and open Draft PRs where a GitHub remote exists.
- Operations base: `8cd66352ee3ae6e2489be22a8d0522084a519fd1` (remote main verified).
- Monitoring source: `/Users/charles/Documents/监控系统/vue_switch_work`.
- Monitoring base: `91b686a313e2f73e0fec9459404ac8ef2b3abc19`.
- Monitoring remote: `ssh://coldstorageamz/mnt/data/opencode-test`, not a GitHub
  repository. No SSH fetch/push or server connection is authorized this round.
- Local source backups: `/Users/charles/factory-ops-monitor-r1-backup/`.

## Scope

Native Vue routes, reusable asset/personnel components, same-origin API path
adaptation, explicit ID link contracts, isolated tests and integration evidence.
Pending business modules must be marked as pending, without synthetic records
in the delivered application. The existing three MCP tools are unchanged.

## Hard Gates

- No production change, service restart, Nginx edit, database migration on a
  server, device command, PLC access, merge, Ready transition or deployment.
- No monitoring token forwarded to operations; no role/name-derived identity.
- Monitoring has shared role accounts (`admin`, `guest`, `xinshao`), not verified
  personal identities. Unified login is BLOCKED. Existing independently verified
  operations sessions may be used; absent sessions fail closed.
- Server audit must use the merged PR #10 tool from an authorized Mac/console.
  Current ports, Nginx, capacity and isolation remain unverified until its output
  is supplied. Do not retry the unavailable SSH channel.

## Validation

### Source and Authentication Audit

| Area | Verified source / result |
| --- | --- |
| Vue Router | `frontend/src/router.js`, HTML5 history, lazy views; existing routes preserved |
| Pinia | `frontend/src/stores/auth.js` and `data.js`; no replacement store or application shell |
| PC navigation | `navigation.ts`, `ApplicationShell.vue`, home `CommandCenter.vue` rail |
| H5 navigation | `MobileNav.vue`; original overview/device/alarm/energy/account entries retained |
| Login | Node `server/routes/auth.js`, persistent hashed sessions in `services/sessions.js`, 8-hour expiry |
| Identity limitation | Only shared role usernames; `/api/session` gives username/role/expiry, not a verified person ID |
| Existing factory rule | Server `requireAuth` limits `xinshao` control to gateway `45482`; not an operations identity or grant |
| Existing reads | Some legacy read routes are public in source. This is not used to bypass operations authorization |
| Monitoring IDs | Reviewed `FAC_*`, `ROOM_D<gateway>_*`, `FAN_ROOM_*` and numeric gateway IDs in `server/monitoring/registry.js` |
| Operations IDs | PostgreSQL factory and asset UUIDs, not names or SQLite row IDs |
| Existing workflows | No real personnel inspection/work-order/maintenance API in the audited monitor source |
| Existing release | Multi-entry Vite build and documented frontend backup/hash/rollback process, including independent Xinshao model |
| Current Nginx/ports/resources | UNVERIFIED; no server connection in this task |

The cloud-managed original checkout could not be fully materialized. The isolated
monitor worktree uses **166 retained source files**, each verified against the
pinned Git blob at the monitoring base. Missing historical preview/document files
were not fabricated, changed, staged or included as deletions. Compiled `dist`
files are not source evidence and are not part of this change.

### Implemented

- `/operations` redirects to `/operations/assets` inside the original shell.
- Eight module choices; six unfinished workflows explicitly show `待开发` and no
  records. `/operations/settings` reuses the original personnel component.
- Existing asset list/detail/API validation and backend three-role/factory/audit
  logic are reused, not rewritten. No second dashboard, iframe or login form.
- Fixed same-origin namespace `/operations-api/v1/*`, rewritten to the existing
  FastAPI `/api/v1/*` contract. Only a review-only Nginx location example is added;
  it has no `listen`, `server`, certificate or existing-route replacement.
- Operations requests use personal operations cookies, never the monitor Bearer,
  browser user_id, username, factory name or a shared administrator session.
- Two read-only link endpoints reuse asset authorization on every request.
  `FACTORY_OPS_MONITOR_LINKS_JSON` defaults to `[]`; confirmed UUID/stable-ID
  associations have effective dates and reject overlapping/ambiguous mappings.
  There are **zero real production mappings** in this change. Unknown, expired,
  wrong-factory and unconfirmed links never select the first available device.
- No monitor database access from operations, schema migration, MCP change,
  device command or new control API. Only existing access-management actions in
  the reused personnel component remain available to authorized group leads.

### Local Results (2026-11-03, Asia/Shanghai)

- Operations backend: **200 passed**, no skips, real isolated loopback PostgreSQL
  **16.15**. PostgreSQL 17 remains the existing mandatory CI database.
- Monitor tests: **163 passed**, including 160 existing and 3 new association tests.
- Both Vue typechecks/builds passed; the existing Three.js >500 kB advisory is
  retained, not suppressed. Final exact-head CI is reported separately on the PR.
- Actual original monitor `App.vue` tested in browser at 1440x960, 768x1024,
  390x844 and 320x844. Measured viewport widths, not screenshot filename guesses.
- Native list/detail/return worked against the real operations API and isolated
  PostgreSQL. Engineer saw only A; tampered factory B returned no rows and a
  forbidden state. Group lead reused the original personnel list (5 synthetic
  people). Unmapped link had zero records; pending issue flow had zero fake data.
- Personal operations session was mandatory despite monitor guest login; module
  contained no iframe. Captured browser warning/error list was empty.
- Browser fixtures use a deliberately non-Secure **loopback-only synthetic**
  cookie adapter. This is not Secure-cookie/HTTPS production acceptance. Existing
  HTTPS identity CI remains unchanged. No actual Feishu/Doubao login was tested.
- Screenshots and browser measurements: `monitor-integration-r1/` alongside this
  document. No credentials, cookies or database connection strings are archived.
- The first resize-adjacent captures (`mobile-detail.png`, `width-320.png`,
  `width-768.png`) had compositor dimensions different from the requested DOM
  viewport. They are **not accepted screenshot evidence**. Use `final-*` and
  `screenshot-metadata.json` instead. Tablet capture height differs from DOM height
  (1003 vs 1024); width/overflow checks use the measured DOM, not the image height.
- A development hot-update briefly reset the module API namespace, producing
  `/assets/*` route warnings. Namespace mode is now preserved in Vite hot data;
  full-load/production routing is unchanged. This is not a hidden production pass.

### Export and Review

`node scripts/export_monitor_portal.mjs <empty-directory>` exports the existing
module sources with per-file SHA256 and source HEAD, not a second application.
The monitor imports the vendored export from its native router. The export has
37 source files; it can be refreshed from a reviewed operations commit.

The operations Draft PR covers this reusable code and the monitor bridge patch.
The actual monitoring repository has an SSH-only server remote, so no monitor
GitHub PR or SSH push is possible within this task's authorized boundaries. Its
local branch/commit and applicable patch are delivered instead; this limitation
must not be labeled a published monitor PR or deployment.

Actual monitor source commit:
`462c050cf55b743b03065bbe00c39c957682ff05` on
`codex/factory-ops-monitor-portal-r1`, based on the exact monitor base above.
It vendors the clean reusable-code commit
`dba043667970e6019dbdc7a8420969d82411d090` (37 source files, per-file hashes).
`monitor-integration-r1/monitor-bridge.patch` contains the other 15 bridge files
for review/application to that exact real source. It is not an invented monitor
app. The generated patch uses zero context lines (avoiding whitespace-only lines
inside a tracked patch artifact). Require the exact base and check with
`git apply --check --index --unidiff-zero` before any application. Then export the
pinned reusable module into the absent `frontend/vendor/factory-operations-portal`
directory. Do not apply a patch to an unverified/dirty project or server.

The final operations PR HEAD may include delivery-only updates after that reusable
code commit. CI is required on the PR's exact HEAD, not inferred from the pinned
module export or local monitor commit. No monitor GitHub CI is claimed.

### Remaining Gates

```text
MONITOR_SOURCE_ACCESS=VERIFIED_LOCAL_PINNED_SOURCE
MONITOR_AUTH_REVIEW=COMPLETE_PERSONAL_SSO_BLOCKED
UNIFIED_PORTAL=IMPLEMENTED_LOCAL_NATIVE_VUE
OPERATIONS_MODULE_ROUTE=/operations/assets
ASSET_API_INTEGRATION=PASS_ISOLATED_REAL_API
FACTORY_ID_MAPPING=CONTRACT_TESTED_PRODUCTION_MAPS_NOT_CONFIGURED
PC_H5_TESTS=PASS_LOCAL_BROWSER_CI_REPORTED_ON_PR
EXISTING_MONITOR_REGRESSION=PASS_163_TESTS_BUILD_LOCAL_UI
SERVER_AUDIT=BLOCKED_AWAITING_USER_PR10_REPORT
READY_FOR_DEPLOYMENT=NO
```

Do not deploy until personal identity/SSO, real ID-map approval, the PR #10 server
audit, exact-head CI, review and recoverable backup verification are complete and
the user explicitly authorizes deployment. The unchanged existing audit runbook
is `docs/operations/EXISTING_SERVER_READONLY_AUDIT.md`; its tool hash is
`ca57621974d28777b2d8e67d49c1dbd431a3643e86ac03cb6555a65ab29cb3db`.

There is no production change to roll back. Local review can revert the scoped
commits; no database restore, secret change or service restart is required.
