#!/bin/bash

# StackDebt Integration Test Script
# Tests the complete deployment to ensure all components work together

set -e

# Configuration
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
TEST_TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    ((TESTS_TOTAL++))
    log_info "Running test: $test_name"
    
    if $test_function; then
        log_success "$test_name"
        return 0
    else
        log_failure "$test_name"
        return 1
    fi
}

# Wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local url="$2"
    local timeout="$3"
    
    log_info "Waiting for $service_name to be ready..."
    
    for i in $(seq 1 $timeout); do
        if curl -f --max-time 5 "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready"
            return 0
        fi
        sleep 1
    done
    
    log_failure "$service_name failed to become ready within ${timeout}s"
    return 1
}

# Test 1: Basic service health
test_service_health() {
    # Test backend health
    if ! curl -f --max-time 10 "$BACKEND_URL/health" > /dev/null 2>&1; then
        return 1
    fi
    
    # Test frontend availability
    if ! curl -f --max-time 10 "$FRONTEND_URL" > /dev/null 2>&1; then
        return 1
    fi
    
    return 0
}

# Test 2: Backend readiness
test_backend_readiness() {
    local response=$(curl -s --max-time 10 "$BACKEND_URL/ready")
    
    if echo "$response" | grep -q '"status":"ready"'; then
        return 0
    else
        return 1
    fi
}

# Test 3: Database connectivity
test_database_connectivity() {
    local response=$(curl -s --max-time 10 "$BACKEND_URL/api/encyclopedia/stats")
    
    if echo "$response" | grep -q '"status":"healthy"'; then
        return 0
    else
        return 1
    fi
}

# Test 4: Cache functionality
test_cache_functionality() {
    local response=$(curl -s --max-time 10 "$BACKEND_URL/api/cache/stats")
    
    if echo "$response" | grep -q '"cache_stats"'; then
        return 0
    else
        return 1
    fi
}

# Test 5: Website analysis
test_website_analysis() {
    local test_url="https://httpbin.org"
    local payload='{"url":"'$test_url'","analysis_type":"website"}'
    
    local response=$(curl -s --max-time 30 \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$BACKEND_URL/api/analyze")
    
    if echo "$response" | grep -q '"stack_age_result"'; then
        return 0
    else
        log_warning "Website analysis response: $response"
        return 1
    fi
}

# Test 6: GitHub analysis
test_github_analysis() {
    local test_repo="https://github.com/octocat/Hello-World"
    local payload='{"url":"'$test_repo'","analysis_type":"github"}'
    
    local response=$(curl -s --max-time 30 \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$BACKEND_URL/api/analyze")
    
    if echo "$response" | grep -q '"stack_age_result"' || echo "$response" | grep -q '"NoComponentsDetected"'; then
        # Either successful analysis or expected "no components" error is acceptable
        return 0
    else
        log_warning "GitHub analysis response: $response"
        return 1
    fi
}

# Test 7: Performance metrics
test_performance_metrics() {
    local response=$(curl -s --max-time 10 "$BACKEND_URL/api/performance/stats")
    
    if echo "$response" | grep -q '"performance"'; then
        return 0
    else
        return 1
    fi
}

# Test 8: External services status
test_external_services() {
    local response=$(curl -s --max-time 10 "$BACKEND_URL/api/external-services/status")
    
    if echo "$response" | grep -q '"external_services"'; then
        return 0
    else
        return 1
    fi
}

# Test 9: Rate limiting
test_rate_limiting() {
    # Make multiple rapid requests to test rate limiting
    local success_count=0
    local rate_limited=false
    
    for i in {1..5}; do
        local status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BACKEND_URL/health")
        if [ "$status_code" = "200" ]; then
            ((success_count++))
        elif [ "$status_code" = "429" ]; then
            rate_limited=true
        fi
    done
    
    # Should have some successful requests
    if [ $success_count -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Test 10: Frontend routing
test_frontend_routing() {
    # Test that frontend serves the React app
    local response=$(curl -s --max-time 10 "$FRONTEND_URL")
    
    if echo "$response" | grep -q "StackDebt" || echo "$response" | grep -q "react"; then
        return 0
    else
        return 1
    fi
}

# Test 11: API documentation
test_api_documentation() {
    local response=$(curl -s --max-time 10 "$BACKEND_URL/docs")
    
    if echo "$response" | grep -q "swagger" || echo "$response" | grep -q "OpenAPI"; then
        return 0
    else
        return 1
    fi
}

# Test 12: Error handling
test_error_handling() {
    local payload='{"url":"invalid-url","analysis_type":"website"}'
    
    local response=$(curl -s --max-time 10 \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$BACKEND_URL/api/analyze")
    
    if echo "$response" | grep -q '"error"' || echo "$response" | grep -q '"detail"'; then
        return 0
    else
        return 1
    fi
}

# Main test execution
main() {
    echo "🧪 StackDebt Integration Test Suite"
    echo "=================================="
    echo ""
    
    # Wait for services to be ready
    if ! wait_for_service "Backend" "$BACKEND_URL/health" 60; then
        log_failure "Backend service not ready, aborting tests"
        exit 1
    fi
    
    if ! wait_for_service "Frontend" "$FRONTEND_URL" 30; then
        log_failure "Frontend service not ready, aborting tests"
        exit 1
    fi
    
    echo ""
    log_info "Starting integration tests..."
    echo ""
    
    # Run all tests
    run_test "Service Health Check" test_service_health
    run_test "Backend Readiness" test_backend_readiness
    run_test "Database Connectivity" test_database_connectivity
    run_test "Cache Functionality" test_cache_functionality
    run_test "Website Analysis" test_website_analysis
    run_test "GitHub Analysis" test_github_analysis
    run_test "Performance Metrics" test_performance_metrics
    run_test "External Services Status" test_external_services
    run_test "Rate Limiting" test_rate_limiting
    run_test "Frontend Routing" test_frontend_routing
    run_test "API Documentation" test_api_documentation
    run_test "Error Handling" test_error_handling
    
    # Test results summary
    echo ""
    echo "📊 Test Results Summary"
    echo "======================"
    echo "Total Tests: $TESTS_TOTAL"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "🎉 All integration tests passed!"
        echo ""
        echo "✅ StackDebt deployment is working correctly"
        echo "   Frontend: $FRONTEND_URL"
        echo "   Backend:  $BACKEND_URL"
        echo "   API Docs: $BACKEND_URL/docs"
        exit 0
    else
        log_failure "❌ Some integration tests failed"
        echo ""
        echo "🔍 Troubleshooting steps:"
        echo "   1. Check service logs: make logs-prod"
        echo "   2. Check service health: make health-prod"
        echo "   3. Monitor services: make monitor-prod"
        echo "   4. Review deployment: ./scripts/deploy.sh health"
        exit 1
    fi
}

# Handle script arguments
case "${1:-run}" in
    "run")
        main
        ;;
    "quick")
        log_info "Running quick health check..."
        if test_service_health && test_backend_readiness; then
            log_success "Quick health check passed"
            exit 0
        else
            log_failure "Quick health check failed"
            exit 1
        fi
        ;;
    "analysis")
        log_info "Testing analysis functionality..."
        if test_website_analysis && test_github_analysis; then
            log_success "Analysis tests passed"
            exit 0
        else
            log_failure "Analysis tests failed"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {run|quick|analysis}"
        echo ""
        echo "Commands:"
        echo "  run       - Run complete integration test suite (default)"
        echo "  quick     - Run quick health check only"
        echo "  analysis  - Test analysis functionality only"
        exit 1
        ;;
esac