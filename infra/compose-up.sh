#!/bin/bash

# SpreadPilot Infrastructure Bootstrap Script
# This script starts the Docker Compose infrastructure and initializes Vault secrets

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

# Default values
VAULT_ROOT_TOKEN="${VAULT_ROOT_TOKEN:-dev-only-token}"
VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

# Export Vault environment variables
export VAULT_ADDR="$VAULT_ADDR"
export VAULT_TOKEN="$VAULT_ROOT_TOKEN"

echo -e "${BLUE}🚀 Starting SpreadPilot Infrastructure...${NC}"

# Create data directories if they don't exist
mkdir -p data/postgres data/minio data/letsencrypt

# Set proper permissions for Let's Encrypt
chmod 600 data/letsencrypt || true

# Start Docker Compose services
echo -e "${YELLOW}📦 Starting Docker Compose services...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"

# Function to wait for service health
wait_for_service() {
    local service_name="$1"
    local max_attempts="${2:-30}"
    local attempt=1
    
    echo -e "${BLUE}   Waiting for $service_name...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps "$service_name" | grep -q "healthy\|Up"; then
            echo -e "${GREEN}   ✅ $service_name is ready${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}   ⏳ Attempt $attempt/$max_attempts - waiting for $service_name...${NC}"
        sleep 5
        ((attempt++))
    done
    
    echo -e "${RED}   ❌ $service_name failed to become healthy${NC}"
    return 1
}

# Wait for core services
wait_for_service "postgres" 20
wait_for_service "vault" 20
wait_for_service "minio" 20

# Wait a bit more for Vault to be fully ready
echo -e "${YELLOW}⏳ Waiting for Vault to be fully initialized...${NC}"
sleep 10

# Function to check if Vault is accessible
check_vault() {
    docker exec spreadpilot-vault vault status > /dev/null 2>&1
}

# Wait for Vault to be accessible
echo -e "${BLUE}🔐 Checking Vault accessibility...${NC}"
for i in {1..30}; do
    if check_vault; then
        echo -e "${GREEN}✅ Vault is accessible${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Vault is not accessible after 30 attempts${NC}"
        echo -e "${YELLOW}💡 Try running: docker-compose logs vault${NC}"
        exit 1
    fi
    echo -e "${YELLOW}⏳ Attempt $i/30 - waiting for Vault...${NC}"
    sleep 2
done

# Initialize Vault secrets
echo -e "${BLUE}🔐 Initializing Vault secrets...${NC}"

# Function to set secret in Vault
set_vault_secret() {
    local secret_path="$1"
    local secret_data="$2"
    
    echo -e "${YELLOW}   Setting secret: $secret_path${NC}"
    
    if docker exec spreadpilot-vault vault kv put secret/"$secret_path" $secret_data; then
        echo -e "${GREEN}   ✅ Secret $secret_path set successfully${NC}"
    else
        echo -e "${RED}   ❌ Failed to set secret $secret_path${NC}"
        return 1
    fi
}

# Function to generate random password
generate_password() {
    openssl rand -base64 32 | tr -d "/+=" | cut -c1-25
}

# Initialize secrets with default or generated values
echo -e "${BLUE}📝 Setting up secrets...${NC}"

# Interactive Brokers credentials
IB_USER="${IB_USER:-demo_user}"
IB_PASS="${IB_PASS:-$(generate_password)}"
set_vault_secret "ibkr/credentials" "username=$IB_USER password=$IB_PASS"

# SMTP Configuration
SMTP_URI="${SMTP_URI:-smtp://user:password@smtp.example.com:587}"
set_vault_secret "smtp/config" "uri=$SMTP_URI"

# Telegram Bot Token
TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-$(generate_password):$(generate_password)}"
set_vault_secret "telegram/bot" "token=$TELEGRAM_TOKEN"

# MinIO Access Keys
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-$(generate_password)}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-$(generate_password)}"
set_vault_secret "minio/credentials" "access_key=$MINIO_ACCESS_KEY secret_key=$MINIO_SECRET_KEY"

# Additional application secrets
DB_PASSWORD="${DB_PASSWORD:-$(generate_password)}"
set_vault_secret "database/postgres" "password=$DB_PASSWORD"

JWT_SECRET="${JWT_SECRET:-$(generate_password)}"
set_vault_secret "app/jwt" "secret=$JWT_SECRET"

API_KEY="${API_KEY:-$(generate_password)}"
set_vault_secret "app/api" "key=$API_KEY"

echo -e "${GREEN}🎉 Infrastructure setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Service Information:${NC}"
echo -e "${YELLOW}   PostgreSQL:${NC} localhost:5432 (user: spreadpilot, db: spreadpilot)"
echo -e "${YELLOW}   Vault:${NC} $VAULT_ADDR (token: $VAULT_ROOT_TOKEN)"
echo -e "${YELLOW}   MinIO API:${NC} http://localhost:9000"
echo -e "${YELLOW}   MinIO Console:${NC} http://localhost:9001"
echo -e "${YELLOW}   Traefik:${NC} HTTP on port 80, HTTPS on port 443"
echo ""
echo -e "${BLUE}🔐 Vault Environment:${NC}"
echo -e "${YELLOW}   export VAULT_ADDR=\"$VAULT_ADDR\"${NC}"
echo -e "${YELLOW}   export VAULT_TOKEN=\"$VAULT_ROOT_TOKEN\"${NC}"
echo ""
echo -e "${BLUE}📖 Useful Commands:${NC}"
echo -e "${YELLOW}   Check services:${NC} docker-compose ps"
echo -e "${YELLOW}   View logs:${NC} docker-compose logs [service-name]"
echo -e "${YELLOW}   Stop services:${NC} docker-compose down"
echo -e "${YELLOW}   Read secrets:${NC} vault kv get secret/[secret-path]"
echo ""
echo -e "${GREEN}✨ Infrastructure is ready for SpreadPilot development!${NC}"

# Save environment variables to a file for easy sourcing
cat > .env.infra << EOF
# SpreadPilot Infrastructure Environment Variables
# Source this file: source .env.infra

export VAULT_ADDR="$VAULT_ADDR"
export VAULT_TOKEN="$VAULT_ROOT_TOKEN"

# Database
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="spreadpilot"
export POSTGRES_USER="spreadpilot"

# MinIO
export MINIO_ENDPOINT="localhost:9000"
export MINIO_CONSOLE="localhost:9001"

# Services Status Check
alias infra-status="docker-compose ps"
alias infra-logs="docker-compose logs"
alias infra-down="docker-compose down"
alias vault-ui="echo 'Vault UI: $VAULT_ADDR (token: $VAULT_TOKEN)'"
EOF

echo -e "${GREEN}💾 Environment variables saved to .env.infra${NC}"
echo -e "${YELLOW}   Run: source .env.infra${NC}"