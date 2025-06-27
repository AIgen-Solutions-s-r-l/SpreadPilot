# SpreadPilot Infrastructure

This directory contains the Docker Compose infrastructure setup for the SpreadPilot trading platform development environment.

## 🏗️ Architecture Overview

The infrastructure consists of the following services:

- **PostgreSQL 16** - Primary database for application data
- **HashiCorp Vault 1.17** - Secret management in development mode
- **MinIO** - S3-compatible object storage for reports and files
- **Traefik v3** - Reverse proxy with HTTPS and Let's Encrypt support

## 🚀 Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- `openssl` command (for secret generation)
- Minimum 2GB RAM available for containers

### 1. Initial Setup

```bash
# Clone the repository and navigate to infrastructure
cd infra/

# Copy environment template (optional - script will use defaults)
cp .env.template .env

# Edit .env file with your specific values (optional)
nano .env
```

### 2. Start Infrastructure

```bash
# Start all services and initialize secrets
./compose-up.sh
```

This script will:
- Start all Docker Compose services
- Wait for services to be healthy
- Initialize Vault with required secrets
- Create MinIO buckets
- Export environment variables

### 3. Verify Installation

```bash
# Check service status
docker-compose ps

# Check service logs
docker-compose logs [service-name]

# Source environment variables
source .env.infra
```

## 📋 Service Information

### PostgreSQL Database
- **Host**: localhost:5432
- **Database**: spreadpilot
- **Username**: spreadpilot
- **Password**: Set via `POSTGRES_PASSWORD` environment variable

```bash
# Connect to database
psql -h localhost -U spreadpilot -d spreadpilot
```

### HashiCorp Vault
- **URL**: http://localhost:8200
- **Root Token**: `dev-only-token` (configurable via `VAULT_ROOT_TOKEN`)
- **Mode**: Development (data not persisted across restarts)

```bash
# Set environment variables
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="dev-only-token"

# List all secrets
vault kv list secret/

# Read specific secret
vault kv get secret/ibkr/credentials
```

### MinIO Object Storage
- **API Endpoint**: http://localhost:9000
- **Console**: http://localhost:9001
- **Root User**: `admin` (configurable via `MINIO_ROOT_USER`)
- **Root Password**: Set via `MINIO_ROOT_PASSWORD`
- **Default Bucket**: `reports`

### Traefik Reverse Proxy
- **HTTP**: Port 80 (redirects to HTTPS)
- **HTTPS**: Port 443
- **Dashboard**: Disabled for security
- **Let's Encrypt**: Staging environment (for development)

## 🔐 Secret Management

The infrastructure automatically initializes the following secrets in Vault:

| Secret Path | Description | Environment Variable |
|-------------|-------------|---------------------|
| `secret/ibkr/credentials` | Interactive Brokers credentials | `IB_USER`, `IB_PASS` |
| `secret/smtp/config` | SMTP configuration for emails | `SMTP_URI` |
| `secret/telegram/bot` | Telegram bot token | `TELEGRAM_TOKEN` |
| `secret/minio/credentials` | MinIO access credentials | `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` |
| `secret/database/postgres` | Database password | `DB_PASSWORD` |
| `secret/app/jwt` | JWT signing secret | `JWT_SECRET` |
| `secret/app/api` | API key for authentication | `API_KEY` |

### Working with Secrets

```bash
# Read a secret
vault kv get secret/ibkr/credentials

# Update a secret
vault kv put secret/ibkr/credentials username=new_user password=new_pass

# Delete a secret
vault kv delete secret/ibkr/credentials

# List all secret paths
vault kv list secret/
```

## 🛠️ Management Commands

### Start Infrastructure
```bash
./compose-up.sh
```

### Stop Infrastructure
```bash
# Stop services only
./compose-down.sh

# Stop and remove volumes (WARNING: deletes all data)
./compose-down.sh --volumes

# Stop and remove images
./compose-down.sh --images

# Stop and remove everything
./compose-down.sh --all
```

### Service Operations
```bash
# View service status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Restart a specific service
docker-compose restart [service-name]

# Scale a service (if applicable)
docker-compose up -d --scale [service-name]=2

# Execute commands in containers
docker-compose exec postgres psql -U spreadpilot -d spreadpilot
docker-compose exec vault vault status
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file to customize the infrastructure:

```bash
# PostgreSQL
POSTGRES_PASSWORD=your-secure-password

