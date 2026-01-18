#!/bin/bash

# StackDebt Production Deployment Script
set -e

echo "🚀 Starting StackDebt production deployment..."

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Production environment file $ENV_FILE not found."
        log_info "Please copy .env.production and configure it with your settings."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Validate environment configuration
validate_environment() {
    log_info "Validating environment configuration..."
    
    source "$ENV_FILE"
    
    # Check required variables
    required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set in $ENV_FILE"
            exit 1
        fi
    done
    
    # Check for default passwords
    if [ "$POSTGRES_PASSWORD" = "your_secure_database_password_here" ]; then
        log_error "Please set a secure database password in $ENV_FILE"
        exit 1
    fi
    
    if [ "$REDIS_PASSWORD" = "your_secure_redis_password_here" ]; then
        log_error "Please set a secure Redis password in $ENV_FILE"
        exit 1
    fi
    
    log_success "Environment configuration validated"
}

# Build and deploy
deploy() {
    log_info "Building and deploying StackDebt..."
    
    # Stop existing containers
    log_info "Stopping existing containers..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down || true
    
    # Build images
    log_info "Building Docker images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --no-cache
    
    # Start services
    log_info "Starting services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    check_health
    
    # Run integration tests
    run_integration_tests
}

# Health check
check_health() {
    log_info "Performing health checks..."
    
    # Check database
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T database pg_isready -U stackdebt_user -d stackdebt_encyclopedia; then
        log_success "Database is healthy"
    else
        log_error "Database health check failed"
        return 1
    fi
    
    # Check Redis
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T redis redis-cli ping | grep -q PONG; then
        log_success "Redis is healthy"
    else
        log_error "Redis health check failed"
        return 1
    fi
    
    # Check backend
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Backend is healthy"
    else
        log_error "Backend health check failed"
        return 1
    fi
    
    # Check frontend
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "Frontend is healthy"
    else
        log_error "Frontend health check failed"
        return 1
    fi
    
    log_success "All services are healthy"
}

# Run integration tests
run_integration_tests() {
    log_info "Running integration tests..."
    
    if [ -f "./scripts/integration-test.sh" ]; then
        if ./scripts/integration-test.sh quick; then
            log_success "Integration tests passed"
        else
            log_warning "Some integration tests failed, but deployment continues"
            log_info "Run './scripts/integration-test.sh' for detailed test results"
        fi
    else
        log_warning "Integration test script not found, skipping tests"
    fi
}

# Show deployment info
show_deployment_info() {
    log_success "🎉 StackDebt deployment completed successfully!"
    echo ""
    echo "📊 Service URLs:"
    echo "   Frontend:  http://localhost:3000"
    echo "   Backend:   http://localhost:8000"
    echo "   API Docs:  http://localhost:8000/docs"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View logs:     docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE logs -f"
    echo "   Stop services: docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down"
    echo "   Restart:       docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE restart"
    echo ""
    echo "📈 Monitoring:"
    echo "   Health check:  curl http://localhost:8000/health"
    echo "   Performance:   curl http://localhost:8000/api/performance/stats"
    echo "   Cache stats:   curl http://localhost:8000/api/cache/stats"
    echo ""
}

# Main execution
main() {
    echo "🏗️  StackDebt Production Deployment"
    echo "=================================="
    echo ""
    
    check_prerequisites
    validate_environment
    deploy
    show_deployment_info
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "test")
        log_info "Running integration tests..."
        ./scripts/integration-test.sh
        ;;
    "health")
        check_health
        ;;
    "stop")
        log_info "Stopping StackDebt services..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        log_success "Services stopped"
        ;;
    "logs")
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
        ;;
    "restart")
        log_info "Restarting StackDebt services..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
        log_success "Services restarted"
        ;;
    *)
        echo "Usage: $0 {deploy|health|stop|logs|restart|test}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Deploy StackDebt in production mode (default)"
        echo "  health   - Check health of all services"
        echo "  stop     - Stop all services"
        echo "  logs     - Show logs from all services"
        echo "  restart  - Restart all services"
        echo "  test     - Run integration tests"
        exit 1
        ;;
esac