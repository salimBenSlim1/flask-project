.DEFAULT_GOAL := help
-include .env
API_PORT ?= 5000
FRONTEND_PORT ?= 3000
COMPOSE := docker compose

.PHONY: help env up down restart logs seed reset infra dev front test psql redis-cli

help: ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example (with a random SECRET_KEY) if missing
	@if [ -f .env ]; then echo ".env already exists, leaving it alone"; else \
	    SECRET=$$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets;print(secrets.token_hex(32))"); \
	    sed "s/^SECRET_KEY=.*/SECRET_KEY=$$SECRET/" .env.example > .env; \
	    echo "Created .env"; fi

up: env ## Build & start EVERYTHING (frontend + api + postgres + redis), seed demo users
	$(COMPOSE) up -d --build --wait
	$(COMPOSE) exec api flask --app run seed
	@echo ""
	@echo "  Frontend: http://localhost:$(FRONTEND_PORT)"
	@echo "  API:      http://localhost:$(API_PORT)/health"
	@[ -n "$(ANTHROPIC_API_KEY)" ] || echo "\n  Note: set ANTHROPIC_API_KEY in .env, then run make restart s=api, to enable answers."

down: ## Stop containers (keeps data)
	$(COMPOSE) down

restart: ## Rebuild & restart. Optional: make restart s=api|frontend
	$(COMPOSE) up -d --build --wait $(s)

logs: ## Tail logs. Optional: make logs s=api|frontend|db|redis
	$(COMPOSE) logs -f $(s)

seed: ## (Re)run the seed script inside the api container (idempotent)
	$(COMPOSE) exec api flask --app run seed

reset: ## Destroy containers AND volumes (wipes DB), then start fresh
	$(COMPOSE) down -v
	$(MAKE) up

infra: env ## Start only postgres + redis (for running Flask on your host)
	$(COMPOSE) up -d --wait db redis

dev: infra ## Run Flask on your host with auto-reload (needs pip install); pair with `make front`
	flask --app run seed
	flask --app run run --debug --port $(API_PORT)

front: ## Run the Vite dev server with hot reload on :3000 (proxies /api to Flask)
	cd frontend && npm install && npm run dev

test: ## Run the backend test suite (in-memory SQLite, no Docker needed)
	python -m pytest -q

psql: ## Open a psql shell in the db container
	$(COMPOSE) exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

redis-cli: ## Open redis-cli in the redis container
	$(COMPOSE) exec redis redis-cli
