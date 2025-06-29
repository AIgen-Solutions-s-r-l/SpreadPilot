#!/bin/bash
# test-services.sh - Test all service health endpoints

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Testing all service health endpoints..."

# Function to test HTTP endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Testing $name ($url)... "
    
    response=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} OK (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗${NC} Failed (HTTP $response)"
        return 1
    fi
}

# Function to test Redis
test_redis() {
    echo -n "Testing Redis... "
    if docker exec spreadpilot-redis redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} OK"
        return 0
    else
        echo -e "${RED}✗${NC} Failed"
        return 1
    fi
}

# Function to test MongoDB
test_mongodb() {
    echo -n "Testing MongoDB... "
    if docker exec spreadpilot-mongodb mongosh --quiet --eval "db.runCommand('ping').ok" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} OK"
        return 0
    else
        echo -e "${RED}✗${NC} Failed"
        return 1
    fi
}

# Function to test Vault
test_vault() {
    echo -n "Testing Vault... "
    if curl -sf http://localhost:8201/v1/sys/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} OK"
        return 0
    else
        echo -e "${RED}✗${NC} Failed"
        return 1
    fi
}

# Track failures
FAILED_TESTS=0

# Test all services
test_endpoint "Trading Bot" "http://localhost:8001/health" || ((FAILED_TESTS++))
test_endpoint "Admin API" "http://localhost:8083/health" || ((FAILED_TESTS++))
test_endpoint "Alert Router" "http://localhost:8006/health" || ((FAILED_TESTS++))
test_endpoint "Frontend" "http://localhost:8080" || ((FAILED_TESTS++))

# Test infrastructure services
test_redis || ((FAILED_TESTS++))
test_mongodb || ((FAILED_TESTS++))
test_vault || ((FAILED_TESTS++))

echo ""

# Summary
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All tests passed! 🎉${NC}"
    
    # Test alert flow
    echo -e "\n${YELLOW}Testing alert flow...${NC}"
    
    # Publish test alert
    docker exec spreadpilot-redis redis-cli XADD alerts '*' data '{
        "follower_id": "test_system",
        "reason": "SYSTEM_TEST: All services are healthy and communicating",
        "severity": "INFO",
        "service": "test-suite",
        "timestamp": '$(date +%s)'
    }' >/dev/null
    
    echo -e "${GREEN}✓${NC} Test alert published to Redis stream"
    
    # Check if alert appears in Redis
    sleep 2
    alert_count=$(docker exec spreadpilot-redis redis-cli XLEN alerts 2>/dev/null || echo "0")
    echo -e "${GREEN}✓${NC} Redis alerts stream has $alert_count messages"
    
    exit 0
else
    echo -e "${RED}$FAILED_TESTS test(s) failed! ❌${NC}"
    exit 1
fi