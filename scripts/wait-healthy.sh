#!/bin/bash
# wait-healthy.sh - Wait for all services to be healthy

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Maximum wait time in seconds
MAX_WAIT=60
WAIT_INTERVAL=2

# Services to check with their health endpoints
declare -A SERVICES=(
    ["trading-bot"]="http://localhost:8001/health"
    ["admin-api"]="http://localhost:8083/health"
    ["alert-router"]="http://localhost:8006/health"
    ["frontend"]="http://localhost:8080"
    ["mongodb"]="mongo"
    ["redis"]="redis"
    ["vault"]="vault"
)

echo "Waiting for services to be healthy..."

# Function to check if a service is healthy
check_service() {
    local service=$1
    local endpoint=$2
    
    case $service in
        "mongodb")
            # Check MongoDB
            docker exec spreadpilot-mongodb mongosh --quiet --eval "db.runCommand('ping').ok" >/dev/null 2>&1
            return $?
            ;;
        "redis")
            # Check Redis
            docker exec spreadpilot-redis redis-cli ping >/dev/null 2>&1
            return $?
            ;;
        "vault")
            # Check Vault
            curl -sf http://localhost:8201/v1/sys/health >/dev/null 2>&1
            return $?
            ;;
        *)
            # HTTP health check
            curl -sf "$endpoint" >/dev/null 2>&1
            return $?
            ;;
    esac
}

# Check each service
for service in "${!SERVICES[@]}"; do
    endpoint="${SERVICES[$service]}"
    elapsed=0
    
    echo -n "Checking $service..."
    
    while [ $elapsed -lt $MAX_WAIT ]; do
        if check_service "$service" "$endpoint"; then
            echo -e " ${GREEN}✓${NC} Healthy"
            break
        fi
        
        if [ $elapsed -eq 0 ]; then
            echo -n " waiting"
        else
            echo -n "."
        fi
        
        sleep $WAIT_INTERVAL
        elapsed=$((elapsed + WAIT_INTERVAL))
    done
    
    if [ $elapsed -ge $MAX_WAIT ]; then
        echo -e " ${RED}✗${NC} Failed (timeout after ${MAX_WAIT}s)"
        exit 1
    fi
done

echo -e "\n${GREEN}All services are healthy!${NC}"

# Run a simple test to verify alert routing works
echo -e "\n${YELLOW}Testing alert routing...${NC}"

# Publish a test alert to Redis
docker exec spreadpilot-redis redis-cli XADD alerts '*' data '{
    "follower_id": "test",
    "reason": "TEST_ALERT: System health check completed",
    "severity": "INFO",
    "service": "wait-healthy",
    "timestamp": '$(date +%s)'
}' >/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Alert published successfully"
else
    echo -e "${RED}✗${NC} Failed to publish test alert"
fi

echo -e "\n${GREEN}System is ready!${NC}"