# Marginalia

Marginalia is a full-stack app for asking questions about PDF documents. Upload a PDF, ask questions in natural language, and get streamed answers with citations that link back to the source pages. It also includes account registration, sign-in, and a small posts feature.

## What’s inside

- **Frontend:** React and Vite
- **API:** Flask, SQLAlchemy, and JWT authentication
- **RAG:** PDF text extraction, chunking, vector search with PostgreSQL and pgvector, and Groq-powered answers
- **Local services:** Docker Compose starts the frontend, API, PostgreSQL, and Redis together
- **Tests:** Pytest backend tests and a production frontend build

The backend is organized under [`backend/`](backend/): the Flask package, tests, Dockerfile, Python dependencies, and entry point are kept together. The root directory contains the frontend, Compose/Make configuration, and deployment files.

## Run locally

### Requirements

- [Git](https://git-scm.com/)
- [GNU Make](https://www.gnu.org/software/make/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose enabled. You will use the Make commands below; Make runs Docker Compose for you.
- A [Groq API key](https://console.groq.com/keys) to generate AI answers. The app can start without one, but asking questions will require it.

On Windows, run these commands from a terminal with `make` available (for example, WSL or a Unix-compatible development environment).

### 1. Clone the repository and enter its folder

```powershell
git clone https://github.com/salimBenSlim1/flask-project.git
cd flask-project
```

### 2. Create and configure `.env`

From the project root:

```sh
make env
```

Open the generated `.env` file in your editor. Set `ANTHROPIC_API_KEY` to your **Groq** API key and keep `ANTHROPIC_MODEL=openai/gpt-oss-20b`, or use another model supported by your Groq account. The `ANTHROPIC_*` names are retained for compatibility with the existing Render environment; they configure Groq in this project. Never commit `.env` or paste API keys into source files.

The default embedding provider is local FastEmbed, so it does not need another API key.

### 3. Start everything

Start Docker Desktop, then from the project root run:

```sh
make up
```

`make up` builds and starts the frontend, Flask API, PostgreSQL, and Redis, waits for them to become healthy, and seeds the demo users. The first run may take a few minutes while dependencies and the local embedding model are downloaded.

Open:

- **App:** [http://localhost:3000](http://localhost:3000)
- **API health:** [http://localhost:5000/health](http://localhost:5000/health)

Docker Compose publishes the frontend on port `3000`, the API on `5000`, PostgreSQL on `5432`, and Redis on `6379`. Edit `FRONTEND_PORT` or `API_PORT` in `.env` to change the host ports for the web app and API.

For the seeded local demo, sign in with `alice@example.com` / `Alice1234!`.

### Common commands

```sh
make logs
make down
make test
```

`make down` stops the app but keeps database data. `make test` runs the backend tests without Docker. `make help` lists the available targets. `make reset` deletes the local database and Redis data before starting over; this is destructive and cannot be undone.

## Run tests

The backend tests use an in-memory SQLite database and do not require Docker:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Set-Location backend
python -m pytest -q
```

Build the frontend separately with Node.js 22 or newer:

```powershell
Set-Location ..\frontend
npm ci
npm run build
```

## Publish your copy on GitHub

1. Create a new, empty repository on GitHub. If you are publishing your own copy, use your own repository URL.
2. Return to the project root and check the current branch and remote:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
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

Production deploys are handled directly by Vercel and Render when changes are pushed to `master`; GitHub Actions is manual-only. See [docs/DEPLOY.md](docs/DEPLOY.md) for the one-time provider setup. Before pushing, verify that `.env` is ignored and that no API keys or other secrets are staged.

## Deployment

Deployment to Render and Vercel is documented in [docs/DEPLOY.md](docs/DEPLOY.md). Production AI configuration belongs in the Render API service environment—not in the frontend or GitHub source. For a real deployment, disable demo-data seeding and replace development secrets with secure production values.
