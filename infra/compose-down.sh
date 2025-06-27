#!/bin/bash

# SpreadPilot Infrastructure Shutdown Script
# This script stops and optionally removes the Docker Compose infrastructure

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

echo -e "${BLUE}🛑 Stopping SpreadPilot Infrastructure...${NC}"

# Parse command line arguments
REMOVE_VOLUMES=false
REMOVE_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --volumes|-v)
            REMOVE_VOLUMES=true
            shift
            ;;
        --images|-i)
            REMOVE_IMAGES=true
            shift
            ;;
        --all|-a)
            REMOVE_VOLUMES=true
            REMOVE_IMAGES=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "  --volumes, -v    Remove volumes (WARNING: This will delete all data)"
            echo "  --images, -i     Remove downloaded images"
            echo "  --all, -a        Remove both volumes and images"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                # Stop services only"
            echo "  $0 --volumes      # Stop services and remove volumes"
            echo "  $0 --all          # Stop services, remove volumes and images"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Stop services
echo -e "${YELLOW}📦 Stopping Docker Compose services...${NC}"
docker-compose down

if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "${RED}⚠️  WARNING: Removing volumes will delete all data!${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🗑️  Removing volumes...${NC}"
        docker-compose down --volumes
        
        # Also remove local data directories
        if [ -d "data" ]; then
            echo -e "${YELLOW}🗑️  Removing local data directories...${NC}"
            sudo rm -rf data/postgres/* data/minio/* data/letsencrypt/* 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ Volumes removed${NC}"
    else
        echo -e "${BLUE}ℹ️  Volume removal cancelled${NC}"
    fi
fi

if [ "$REMOVE_IMAGES" = true ]; then
    echo -e "${YELLOW}🗑️  Removing Docker images...${NC}"
    
    # List of images used in docker-compose.yml
    IMAGES=(
        "postgres:16-alpine"
        "vault:1.17"
        "minio/minio:latest"
        "minio/mc:latest"
        "traefik:v3.0"
    )
    
    for image in "${IMAGES[@]}"; do
        if docker image inspect "$image" >/dev/null 2>&1; then
            echo -e "${YELLOW}   Removing $image...${NC}"
            docker rmi "$image" 2>/dev/null || echo -e "${YELLOW}   ⚠️  Could not remove $image (may be in use)${NC}"
        fi
    done
    
    echo -e "${GREEN}✅ Images cleanup completed${NC}"
fi

# Remove network if it exists and is not in use
if docker network inspect spreadpilot >/dev/null 2>&1; then
    echo -e "${YELLOW}🌐 Removing Docker network...${NC}"
    docker network rm spreadpilot 2>/dev/null || echo -e "${YELLOW}   ⚠️  Network may still be in use${NC}"
fi

# Clean up environment file
if [ -f ".env.infra" ]; then
    echo -e "${YELLOW}🧹 Removing environment file...${NC}"
    rm -f .env.infra
fi

echo -e "${GREEN}🎉 Infrastructure shutdown completed!${NC}"

# Show cleanup summary
echo ""
echo -e "${BLUE}📋 Cleanup Summary:${NC}"
echo -e "${GREEN}   ✅ Services stopped${NC}"

if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "${GREEN}   ✅ Volumes removed${NC}"
else
    echo -e "${YELLOW}   ⏸️  Volumes preserved (use --volumes to remove)${NC}"
fi

if [ "$REMOVE_IMAGES" = true ]; then
    echo -e "${GREEN}   ✅ Images removed${NC}"
else
    echo -e "${YELLOW}   ⏸️  Images preserved (use --images to remove)${NC}"
fi

echo ""
echo -e "${BLUE}💡 Next Steps:${NC}"
echo -e "${YELLOW}   To restart: ./compose-up.sh${NC}"
echo -e "${YELLOW}   To check status: docker-compose ps${NC}"

if [ "$REMOVE_VOLUMES" = false ]; then
    echo -e "${YELLOW}   Your data is preserved in ./data/${NC}"
fi