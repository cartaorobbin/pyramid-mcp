.PHONY: help install test check format lint clean docs serve-docs docker-build-examples docker-test-examples docker-clean docker-check docker-run-secure

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and setup development environment
	poetry install
	poetry run pre-commit install

test: ## Run all tests with coverage
	poetry run pytest

test-unit: ## Run only unit tests
	poetry run pytest -m unit

test-integration: ## Run only integration tests  
	poetry run pytest -m integration

test-fast: ## Run tests excluding slow ones
	poetry run pytest -m "not slow"

test-verbose: ## Run tests with verbose output
	poetry run pytest -v

test-coverage: ## Run tests and generate HTML coverage report
	poetry run pytest --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

check: ## Run all code quality checks
	poetry run black --check pyramid_mcp tests examples
	poetry run isort --check-only pyramid_mcp tests examples
	poetry run flake8 pyramid_mcp tests examples
	poetry run mypy pyramid_mcp

format: ## Format code with black and isort
	poetry run black pyramid_mcp tests examples
	poetry run isort pyramid_mcp tests examples

lint: ## Run linting checks
	poetry run flake8 pyramid_mcp tests examples
	poetry run mypy pyramid_mcp

clean: ## Clean up build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

watch-tests: ## Run tests in watch mode (requires pytest-watch)
	poetry run ptw

# Docker Development Commands

docker-check: ## Verify Docker is working in dev container
	@echo "🐳 Checking Docker functionality..."
	docker --version
	docker info --format "Docker is running: {{.ServerVersion}}"
	@echo "✅ Docker check complete"

docker-build-examples: ## Build all example Docker images
	@echo "🔨 Building example Docker images..."
	@if [ -f examples/secure/Dockerfile ]; then \
		echo "Building secure example..."; \
		cd examples/secure && docker build -t pyramid-mcp-secure:latest .; \
	fi
	@if [ -f examples/simple/Dockerfile ]; then \
		echo "Building simple example..."; \
		cd examples/simple && docker build -t pyramid-mcp-simple:latest .; \
	fi
	@echo "✅ Docker build complete"

docker-test-examples: ## Test example Docker containers
	@echo "🧪 Testing example Docker containers..."
	@if docker image inspect pyramid-mcp-secure:latest >/dev/null 2>&1; then \
		echo "Testing secure example container..."; \
		docker run --rm -d --name test-secure -p 8080:8080 pyramid-mcp-secure:latest && \
		sleep 5 && \
		curl -f http://localhost:8080/health && \
		docker stop test-secure; \
	else \
		echo "⚠️  pyramid-mcp-secure:latest not found, run 'make docker-build-examples' first"; \
	fi
	@echo "✅ Docker test complete"

docker-run-secure: ## Run the secure example container interactively
	@echo "🚀 Starting secure example container..."
	@if docker image inspect pyramid-mcp-secure:latest >/dev/null 2>&1; then \
		docker run --rm -p 8080:8080 --name pyramid-mcp-secure pyramid-mcp-secure:latest; \
	else \
		echo "❌ pyramid-mcp-secure:latest not found, run 'make docker-build-examples' first"; \
	fi

docker-clean: ## Clean up Docker images and containers
	@echo "🧹 Cleaning up Docker resources..."
	-docker stop $(shell docker ps -q --filter "ancestor=pyramid-mcp-secure:latest" --filter "ancestor=pyramid-mcp-simple:latest") 2>/dev/null || true
	-docker rm $(shell docker ps -aq --filter "ancestor=pyramid-mcp-secure:latest" --filter "ancestor=pyramid-mcp-simple:latest") 2>/dev/null || true
	-docker rmi pyramid-mcp-secure:latest pyramid-mcp-simple:latest 2>/dev/null || true
	@echo "✅ Docker cleanup complete"

build: ## Build the package
	poetry build

publish: ## Publish to PyPI (requires authentication)
	poetry publish