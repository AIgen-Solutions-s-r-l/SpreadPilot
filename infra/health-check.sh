#!/bin/bash

# SpreadPilot Infrastructure Health Check Script
# This script checks the health status of all infrastructure services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}🔍 SpreadPilot Infrastructure Health Check${NC}"
echo ""

# Function to check service health
check_service_health() {
    local service_name="$1"
    local container_name="$2"
    local port="$3"
    local endpoint="$4"
    
    echo -n -e "${BLUE}   $service_name:${NC} "
    
    # Check if container is running
    if ! docker ps --format "table {{.Names}}" | grep -q "^$container_name$"; then
        echo -e "${RED}❌ Container not running${NC}"
        return 1
    fi
    
    # Check container health status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")
    
    case "$health_status" in
        "healthy")
            echo -e "${GREEN}✅ Healthy${NC}"
            return 0
            ;;
        "unhealthy")
            echo -e "${RED}❌ Unhealthy${NC}"
            return 1
            ;;
        "starting")
            echo -e "${YELLOW}⏳ Starting${NC}"
            return 1
            ;;
        *)
            # For services without health check, test port connectivity
            if [ -n "$port" ]; then
                if nc -z localhost "$port" 2>/dev/null; then
                    echo -e "${GREEN}✅ Running (port $port open)${NC}"
                    return 0
                else
                    echo -e "${RED}❌ Port $port not accessible${NC}"
                    return 1
                fi
            else
                echo -e "${YELLOW}⚠️  Status unknown${NC}"
                return 1
            fi
            ;;
    esac
}

# Function to check endpoint
check_endpoint() {
    local name="$1"
    local url="$2"
    
    echo -n -e "${BLUE}   $name:${NC} "
    
    if curl -s -f "$url" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Accessible${NC}"
        return 0
    else
        echo -e "${RED}❌ Not accessible${NC}"
        return 1
    fi
}

# Check if docker-compose is running
echo -e "${BLUE}📦 Docker Compose Status:${NC}"
if docker-compose ps >/dev/null 2>&1; then
    docker-compose ps
else
    echo -e "${RED}❌ Docker Compose not running or not in correct directory${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🏥 Service Health:${NC}"

# Track overall health
overall_healthy=true

# Check each service
check_service_health "PostgreSQL" "spreadpilot-postgres" "5432" || overall_healthy=false
check_service_health "Vault" "spreadpilot-vault" "8200" || overall_healthy=false
check_service_health "MinIO" "spreadpilot-minio" "9000" || overall_healthy=false
check_service_health "Traefik" "spreadpilot-traefik" "80" || overall_healthy=false

echo ""
echo -e "${BLUE}🌐 Endpoint Accessibility:${NC}"

# Check endpoints
check_endpoint "Vault API" "http://localhost:8200/v1/sys/health" || overall_healthy=false
check_endpoint "MinIO API" "http://localhost:9000/minio/health/live" || overall_healthy=false
check_endpoint "MinIO Console" "http://localhost:9001/minio/health/live" || overall_healthy=false

echo ""
echo -e "${BLUE}💾 Storage Status:${NC}"

# Check data directories
echo -n -e "${BLUE}   PostgreSQL Data:${NC} "
if [ -d "data/postgres" ] && [ "$(ls -A data/postgres 2>/dev/null)" ]; then
    echo -e "${GREEN}✅ Data present${NC}"
else
    echo -e "${YELLOW}⚠️  No data found${NC}"
fi

echo -n -e "${BLUE}   MinIO Data:${NC} "
if [ -d "data/minio" ] && [ "$(ls -A data/minio 2>/dev/null)" ]; then
    echo -e "${GREEN}✅ Data present${NC}"
else
    echo -e "${YELLOW}⚠️  No data found${NC}"
fi

# Check environment file
echo ""
echo -e "${BLUE}🔧 Configuration:${NC}"

echo -n -e "${BLUE}   Environment File:${NC} "
if [ -f ".env.infra" ]; then
    echo -e "${GREEN}✅ Present${NC}"
else
    echo -e "${YELLOW}⚠️  Missing (run ./compose-up.sh)${NC}"
fi

# Check Vault secrets (if vault is accessible)
if docker exec spreadpilot-vault vault status >/dev/null 2>&1; then
    echo -n -e "${BLUE}   Vault Secrets:${NC} "
    
    secret_count=$(docker exec -e VAULT_TOKEN=dev-only-token spreadpilot-vault vault kv list -format=json secret/ 2>/dev/null | jq '. | length' 2>/dev/null || echo "0")
    
    if [ "$secret_count" -gt 0 ]; then
        echo -e "${GREEN}✅ $secret_count secrets configured${NC}"
    else
        echo -e "${YELLOW}⚠️  No secrets found${NC}"
    fi
fi

echo ""
echo -e "${BLUE}📊 Resource Usage:${NC}"

# Show Docker stats for our containers
if command -v docker >/dev/null 2>&1; then
    echo -e "${YELLOW}   Container Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep "spreadpilot-" || echo "   No containers found"
fi

# Overall status
echo ""
if [ "$overall_healthy" = true ]; then
    echo -e "${GREEN}🎉 Infrastructure is healthy!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some services have issues. Check logs with: docker-compose logs [service-name]${NC}"
    echo ""
    echo -e "${BLUE}💡 Useful commands:${NC}"
    echo -e "${YELLOW}   View logs: docker-compose logs [service-name]${NC}"
    echo -e "${YELLOW}   Restart service: docker-compose restart [service-name]${NC}"
    echo -e "${YELLOW}   Full restart: ./compose-down.sh && ./compose-up.sh${NC}"
    exit 1
fi