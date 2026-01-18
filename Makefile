# StackDebt Development Makefile

.PHONY: help setup start stop clean test test-db logs build status deploy-prod monitor-prod

help: ## Show this help message
	@echo "StackDebt Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $1, $2}'

setup: ## Set up the development environment
	@echo "Setting up StackDebt development environment..."
	@cp .env.example .env
	@echo "✅ Environment file created"
	@echo "🚀 Run 'make start' to start all services"

start: ## Start all services with Docker Compose (development)
	@echo "Starting StackDebt services in development mode..."
	@docker-compose up -d
	@echo "✅ Services started!"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"
	@echo "   Database: localhost:5432"

stop: ## Stop all services
	@echo "Stopping StackDebt services..."
	@docker-compose down
	@echo "✅ Services stopped"

clean: ## Stop services and remove volumes
	@echo "Cleaning up StackDebt environment..."
	@docker-compose down -v
	@docker system prune -f
	@echo "✅ Environment cleaned"

build: ## Build all Docker images
	@echo "Building Docker images..."
	@docker-compose build

status: ## Show status of all services
	@docker-compose ps

logs: ## Show logs from all services
	@docker-compose logs -f

logs-backend: ## Show backend logs only
	@docker-compose logs -f backend

logs-frontend: ## Show frontend logs only
	@docker-compose logs -f frontend

logs-database: ## Show database logs only
	@docker-compose logs -f database

# Production deployment commands
deploy-prod: ## Deploy StackDebt in production mode
	@echo "🚀 Deploying StackDebt in production mode..."
	@./scripts/deploy.sh deploy

stop-prod: ## Stop production deployment
	@echo "Stopping StackDebt production services..."
	@./scripts/deploy.sh stop

restart-prod: ## Restart production services
	@echo "Restarting StackDebt production services..."
	@./scripts/deploy.sh restart

logs-prod: ## Show production logs
	@./scripts/deploy.sh logs

health-prod: ## Check production health
	@./scripts/deploy.sh health

monitor-prod: ## Start production monitoring
	@./scripts/monitor.sh monitor

# Development commands
dev-backend: ## Start backend in development mode (local Python)
	@echo "Starting backend in development mode..."
	@cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend in development mode (local Node.js)
	@echo "Starting frontend in development mode..."
	@cd frontend && npm start

install-backend: ## Install backend dependencies locally
	@echo "Installing backend dependencies..."
	@cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies locally
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install

# Testing commands
test-backend: ## Run backend tests
	@echo "Running backend tests..."
	@cd backend && pytest

test-frontend: ## Run frontend tests
	@echo "Running frontend tests..."
	@cd frontend && npm test

test-db: ## Test database connection and setup
	@echo "Testing database setup..."
	@cd backend && python test_database_setup.py

test-all: ## Run all tests
	@echo "Running all tests..."
	@make test-backend
	@make test-frontend

# Utility commands
shell-backend: ## Open shell in backend container
	@docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	@docker-compose exec frontend sh

shell-database: ## Open PostgreSQL shell
	@docker-compose exec database psql -U stackdebt_user -d stackdebt_encyclopedia

backup-db: ## Backup production database
	@echo "Creating database backup..."
	@docker-compose -f docker-compose.prod.yml --env-file .env.production exec -T database pg_dump -U stackdebt_user stackdebt_encyclopedia > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created"

restore-db: ## Restore database from backup (usage: make restore-db BACKUP=backup_file.sql)
	@echo "Restoring database from $(BACKUP)..."
	@docker-compose -f docker-compose.prod.yml --env-file .env.production exec -T database psql -U stackdebt_user -d stackdebt_encyclopedia < $(BACKUP)
	@echo "✅ Database restored"