#!/bin/bash

# StackDebt Monitoring Script
set -e

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

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

# Check service health
check_service_health() {
    local service_name=$1
    local health_url=$2
    local timeout=${3:-10}
    
    if curl -f --max-time "$timeout" "$health_url" > /dev/null 2>&1; then
        log_success "$service_name is healthy"
        return 0
    else
        log_error "$service_name health check failed"
        return 1
    fi
}

# Get service stats
get_service_stats() {
    log_info "Fetching service statistics..."
    
    echo ""
    echo "🔍 Backend Performance Stats:"
    curl -s "$BACKEND_URL/api/performance/stats" | jq '.' 2>/dev/null || echo "Unable to fetch performance stats"
    
    echo ""
    echo "💾 Cache Statistics:"
    curl -s "$BACKEND_URL/api/cache/stats" | jq '.' 2>/dev/null || echo "Unable to fetch cache stats"
    
    echo ""
    echo "🌐 External Services Status:"
    curl -s "$BACKEND_URL/api/external-services/status" | jq '.' 2>/dev/null || echo "Unable to fetch external services status"
    
    echo ""
    echo "📊 Encyclopedia Statistics:"
    curl -s "$BACKEND_URL/api/encyclopedia/stats" | jq '.' 2>/dev/null || echo "Unable to fetch encyclopedia stats"
}

# Check Docker containers
check_containers() {
    log_info "Checking Docker container status..."
    
    if [ -f "$COMPOSE_FILE" ] && [ -f "$ENV_FILE" ]; then
        echo ""
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    else
        log_warning "Production compose file or environment file not found"
        echo ""
        docker ps --filter "name=stackdebt"
    fi
}

# Check resource usage
check_resources() {
    log_info "Checking resource usage..."
    
    echo ""
    echo "💻 System Resources:"
    echo "Memory Usage:"
    free -h
    echo ""
    echo "Disk Usage:"
    df -h
    echo ""
    echo "Docker Container Resources:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" $(docker ps --filter "name=stackdebt" -q) 2>/dev/null || echo "No StackDebt containers running"
}

# Check logs for errors
check_logs() {
    local service=${1:-all}
    local lines=${2:-50}
    
    log_info "Checking recent logs for errors..."
    
    if [ "$service" = "all" ]; then
        if [ -f "$COMPOSE_FILE" ] && [ -f "$ENV_FILE" ]; then
            echo ""
            echo "🔍 Recent Backend Logs (last $lines lines):"
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail="$lines" backend | grep -i error || echo "No errors found in backend logs"
            
            echo ""
            echo "🔍 Recent Frontend Logs (last $lines lines):"
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail="$lines" frontend | grep -i error || echo "No errors found in frontend logs"
            
            echo ""
            echo "🔍 Recent Database Logs (last $lines lines):"
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail="$lines" database | grep -i error || echo "No errors found in database logs"
        else
            log_warning "Production compose file not found, checking individual containers"
            docker logs --tail="$lines" stackdebt-archeologist-prod 2>/dev/null | grep -i error || echo "No backend container or errors found"
            docker logs --tail="$lines" stackdebt-interrogator-prod 2>/dev/null | grep -i error || echo "No frontend container or errors found"
            docker logs --tail="$lines" stackdebt-encyclopedia-prod 2>/dev/null | grep -i error || echo "No database container or errors found"
        fi
    else
        if [ -f "$COMPOSE_FILE" ] && [ -f "$ENV_FILE" ]; then
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail="$lines" "$service"
        else
            docker logs --tail="$lines" "stackdebt-$service-prod" 2>/dev/null || log_error "Container stackdebt-$service-prod not found"
        fi
    fi
}

# Full health check
full_health_check() {
    log_info "Performing comprehensive health check..."
    
    local overall_health=0
    
    # Check individual services
    check_service_health "Backend" "$BACKEND_URL/health" 10 || overall_health=1
    check_service_health "Frontend" "$FRONTEND_URL" 10 || overall_health=1
    
    # Check containers
    check_containers
    
    # Check for recent errors
    check_logs all 20
    
    if [ $overall_health -eq 0 ]; then
        log_success "Overall system health: HEALTHY ✅"
    else
        log_error "Overall system health: DEGRADED ❌"
    fi
    
    return $overall_health
}

# Performance monitoring
performance_monitor() {
    log_info "Starting performance monitoring (press Ctrl+C to stop)..."
    
    while true; do
        clear
        echo "🔄 StackDebt Performance Monitor - $(date)"
        echo "========================================"
        
        # Quick health check
        echo ""
        echo "🏥 Health Status:"
        check_service_health "Backend" "$BACKEND_URL/health" 5 && echo -n "✅ Backend " || echo -n "❌ Backend "
        check_service_health "Frontend" "$FRONTEND_URL" 5 && echo "✅ Frontend" || echo "❌ Frontend"
        
        # Resource usage
        echo ""
        echo "💻 Resource Usage:"
        docker stats --no-stream --format "{{.Container}}: CPU {{.CPUPerc}} | Memory {{.MemUsage}}" $(docker ps --filter "name=stackdebt" -q) 2>/dev/null || echo "No containers running"
        
        # Performance stats
        echo ""
        echo "📊 Performance Metrics:"
        curl -s "$BACKEND_URL/api/performance/stats" | jq -r '.performance | "Analysis Count: \(.total_analyses // 0) | Avg Response Time: \(.average_response_time_ms // 0)ms | Cache Hit Rate: \(.cache_hit_rate // 0)%"' 2>/dev/null || echo "Unable to fetch performance metrics"
        
        sleep 10
    done
}

# Main function
main() {
    case "${1:-health}" in
        "health")
            full_health_check
            ;;
        "stats")
            get_service_stats
            ;;
        "containers")
            check_containers
            ;;
        "resources")
            check_resources
            ;;
        "logs")
            check_logs "${2:-all}" "${3:-50}"
            ;;
        "monitor")
            performance_monitor
            ;;
        *)
            echo "StackDebt Monitoring Script"
            echo "=========================="
            echo ""
            echo "Usage: $0 {health|stats|containers|resources|logs|monitor}"
            echo ""
            echo "Commands:"
            echo "  health      - Perform comprehensive health check (default)"
            echo "  stats       - Show service statistics and performance metrics"
            echo "  containers  - Show Docker container status"
            echo "  resources   - Show system and container resource usage"
            echo "  logs        - Show recent logs (optional: service name, line count)"
            echo "  monitor     - Start real-time performance monitoring"
            echo ""
            echo "Examples:"
            echo "  $0 health"
            echo "  $0 logs backend 100"
            echo "  $0 monitor"
            exit 1
            ;;
    esac
}

# Check if jq is available for JSON parsing
if ! command -v jq &> /dev/null; then
    log_warning "jq is not installed. JSON output will not be formatted."
    log_info "Install jq for better output formatting: apt-get install jq"
fi

# Run main function
main "$@"