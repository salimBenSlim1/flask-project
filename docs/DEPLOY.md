# Deployment (Git integration → Render + Vercel)

Vercel and Render deploy directly from GitHub on pushes to `master`; GitHub Actions is not required for
deployments. The optional workflow (`.github/workflows/ci-cd.yml`) runs backend and frontend checks only
when manually started.

## One-time setup
1. **Render**: Connect this repo as a Blueprint using `render.yaml`. The API's Docker root is `backend/`.
   Sync the Blueprint to apply `autoDeployTrigger: commit` and deploy commits from the connected branch.
2. **Vercel**: Connect the project to this repo and set its production branch to `master`.
3. Set the `/api` rewrite in `frontend/vercel.json` to your Render service URL
   (currently `https://flask-api-wksi.onrender.com`).
4. On each push to `master`, both providers build and deploy independently of GitHub Actions.

## Notes
- Free Render web services sleep when idle (slow first request); free Postgres/Key Value have
  limits and expiry rules, check Render's current plan terms.
- Seeded demo users are created on boot while `SEED_ON_START=true`. Disable before real users.
- Schema changes: add Flask-Migrate and run migrations via `preDeployCommand` in `render.yaml`.

## RAG settings (Marginalia)
- **Groq** is used to answer questions. Set `ANTHROPIC_API_KEY` to your Groq API key and
  `ANTHROPIC_MODEL` to the Groq model name (for example, `openai/gpt-oss-20b`) on Render.
  The existing variable names are retained so the current Render environment does not need renaming.
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
