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
3. Set the `/api` rewrite in `frontend/vercel.json` to your Render service URL
   (currently `https://flask-api-wksi.onrender.com`).
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

## RAG settings (Marginalia)
- **`ANTHROPIC_API_KEY`** is required to answer questions (Render: set it on the service; Docker: put it in `.env`).
- **Embeddings** default to a local model (`fastembed`, no key). It needs ~300 MB of RAM, which is tight on
  Render's free 512 MB tier. If you hit memory limits, use an API provider: `pip install langchain-voyageai`
  (or `langchain-openai`), set `EMBEDDINGS_PROVIDER=voyage|openai`, `EMBEDDING_MODEL`, the provider's API key,
  and **`EMBEDDING_DIM` to that model's output size** (check the provider docs), on a fresh database.
- **pgvector**: the app runs `CREATE EXTENSION IF NOT EXISTS vector` on boot. If your DB user isn't allowed,
  run it once as an admin: `psql "$DATABASE_URL" -c 'CREATE EXTENSION vector;'`.
- **Big uploads / streaming on Vercel**: set `VITE_API_URL=https://<your-service>.onrender.com` in the Vercel
  project env (Production) and `CORS_ORIGINS=https://<your-app>.vercel.app` on Render. The browser then talks to
  the API directly, avoiding proxy body limits and response buffering.
- Switching the local compose DB image to pgvector: run `make reset` once (alpine→debian volume change).
