# Marginalia

Marginalia is a full-stack app for asking questions about PDF documents. Upload a PDF, ask questions in natural language, and get streamed answers with citations that link back to the source pages. It also includes account registration, sign-in, and a small posts feature.

## What’s inside

- **Frontend:** React and Vite
- **API:** Flask, SQLAlchemy, and JWT authentication
- **RAG:** PDF text extraction, chunking, vector search with PostgreSQL and pgvector, and Groq-powered answers
- **Local services:** Docker Compose starts the frontend, API, PostgreSQL, and Redis together
- **Tests:** Pytest backend tests and a production frontend build

## Run locally with Docker

### Requirements

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose enabled
- A [Groq API key](https://console.groq.com/keys) to generate AI answers. The app can start without one, but asking questions will require it.

### 1. Clone the repository

```powershell
git clone https://github.com/salimBenSlim1/flask-project.git
cd flask-project
```

### 2. Create your local environment file

In PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `ANTHROPIC_API_KEY` to your **Groq** API key and keep `ANTHROPIC_MODEL=openai/gpt-oss-20b`, or use another model supported by your Groq account. The `ANTHROPIC_*` names are retained for compatibility with the existing Render environment; they configure Groq in this project. Never commit `.env` or paste API keys into source files.

The default embedding provider is local FastEmbed, so it does not need another API key.

### 3. Start the app

Make sure Docker Desktop is running, then run:

```powershell
docker compose up -d --build --wait
docker compose exec api flask --app run seed
```

The first build may take a few minutes while dependencies and the local embedding model are downloaded.

Open:

- **App:** [http://localhost:3000](http://localhost:3000)
- **API health:** [http://localhost:5000/health](http://localhost:5000/health)

For the seeded local demo, sign in with `alice@example.com` / `Alice1234!`.

### Stop or inspect the app

```powershell
docker compose logs -f
docker compose down
```

`docker compose down` keeps the database volumes. To delete the local database and Redis data too, run `docker compose down -v`—this is destructive and cannot be undone.

## Run tests

The backend tests use an in-memory SQLite database and do not require Docker:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

Build the frontend separately with Node.js 22 or newer:

```powershell
cd frontend
npm ci
npm run build
```

## Publish your copy on GitHub

1. Create a new, empty repository on GitHub. If you are publishing your own copy, use your own repository URL.
2. From the project root, check the current branch and remote:

   ```powershell
   git branch --show-current
   git remote -v
   ```

3. If `origin` still points to this project, change it to your new repository:

   ```powershell
   git remote set-url origin https://github.com/<your-username>/<your-repository>.git
   ```

4. Commit and push your work:

   ```powershell
   git add .
   git commit -m "Describe your changes"
   git push -u origin HEAD
   ```

This project’s GitHub Actions workflow currently listens for pushes to `master`. Keep that branch name for the existing workflow, or update the branch filters in `.github/workflows/ci-cd.yml` if you choose a different default branch. Before pushing, verify that `.env` is ignored and that no API keys or other secrets are staged.

## Deployment

Deployment to Render and Vercel is documented in [docs/DEPLOY.md](docs/DEPLOY.md). Production AI configuration belongs in the Render API service environment—not in the frontend or GitHub source. For a real deployment, disable demo-data seeding and replace development secrets with secure production values.
