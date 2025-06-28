#!/bin/bash

# Start SpreadPilot with Traefik reverse proxy
# This script sets up the web network and runs services with Traefik

set -e

echo "🚀 Starting SpreadPilot with Traefik..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.traefik to .env and configure your settings."
    exit 1
fi

# Check if DOMAIN is set
if ! grep -q "DOMAIN=" .env; then
    echo "❌ Error: DOMAIN not set in .env file!"
    echo "Please set DOMAIN=yourdomain.com in your .env file."
    exit 1
fi

# Create external web network if it doesn't exist
if ! docker network ls | grep -q " web "; then
    echo "📡 Creating external web network..."
    docker network create web
else
    echo "✅ Web network already exists"
fi

# Create letsencrypt directory if it doesn't exist
if [ ! -d "./letsencrypt" ]; then
    echo "📁 Creating letsencrypt directory..."
    mkdir -p ./letsencrypt
fi

# Start services with both compose files
echo "🐳 Starting services..."
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml ps

# Show access URLs
DOMAIN=$(grep "DOMAIN=" .env | cut -d'=' -f2)
echo ""
echo "✅ SpreadPilot is running with Traefik!"
echo ""
echo "🌐 Access URLs:"
echo "  - Admin API: https://dashboard.${DOMAIN}"
echo "  - Admin Dashboard: https://app.${DOMAIN}"
echo "  - Traefik Dashboard: https://traefik.${DOMAIN}"
echo ""
echo "📋 View logs:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.traefik.yml logs -f"
echo ""
echo "🛑 Stop services:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.traefik.yml down"