# Deployment (GitHub Actions → Render + Vercel)

Pipeline (`.github/workflows/ci-cd.yml`): on every push/PR it lints + tests the backend, builds the Docker
image, and builds the frontend. On push to `main`, only if all of that passed: deploy backend (Render)
→ deploy frontend (Vercel). PRs run checks only.

## One-time setup
1. **Render**: New → Blueprint → select this repo (`render.yaml`). Wait for the first deploy.
   Then Service → Settings → **Deploy Hook** → copy the URL.
2. **Vercel** (do NOT import the repo via Git, the pipeline deploys):
   `cd frontend && npx vercel link` → creates the project and `.vercel/project.json` (orgId, projectId).
   Create a token at vercel.com/account/tokens.
3. Edit `frontend/vercel.json`: replace `YOUR-SERVICE.onrender.com` with your Render URL.
4. **GitHub** → Settings → Environments → `production` → add secrets:
   `RENDER_DEPLOY_HOOK_URL`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
   (Optional: add required reviewers there for manual approval.)
5. **GitHub** → Settings → Branches → protect `main`: require PR + the `backend` and `frontend` checks.
6. Push to `main`.

## Notes
- Free Render web services sleep when idle (slow first request); free Postgres/Key Value have
  limits and expiry rules, check Render's current plan terms.
- Seeded demo users are created on boot while `SEED_ON_START=true`. Disable before real users.
- Schema changes: add Flask-Migrate and run migrations via `preDeployCommand` in `render.yaml`.
