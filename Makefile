.PHONY: help install run test lint fmt migrate revision clean

help:
	@echo "Targets:"
	@echo "  install   Create venv and install dependencies"
	@echo "  run       Start the bot (long polling)"
	@echo "  test      Run the test suite"
	@echo "  migrate   Apply Alembic migrations to head"
	@echo "  revision  Autogenerate a new Alembic revision (m='message')"
	@echo "  clean     Remove caches and build artifacts"

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

run:
	. .venv/bin/activate && python -m bot.main

test:
	. .venv/bin/activate && pytest -q

migrate:
	. .venv/bin/activate && alembic upgrade head

revision:
	. .venv/bin/activate && alembic revision --autogenerate -m "$(m)"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache
