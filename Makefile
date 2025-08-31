.PHONY: help install install-dev clean lint format type-check test test-cov run-appservice run-chat run-analyzer clear-db setup-dev

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment setup
install: ## Install the package
	pip install -e .

install-dev: ## Install the package with development dependencies
	pip install -e ".[dev]"

setup-dev: install-dev ## Setup development environment with pre-commit hooks
	pre-commit install

# Code quality
clean: ## Clean up build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

format: ## Format code with black and isort
	black src/ scripts/ tests/
	isort src/ scripts/ tests/

lint: ## Run linting checks
	flake8 src/ scripts/ tests/
	black --check src/ scripts/ tests/
	isort --check-only src/ scripts/ tests/

type-check: ## Run mypy type checking
	mypy scripts/run_appservice_server.py scripts/run_simulator_client.py scripts/run_chat_server.py scripts/run_analyzer_server.py scripts/run_dev_clear_db.py

type-check-all: ## Run mypy type checking on all source code
	mypy src/ scripts/

# Testing
test: ## Run tests
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=src/nirva_service --cov-report=html --cov-report=term

# Services
run-appservice: ## Start the appservice server
	python scripts/run_appservice_server.py

run-chat: ## Start the chat server
	python scripts/run_chat_server.py

run-analyzer: ## Start the analyzer server
	python scripts/run_analyzer_server.py

run-audio-processor: ## Start the audio processor server
	python scripts/run_audio_processor_server.py

clear-db: ## Clear database (development only)
	python scripts/run_dev_clear_db.py

run-all: ## Start all services using pm2
	./scripts/run_pm2script.sh

pm2-reload: ## Reload PM2 services without downtime
	pm2 reload ecosystem.config.js

pm2-stop: ## Stop all PM2 services
	pm2 stop all

pm2-status: ## Show PM2 service status
	pm2 status

pm2-logs: ## Show PM2 logs
	pm2 logs

# Database
db-upgrade: ## Run database migrations
	alembic upgrade head

db-revision: ## Create a new database migration
	alembic revision --autogenerate -m "$(message)"

# Development utilities
simulate: ## Run simulator client
	python scripts/run_simulator_client.py

logs: ## Show recent logs
	tail -f logs/*.log

# Docker (if needed in the future)
docker-build: ## Build Docker image
	docker build -t nirva-service .

docker-run: ## Run Docker container
	docker run -p 8000:8000 nirva-service

# Conda environment
conda-export: ## Export conda environment
	conda env export > environment.yml

conda-update: ## Update conda environment from environment.yml
	conda env update -f environment.yml

sync-requirements: ## Sync requirements.txt with environment.yml
	python scripts/sync_requirements.py

# Pre-commit
pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

# Build and distribution
build: clean ## Build the package
	python -m build

# Security
security-check: ## Run security checks
	pip-audit

# Deployment
deploy: ## Deploy to EC2 server (usage: make deploy server=52.73.87.226)
	./scripts/deploy_to_server.sh $(server)

deploy-ec2: ## Deploy to default EC2 server
	./scripts/deploy_to_server.sh 52.73.87.226
