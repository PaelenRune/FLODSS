# TASK-005 — Runtime, cockpit integration and deployment audit

Date: 2026-10-26. Scope: backend runtime/imports, guest login, isometric cockpit's connection to real solver state, Docker/Render build inputs. Changes were made in the shared checkout, without committing.

## Fixed findings

| Finding | Location (current lines) | Fix / evidence |
| --- | --- | --- |
| Root health check imported a nonexistent package and nonexistent function, returning HTTP 500. | `backend/app/main.py:93-97` | Calls the actual `app.api.routes.health.get_health`. New test reproduced the import crash before the fix. |
| Simultaneous first demo logins could both observe no guest and collide on the unique email insertion; one returned HTTP 500. | `backend/app/services/auth_service.py:352-370` | Conflict-safe guest insertion followed by reading the persisted identity. A deterministic two-request barrier test changed from `[500, 200]` to `[200, 200]`, with both sessions referencing the same stored user. This is a proven 500 path, not proof of the cause of the prior externally observed 500. |
| Concurrent guest provisioning could duplicate the starter project. | `backend/app/services/auth_service.py:380-400` | Atomic conditional project insertion. Concurrent regression also asserts exactly one starter project. |
| Cockpit accepted no problem/layout/evaluation props and always displayed fixture data. | `frontend/src/pages/Dashboard.tsx:339`; `frontend/src/components/cockpit/CockpitOverview.tsx:13-30` | Dashboard passes the shared state already updated by optimization callbacks. Live data context feeds every cockpit analytic component. |
| Illustrative geometry, directional arrows, areas, matrix, savings and scenario scores could not reflect solver output. | `frontend/src/components/cockpit/CockpitDataContext.ts:19-44`; `frontend/src/components/cockpit/LiveFactoryCanvas.tsx:5-50`; `KpiMetricsCard.tsx:3-19`; `LayoutVersionsTable.tsx:4-15` in the same directory | Live geometry uses actual placements and one uniform display scale. Matrix sums actual directed flow entries. Arrows show the 30 highest-volume placed-to-placed directed flows. Areas are computed from placements; missing placements remain unallocated. Live KPIs use matching backend evaluations, not invented percentage improvements. Live export downloads actual layout JSON. Reference fixtures remain explicitly labeled when no problem exists. |
| Initial example loading could select a layout from another problem. | `frontend/src/pages/Dashboard.tsx:141` | Removed unrelated-layout fallback. Cockpit additionally rejects layouts with a different problem ID and evaluations with a conflicting layout signature. |
| Explicit login modal could remain open after successful login. | `frontend/src/pages/Dashboard.tsx:120` | Successful user initialization closes it. Logout also invalidates initial-load problem-version requests. |
| New/restored layouts could retain previous displayed metrics while evaluation was pending. | `frontend/src/pages/Dashboard.tsx:213-232,243-250,354-356` | Clear evaluation/validation when accepting a layout; restored layouts now use the shared solver-result handler and are reevaluated. |
| Docker dependency installation ignored the frontend lockfile. | `Dockerfile:10-11` | Uses `npm ci`; clean install and production build both succeeded. |
| Render did not declare its health route; Docker context could contain local secrets/databases. | `render.yaml:7`; `.dockerignore:19-24` | Added `/health` health check and exclusions for env files, secrets and local SQLite files. Migrations create a clean runtime database; example JSON/CSV data remains copied. |

## Verification

An isolated Python 3.12 virtual environment was created at `C:\Users\paele\AppData\Local\Temp\opencode\flodss-audit-venv` and installed the exact production requirements plus pytest/pytest-asyncio.

- `python -m pytest -q` in `backend`: **454 passed**, one upstream Starlette/httpx deprecation warning. Baseline before new regressions: 450 passed.
- `python -m pip check`: no broken requirements.
- `npm.cmd ci` in `frontend`: clean lockfile install succeeded.
- `npm.cmd run build`: TypeScript and Vite production build succeeded; nonblocking large-chunk warning (approximately 589 KB uncompressed JS).
- `npm.cmd run test:cockpit`: passed. Checks live geometry updates between layouts, actual department labels/areas, duplicate directed-flow aggregation, empty/mismatched layout handling, matching/stale evaluation signatures, real KPI values, and absence of fabricated live-mode savings/scenarios.
- `backend/tests/test_deployment_smoke.py:17-73`: root/API health, fresh and repeated guest session use, simultaneous first guest provisioning, built SPA/index/assets, browser deep-link fallback, and unknown-API 404 behavior.
- Docker entry point resolves to `backend/app/main.py`; compiled SPA copy matches the application's default `frontend/dist` lookup; API requests are same-origin `/api`; startup applies database migrations before serving.
- Tests wrote timing-dependent benchmark result files; only those generated changes were restored after verification.

## Remaining limitations / incomplete items

1. **Actual container/Render deployment is not verified.** `docker version` fails because Docker is not installed. Production Python requirements installed successfully on Windows; a Linux image build still needs `docker build -t flodss .` and a container smoke run, followed by an actual Render deployment check. No cloud service was provisioned by this task.
2. **Render free-plan SQLite storage is ephemeral.** `render.yaml:5,11-12` uses free hosting and a relative SQLite path without a persistent disk. Research runs/users are not durable across redeploys. Use a supported persistent disk/paid plan or an external database before promising persistence.
3. **Current deployment is a public shared demo, not private tenant access.** `render.yaml:13-14`, `backend/app/api/deps.py:35-39`, `backend/app/services/auth_service.py:339` use disabled auth enforcement and one shared guest identity. Separate demo access from confidential production use; also set proper admin credentials/secrets and secure-cookie settings for HTTPS deployment. Existing demo behavior was not redesigned.
4. **Research-run save metadata remains fabricated.** `frontend/src/components/ProjectManagerCard.tsx:101-107` hardcodes version, seed, duration and provenance hashes/signature. The cockpit no longer fabricates solver metrics, but this existing persistence path is not scientifically faithful provenance.
5. **Cross-problem run restore does not restore its problem definition.** `frontend/src/pages/Dashboard.tsx:354-356` accepts the restored layout into current workspace state, but does not fetch its corresponding saved problem. The live cockpit rejects a mismatched problem ID rather than misrepresent it. Select/load the corresponding problem before restoring such a run; automatic project/problem snapshot restoration remains work.
6. **Single-file CSV and Excel ingestion are deliberately unfinished.** `backend/app/services/problem_loader.py:146-161` raises `NotImplementedError`; JSON and CSV-directory loading are the implemented alternatives.
7. **Python package metadata is not the production dependency source.** `backend/pyproject.toml:9,11-19` references a missing backend-local README and omits runtime dependencies such as python-dotenv/httpx/cryptography. Docker is unaffected because it installs `backend/requirements-prod.txt`, which passed installation and consistency checks. Editable/package installation needs separate metadata cleanup.
8. **Build-tool dependency audit is not clean.** `frontend/package.json:20-22` / lockfile resolve Vite 5.4.21 and esbuild 0.21.5. `npm audit` reports one high and one moderate build/dev-tool vulnerability. These tools are not shipped in the final Python runtime image. Upgrade the toolchain with compatibility testing rather than `npm audit fix --force` blindly.

## Readiness conclusion

The verified application build/runtime paths and cockpit data bridge pass local checks. The reproducible health and concurrent demo-login 500s are fixed and regression-covered. Container/cloud deployment remains **conditional**, not certified: execute a Linux Docker build and Render smoke check, and resolve storage/access policy before treating this public demo configuration as durable private production.
