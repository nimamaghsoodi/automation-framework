.PHONY: up down logs api worker web migrate lint test gen-env

# Start everything (first run: docker compose up --build)
up:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

# Run just the API in dev mode (requires local .env + postgres + redis)
api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

# Run the Celery worker locally
worker:
	cd apps/api && celery -A app.celery_app worker --loglevel=info

# Run the web frontend
web:
	cd apps/web && npm run dev

# Apply Alembic migrations
migrate:
	cd apps/api && alembic upgrade head

# Generate a new migration (autogenerate from models)
# Usage: make migration MSG="add foo table"
migration:
	cd apps/api && alembic revision --autogenerate -m "$(MSG)"

# Install Python dev dependencies (run once)
install-backend:
	cd packages/sdk && pip install -e .
	cd packages/connectors && pip install -e .
	cd apps/api && pip install -e ".[dev]"

# Install frontend dependencies
install-frontend:
	cd apps/web && npm install

# Generate a .env file with random secrets
gen-env:
	@python3 -c " \
import secrets; \
from cryptography.fernet import Fernet; \
sk = secrets.token_urlsafe(32); \
ek = Fernet.generate_key().decode(); \
print(f'SECRET_KEY={sk}'); \
print(f'ENCRYPTION_KEY={ek}'); \
print('DATABASE_URL=postgresql+asyncpg://nexus:nexus_dev@localhost:5432/nexus'); \
print('DATABASE_URL_SYNC=postgresql+psycopg2://nexus:nexus_dev@localhost:5432/nexus'); \
print('REDIS_URL=redis://localhost:6379/0'); \
print('CELERY_BROKER_URL=redis://localhost:6379/0'); \
print('CELERY_RESULT_BACKEND=redis://localhost:6379/1'); \
print('ENVIRONMENT=development'); \
print('DEBUG=true'); \
" > apps/api/.env
	@echo "Generated apps/api/.env"

# Run backend tests
test:
	cd packages/connectors && pytest -v

# Lint
lint:
	cd apps/api && ruff check .
	cd packages/sdk && ruff check .
	cd packages/connectors && ruff check .
