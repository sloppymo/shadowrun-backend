# Shadowrun RPG System - Development Makefile

.PHONY: help install test test-all test-security test-race test-coverage lint format run clean docker-build docker-run qa dev-setup

# Default target
help:
	@echo "Shadowrun RPG System - Available Commands:"
	@echo "  make install       - Install all dependencies"
	@echo "  make test          - Run all tests"
	@echo "  make test-security - Run security tests only"
	@echo "  make test-race     - Run race condition tests"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo "  make lint          - Run code linters"
	@echo "  make format        - Format code with black/prettier"
	@echo "  make run           - Run development servers"
	@echo "  make qa            - Run complete QA suite"
	@echo "  make dev-setup     - Setup development environment"
	@echo "  make clean         - Clean temporary files"

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	cd shadowrun-backend && pip install -r requirements.txt
	cd shadowrun-backend && pip install -r requirements-dev.txt
	@echo "Installing frontend dependencies..."
	cd shadowrun-interface && npm install

# Run all tests
test:
	@echo "Running backend tests..."
	cd shadowrun-backend && python -m pytest tests/ -v
	@echo "Running frontend tests..."
	cd shadowrun-interface && npm test

# Security tests
test-security:
	@echo "Running security vulnerability tests..."
	cd shadowrun-backend && python -m pytest tests/test_security.py -v --tb=short

# Race condition tests
test-race:
	@echo "Running race condition tests..."
	cd shadowrun-backend && python -m pytest tests/test_race_conditions.py -v --tb=short

# Test coverage
test-coverage:
	@echo "Running tests with coverage..."
	cd shadowrun-backend && python -m pytest tests/ --cov=. --cov-report=html --cov-report=term
	cd shadowrun-interface && npm run test:coverage

# Linting
lint:
	@echo "Linting backend code..."
	cd shadowrun-backend && flake8 . --max-line-length=100 --exclude=venv,__pycache__
	cd shadowrun-backend && mypy . --ignore-missing-imports
	@echo "Linting frontend code..."
	cd shadowrun-interface && npm run lint

# Format code
format:
	@echo "Formatting backend code..."
	cd shadowrun-backend && black . --line-length=100 --exclude=venv
	@echo "Formatting frontend code..."
	cd shadowrun-interface && npm run format

# Run development servers
run:
	@echo "Starting development servers..."
	@echo "Backend: http://localhost:5000"
	@echo "Frontend: http://localhost:3000"
	@echo "Press Ctrl+C to stop"
	@trap 'kill %1; kill %2' INT; \
	cd shadowrun-backend && python app.py & \
	cd shadowrun-interface && npm run dev & \
	wait

# Complete QA suite
qa:
	@echo "Running complete QA suite..."
	@echo "1. Security tests..."
	@make test-security
	@echo "2. Race condition tests..."
	@make test-race
	@echo "3. Unit tests..."
	@make test
	@echo "4. Linting..."
	@make lint
	@echo "5. Coverage report..."
	@make test-coverage
	@echo "QA Complete! Check reports in coverage/ directory"

# Development setup
dev-setup:
	@echo "Setting up development environment..."
	@echo "1. Creating Python virtual environment..."
	cd shadowrun-backend && python3 -m venv venv
	@echo "2. Installing dependencies..."
	@make install
	@echo "3. Setting up pre-commit hooks..."
	cd shadowrun-backend && pre-commit install
	@echo "4. Creating .env files..."
	@if [ ! -f shadowrun-backend/.env ]; then \
		echo "Creating backend .env file..."; \
		cp shadowrun-backend/.env.example shadowrun-backend/.env; \
	fi
	@if [ ! -f shadowrun-interface/.env.local ]; then \
		echo "Creating frontend .env file..."; \
		cp shadowrun-interface/.env.example shadowrun-interface/.env.local; \
	fi
	@echo "5. Initializing database..."
	cd shadowrun-backend && python -c "from app import app, db; app.app_context().push(); db.create_all()"
	@echo "Development environment ready!"

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf shadowrun-backend/htmlcov
	rm -rf shadowrun-backend/.pytest_cache
	rm -rf shadowrun-interface/.next
	rm -rf shadowrun-interface/coverage
	@echo "Clean complete!"

# Docker commands
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-run:
	@echo "Running with Docker..."
	docker-compose up

# Database migrations
db-migrate:
	@echo "Running database migrations..."
	cd shadowrun-backend && flask db upgrade

db-reset:
	@echo "Resetting database..."
	cd shadowrun-backend && python -c "from app import app, db; app.app_context().push(); db.drop_all(); db.create_all()"
	@echo "Database reset complete!"

# Performance testing
test-perf:
	@echo "Running performance tests..."
	cd shadowrun-backend && locust -f tests/test_performance.py --headless -u 100 -r 10 -t 60s

# Stress testing
test-stress:
	@echo "Running stress tests..."
	cd shadowrun-backend && python tests/test_stress.py

# Security audit
audit:
	@echo "Running security audit..."
	cd shadowrun-backend && safety check
	cd shadowrun-backend && bandit -r . -x /venv/
	cd shadowrun-interface && npm audit

# Generate test data
test-data:
	@echo "Generating test data..."
	cd shadowrun-backend && python scripts/generate_test_data.py

# API documentation
docs-api:
	@echo "Generating API documentation..."
	cd shadowrun-backend && python scripts/generate_api_docs.py

# Full deployment check
deploy-check:
	@echo "Running deployment readiness check..."
	@make qa
	@make audit
	@echo "Checking environment variables..."
	cd shadowrun-backend && python scripts/check_env.py
	@echo "Deployment check complete!" 