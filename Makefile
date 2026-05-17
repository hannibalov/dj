.PHONY: install lint lint-fix test test-backend test-frontend typecheck run-api

install:
	./install.sh

lint:
	$(MAKE) lint-backend
	$(MAKE) lint-frontend

lint-fix:
	cd backend && .venv/bin/ruff check . --fix && .venv/bin/ruff format .
	cd frontend && npm run lint:fix

lint-backend:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app tests

lint-frontend:
	cd frontend && npm run lint && npm run typecheck

test: test-backend test-frontend

test-backend:
	cd backend && .venv/bin/pytest -q

test-frontend:
	cd frontend && npm test

typecheck:
	cd frontend && npm run typecheck

run-api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
