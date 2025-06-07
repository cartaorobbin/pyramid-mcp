.PHONY: help install test check format lint clean docs serve-docs

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
	poetry run black --check pyramid_mcp tests
	poetry run isort --check-only pyramid_mcp tests
	poetry run flake8 pyramid_mcp tests
	poetry run mypy pyramid_mcp

format: ## Format code with black and isort
	poetry run black pyramid_mcp tests
	poetry run isort pyramid_mcp tests

lint: ## Run linting checks
	poetry run flake8 pyramid_mcp tests
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

build: ## Build the package
	poetry build

publish: ## Publish to PyPI (requires authentication)
	poetry publish