# Vault
VAULT_ROOT_TOKEN=your-vault-token

# MinIO
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=your-minio-password

# Traefik Let's Encrypt
ACME_EMAIL=your-email@example.com

# Application secrets
IB_USER=your-ib-username
IB_PASS=your-ib-password
SMTP_URI=smtp://user:pass@smtp.example.com:587
TELEGRAM_TOKEN=your-telegram-bot-token
```

### Custom Domains

To use custom domains with Traefik, update your `/etc/hosts` file:

```bash
127.0.0.1 vault.local
127.0.0.1 minio.local
127.0.0.1 minio-api.local
```

### Persistent Data

Data is stored in the following directories:

```
infra/data/
├── postgres/     # PostgreSQL data
├── minio/        # MinIO object storage
└── letsencrypt/  # SSL certificates
```

**⚠️ Important**: The `data/` directory is ignored by git. Make sure to backup important data before running cleanup commands.

## 🚨 Troubleshooting

### Common Issues

#### Services not starting
```bash
# Check Docker daemon
docker info

# Check available resources
docker system df

# View detailed logs
docker-compose logs --tail=50 [service-name]
```

#### Vault not accessible
```bash
# Check Vault status
docker-compose exec vault vault status

# Restart Vault
docker-compose restart vault

# Check Vault logs
docker-compose logs vault
```

#### Port conflicts
```bash
# Check what's using a port
lsof -i :5432  # PostgreSQL
lsof -i :8200  # Vault
lsof -i :9000  # MinIO

# Modify ports in docker-compose.yml if needed
```

#### Permission issues
```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/

# For Let's Encrypt
chmod 600 data/letsencrypt/acme.json
```

### Reset Everything

To completely reset the infrastructure:

```bash
# Stop and remove everything
./compose-down.sh --all

# Remove data directories
sudo rm -rf data/

# Start fresh
./compose-up.sh
```

## 🧪 Development Tips

### Database Access
```bash
# Direct PostgreSQL connection
docker-compose exec postgres psql -U spreadpilot -d spreadpilot

# Using pgAdmin (add to docker-compose.yml if needed)
# Access via web interface at http://localhost:5050
```

### Vault Development
```bash
# Enable Vault UI (modify docker-compose.yml)
# Add: VAULT_UI=true to vault environment

# Use Vault CLI
docker-compose exec vault vault auth -method=userpass
```

### MinIO Development
```bash
# MinIO client commands
docker-compose exec minio-init mc ls minio/

# Upload test files
docker-compose exec minio-init mc cp /tmp/testfile minio/reports/
```

### Monitoring
```bash
# Resource usage
docker stats

# Service health
docker-compose ps
docker-compose top

# Network inspection
docker network inspect spreadpilot
```

## 📚 Production Considerations

This infrastructure setup is designed for **development only**. For production deployment:

1. **Security**:
   - Use proper Vault seal configuration
   - Enable TLS for all services
   - Use strong, unique passwords
   - Disable Vault development mode

2. **Persistence**:
   - Configure Vault with proper storage backend
   - Set up database backups
   - Use external volumes for critical data

3. **High Availability**:
   - Deploy multiple instances
   - Use external load balancers
   - Configure health checks and monitoring

4. **Networking**:
   - Use proper domain names
   - Configure firewall rules
   - Set up VPN access

## 🤝 Integration with SpreadPilot

The infrastructure provides the following endpoints for SpreadPilot services:

- **Database**: `postgresql://spreadpilot:password@localhost:5432/spreadpilot`
- **Vault**: `http://localhost:8200` (token in `.env.infra`)
- **Object Storage**: `http://localhost:9000` (credentials in Vault)
- **Reverse Proxy**: Automatic HTTPS termination for web services

### Environment Integration

```bash
# Source infrastructure environment
source infra/.env.infra

# Start SpreadPilot services
cd ..
docker-compose -f docker-compose.yml up -d
```

## 📝 License

This infrastructure configuration is part of the SpreadPilot project.