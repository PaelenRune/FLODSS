# Render deployment verification

## Security prerequisite

The existing `DEPLOYMENT_SECURITY_CHECKLIST.md` and `PRIVATE_PILOT_OPERATIONS.md`
prohibit public hosting. The presence of `render.yaml` does not override that
policy. Obtain explicit owner approval and resolve the access-control requirements
before enabling a new public deployment. No hosting or authentication settings
were changed for the cockpit release.

## Repository configuration

- `render.yaml` declares a Docker web service named `flodss`, on the free plan in
  Frankfurt. It does **not** explicitly declare a repository, branch, or auto-deploy
  setting; therefore the file alone cannot verify that an existing service tracks
  `main` or has auto-deploy enabled.
- `Dockerfile` builds the React frontend with `npm run build`, copies its output
  to `frontend/dist`, and starts FastAPI with Uvicorn on Render's injected `PORT`.
  No separate frontend publish command or deploy hook is required by this image.
- `AUTH_ENFORCED=false` and `AI_ENABLED=false` are currently declared. Authentication
  is not enforced by this configuration; do not treat it as secure private hosting.
- SQLite uses `data/flodss_research.db`. No persistent disk is declared, so runtime
  writes must not be assumed to survive redeployments or instance replacement.

## Verify an existing, approved service

1. In Render, open the service and confirm its repository is
   `PaelenRune/FLODSS`, branch is `main`, and Dockerfile path is `./Dockerfile`
   with repository root as its build context.
2. Check **Settings > Build & Deploy > Auto-Deploy**. If enabled for commits,
   pushing `main` should enqueue a Docker rebuild. If disabled, use
   **Manual Deploy > Deploy latest commit** after approval. If configured to wait
   for checks, ensure the required checks complete. A deploy hook is optional,
   not required by the repository configuration.
3. In **Events**, confirm that the deployment commit matches `git rev-parse HEAD`,
   inspect build/start logs, and wait for the deployment to become live.
4. Open the service URL and verify the cockpit, layout-editor navigation, and
   existing API functionality. The cockpit is explicitly labeled as an illustrative
   reference dataset, not live solver output.

## Verification record (2026-10-26)

- Local frontend production build passed (`npm.cmd run build`); Vite reported a
  non-blocking JavaScript chunk-size warning.
- Repository configuration and Docker startup were inspected, not executed on Render.
- Live Render service settings, deployment events, and deployment success were not
  accessible during this check. A successful Git push is not proof of deployment.
- Local `.orchestrator/` state and `.openchamber/` screenshots are intentionally
  excluded from Git and the Docker build context.
