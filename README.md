<div align="center">

# SpreadPilot

**Enterprise-Grade Automated Options Trading Platform**

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/AIgen-Solutions-s-r-l/SpreadPilot/releases)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![CI Pipeline](https://github.com/AIgen-Solutions-s-r-l/SpreadPilot/actions/workflows/ci.yml/badge.svg)](https://github.com/AIgen-Solutions-s-r-l/SpreadPilot/actions/workflows/ci.yml)
[![Security Scan](https://github.com/AIgen-Solutions-s-r-l/SpreadPilot/actions/workflows/ci-security.yml/badge.svg)](https://github.com/AIgen-Solutions-s-r-l/SpreadPilot/actions/workflows/ci-security.yml)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.7+-blue.svg)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Cloud](https://img.shields.io/badge/cloud-GCP-4285F4.svg)](https://cloud.google.com/)

**Sophisticated microservices-based copy-trading platform that automates QQQ options strategies from Google Sheets to Interactive Brokers accounts**

[Features](#-key-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Architecture](#-architecture) • [Security](#-security) • [Support](#-support)

---

### 🏢 Developed by AIgen Solutions S.r.l.

**Professional Trading Automation • Enterprise Security • Cloud-Native Architecture**

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Security](#-security)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Monitoring & Operations](#-monitoring--operations)
- [Development](#-development)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Release History](#-release-history)
- [Support & Licensing](#-support--licensing)

---

## 🎯 Overview

**SpreadPilot** is an institutional-grade, cloud-native trading automation platform designed for professional options traders and fund managers. Built with modern microservices architecture, it provides automated execution, real-time P&L tracking, comprehensive risk management, and enterprise-level security.

### 🎪 What SpreadPilot Does

SpreadPilot bridges the gap between strategy development and execution by:

1. **📊 Reading Strategy Signals** from Google Sheets in real-time
2. **🤖 Executing Trades Automatically** across multiple Interactive Brokers accounts
3. **💰 Tracking P&L in Real-Time** with 30-second mark-to-market calculations
4. **🛡️ Managing Risk Dynamically** with automated position monitoring and liquidation
5. **📈 Generating Professional Reports** with PDF/Excel exports and automated distribution
6. **🔔 Alerting Stakeholders** via Telegram and email for critical events

### 🏆 Why SpreadPilot?

- **✅ Production-Ready**: Used in live trading with real capital
- **⚡ High Performance**: Sub-second order execution with intelligent retry mechanisms
- **🔒 Enterprise Security**: OAuth2 authentication, HashiCorp Vault integration, encrypted communications
- **📊 Real-Time Insights**: Live dashboards, WebSocket updates, comprehensive metrics
- **☁️ Cloud-Native**: Containerized microservices, horizontal scaling, multi-region deployment
- **🧪 Fully Tested**: 90%+ code coverage, E2E integration tests, automated CI/CD

---

## ✨ Key Features

### 🤖 Automated Trading Engine

- **Smart Order Execution**: Advanced limit-ladder algorithm with dynamic pricing
- **Pre-Trade Validation**: Margin checks, position limits, strategy compliance
- **Multi-Follower Support**: Replicate strategies across unlimited accounts simultaneously
- **Intelligent Retry Logic**: Automatic retry with exponential backoff for failed orders
- **Position Management**: Real-time position tracking, assignment handling, corporate action processing

### 💰 Real-Time P&L System

- **Sub-Minute Updates**: 30-second mark-to-market calculations
- **Multi-Timeframe Analytics**: Intraday, daily, monthly, and inception-to-date P&L
- **Automated Commissions**: Dynamic commission calculation on positive P&L with IBAN tracking
- **PostgreSQL Storage**: High-performance time-series data with efficient rollups
- **Performance Metrics**: Sharpe ratio, max drawdown, win rate, average trade P&L

### 🛡️ Advanced Risk Management

- **Time Value Monitoring**: Automatic liquidation when TV < $0.10 to prevent assignment
- **Position Limits**: Per-follower and per-strategy exposure limits
- **Margin Monitoring**: Real-time margin utilization tracking with alerts
- **Circuit Breakers**: Automatic trading suspension on abnormal market conditions
- **Emergency Controls**: One-click position closure from admin dashboard

### 📊 Professional Reporting

- **Automated Report Generation**: Daily, weekly, and monthly P&L reports
- **Multiple Formats**: PDF (presentation-ready) and Excel (data analysis)
- **Secure Distribution**: GCS storage with time-limited signed URLs
- **Email Delivery**: Automated distribution to stakeholders with SendGrid
- **Custom Branding**: White-label reports with company logo and styling

### 🎛️ Admin Dashboard

- **Real-Time Monitoring**: Live position updates via WebSocket
- **Follower Management**: Add, edit, enable/disable accounts
- **Service Health Monitoring**: RED/YELLOW/GREEN status indicators with auto-restart
- **Live Logs**: Real-time log streaming from all services
- **Manual Controls**: Emergency stop, position closure, strategy override
- **🔐 OAuth2 Authentication**: Secure login with JWT token management (NEW in v2.0.0)

### 🔔 Multi-Channel Alerting

- **Telegram Integration**: Instant notifications for critical events
- **Email Alerts**: HTML formatted emails with detailed trade information
- **Alert Routing**: Flexible routing based on severity and event type
- **Rate Limiting**: Prevent alert fatigue with intelligent throttling

### 🏗️ Enterprise Architecture

- **Microservices Design**: Loosely coupled, independently deployable services
- **Container-First**: Docker and Kubernetes ready for cloud deployment
- **Horizontal Scaling**: Scale individual services based on load
- **Observability**: OpenTelemetry, Prometheus metrics, Grafana dashboards
- **High Availability**: Redis for caching, PostgreSQL replication, MongoDB replica sets

### 🔒 Security & Compliance

- **OAuth2 + JWT**: Industry-standard authentication for admin dashboard
- **HashiCorp Vault**: Centralized secret management for credentials
- **Encrypted Communications**: TLS 1.3 for all external communications
- **Audit Logging**: Comprehensive audit trail for compliance
- **RBAC**: Role-based access control for multi-user environments
- **Container Security**: Non-root users, minimal base images, vulnerability scanning

---

## 🏗️ System Architecture

### 🎯 Microservices Overview

<div align="center">

```mermaid
graph TB
    subgraph "📊 Data Sources"
        A[Google Sheets<br/>Strategy Signals]
        B[Interactive Brokers<br/>Market Data]
    end

    subgraph "🎛️ SpreadPilot Platform"
        C[Signal Listener]
        D[Trading Bot]
        E[Admin API]
        F[Frontend Dashboard]
        G[Watchdog Service]
        H[Report Worker]
        I[Alert Router]
    end

    subgraph "🗄️ Data Layer"
        J[(PostgreSQL<br/>P&L Data)]
        K[(MongoDB<br/>Trading Data)]
        L[(Redis<br/>Pub/Sub)]
        M[HashiCorp Vault<br/>Secrets]
    end

    subgraph "☁️ Cloud Services"
        N[Google Cloud Storage<br/>Reports]
        O[SendGrid<br/>Email]
        P[Telegram<br/>Notifications]
    end

    A -->|Poll Signals| C
    C -->|Publish| L
    L -->|Subscribe| D
    D <-->|Execute Trades| B
    D -->|Write Positions| K
    D -->|Write P&L| J
    K -->|Read Data| E
    J -->|Read Data| E
    E <-->|REST API| F
    G -->|Monitor| D
    G -->|Monitor| E
    H -->|Generate Reports| J
    H -->|Upload| N
    I -->|Send Alerts| O
    I -->|Send Alerts| P
    M -->|Retrieve Secrets| D
    M -->|Retrieve Secrets| E
```

</div>

### 🧩 Service Components

| Service | Technology | Purpose | Port | Status |
|---------|-----------|---------|------|--------|
| **🤖 Trading Bot** | Python 3.9+, FastAPI | Trade execution, position management | 8001 | ✅ Production |
| **🎛️ Admin API** | Python 3.9+, FastAPI | REST API for dashboard, follower management | 8002 | ✅ Production |
| **🖥️ Frontend Dashboard** | React 19, TypeScript 5.7, Vite | Modern admin interface with OAuth2 auth | 8080 | ✅ Production |
| **👀 Watchdog** | Python 3.9+ | Autonomous service health monitoring & restart | - | ✅ Production |
| **📊 Report Worker** | Python 3.9+, ReportLab | PDF/Excel report generation | 8004 | ✅ Production |
| **🔔 Alert Router** | Python 3.9+, Redis Streams | Multi-channel notification delivery | 8005 | ✅ Production |

### 🗄️ Data Stores

| Store | Technology | Purpose | Backup Strategy |
|-------|-----------|---------|----------------|
| **PostgreSQL** | PostgreSQL 13+ | P&L data, time-series analytics | Daily automated backups to GCS |
| **MongoDB** | MongoDB 5+ | Trading data, follower configuration | Replica set with point-in-time recovery |
| **Redis** | Redis 7+ | Pub/Sub messaging, caching, alert streams | Persistence with AOF, daily snapshots |
| **Vault** | HashiCorp Vault | Encrypted secret storage | Automated Vault snapshots |
| **GCS** | Google Cloud Storage | Report files, backups | Multi-region with versioning |

### 🔄 Data Flow Architecture

**Signal Processing Flow:**
```
Google Sheets → Signal Listener → Redis Pub/Sub → Trading Bot → IB Gateway → Execution
                                                          ↓
                                                    MongoDB (Trades)
                                                          ↓
                                                    PostgreSQL (P&L)
```

**Reporting Flow:**
```
PostgreSQL P&L Data → Report Worker → PDF/Excel Generation → GCS Upload → Email Distribution
```

**Authentication Flow (NEW in v2.0.0):**
```
User → Login Page → OAuth2 Token Request → Admin API → JWT Token → Stored in LocalStorage
      ↓
All API Requests → Axios Interceptor → Add Bearer Token → Admin API → Verify JWT
```

---

## 🚀 Quick Start

### 📋 Prerequisites

Ensure you have the following installed and configured:

- ✅ **Docker** 20.10+ and **Docker Compose** 2.0+
- ✅ **Python** 3.9+ (for local development)
- ✅ **Node.js** 18+ and **npm** 9+ (for frontend)
- ✅ **Make** (optional, for convenience commands)
- ✅ **Interactive Brokers Account** with API access enabled
- ✅ **Google Cloud Platform Account** (for production deployment)
- ✅ **Google Sheets** with trading strategy
- ✅ **SendGrid API Key** (for email notifications)
- ✅ **Telegram Bot Token** (for Telegram notifications)

### ⚡ One-Command Setup

```bash
# 1️⃣ Clone the repository
git clone https://github.com/AIgen-Solutions-s-r-l/SpreadPilot.git
cd SpreadPilot

# 2️⃣ Start infrastructure services (PostgreSQL, MongoDB, Redis, Vault)
cd infra/
./compose-up.sh

# 3️⃣ Configure environment variables
cd ..
cp deploy/.env.dev.template .env
# Edit .env with your credentials (see Configuration section)

# 4️⃣ Build and start SpreadPilot services
docker-compose up --build -d

# 5️⃣ Verify all services are running
docker-compose ps
cd infra/ && ./health-check.sh
```

### 🎯 Access Points

Once deployed, access the platform at:

| Service | URL | Credentials |
|---------|-----|-------------|
| 🎛️ **Admin Dashboard** | http://localhost:8080 | Configure in .env |
| 📊 **Admin API** | http://localhost:8002/docs | JWT token required |
| 📈 **Grafana Monitoring** | http://localhost:3000 | admin / admin (default) |
| 🗄️ **PostgreSQL** | localhost:5432 | Configure in .env |
| 🍃 **MongoDB** | localhost:27017 | Configure in .env |
| 🔴 **Redis** | localhost:6379 | No authentication (dev) |
| 🔐 **Vault UI** | http://localhost:8200 | Root token in infra/.env |

### 🌐 Production Deployment with Traefik

For production deployment with HTTPS, automatic SSL, and domain routing:

```bash
# 1️⃣ Configure domain in environment
cp .env.traefik .env
nano .env  # Set DOMAIN=yourdomain.com

# 2️⃣ Deploy with Traefik reverse proxy
./scripts/start-with-traefik.sh

# 3️⃣ Verify deployment
curl https://dashboard.yourdomain.com/api/v1/health
```

**Production URLs:**
- 🔐 **Admin API**: https://dashboard.yourdomain.com
- 📱 **Admin Dashboard**: https://app.yourdomain.com
- 🎛️ **Traefik Dashboard**: https://traefik.yourdomain.com (basic auth required)

---

## ⚙️ Configuration

### 📝 Environment Variables

Create a `.env` file in the project root based on `deploy/.env.dev.template`:

```bash
# ==========================================
# 🏦 Interactive Brokers Configuration
# ==========================================
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password
IB_ACCOUNT=your_ib_account_id
IB_TRADING_MODE=paper  # or 'live' for production

# ==========================================
# 📊 Google Sheets Integration
# ==========================================
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_SHEET_RANGE='Strategy!A1:Z1000'

# ==========================================
# 🔐 Authentication (NEW in v2.0.0)
# ==========================================
ADMIN_USERNAME=admin
# Generate password hash: htpasswd -bnBC 12 "" your_password | tr -d ':\n'
ADMIN_PASSWORD_HASH=your_bcrypt_hashed_password
# Generate JWT secret: openssl rand -hex 32
JWT_SECRET=your_32_byte_hex_secret
JWT_EXPIRATION_MINUTES=1440  # 24 hours

# ==========================================
# 📧 Email Configuration
# ==========================================
SENDGRID_API_KEY=SG.your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME="SpreadPilot Alerts"
EMAIL_RECIPIENTS=trader1@example.com,trader2@example.com

# ==========================================
# 🤖 Telegram Configuration
# ==========================================
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id_or_group_id
TELEGRAM_ENABLED=true

# ==========================================
# 🗄️ Database Configuration
# ==========================================
# PostgreSQL (P&L Data)
POSTGRES_USER=spreadpilot
POSTGRES_PASSWORD=secure_postgres_password
POSTGRES_DB=spreadpilot_pnl
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_URI=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# MongoDB (Trading Data)
MONGO_USER=spreadpilot
MONGO_PASSWORD=secure_mongo_password
MONGO_DB=spreadpilot_admin
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_URI=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}?authSource=admin

# Redis (Pub/Sub & Caching)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=  # Leave empty for no auth (dev only)

# ==========================================
# 🔐 HashiCorp Vault (Optional)
# ==========================================
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-only-token-change-in-production
VAULT_ENABLED=true
VAULT_SECRET_PATH=secret/ibkr

# ==========================================
# ☁️ Google Cloud Storage
# ==========================================
GCS_BUCKET_NAME=spreadpilot-reports
GCS_SERVICE_ACCOUNT_KEY_PATH=/path/to/gcs-service-account-key.json
GCS_PRESIGNED_URL_EXPIRATION=86400  # 24 hours

# ==========================================
# 📊 Application Configuration
# ==========================================
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
ENVIRONMENT=development  # development, staging, production
TZ=America/New_York  # Trading timezone

# Trading Bot
TRADING_BOT_POLL_INTERVAL=10  # seconds
TRADING_BOT_MAX_RETRIES=3
TRADING_BOT_RETRY_DELAY=5  # seconds

# Report Worker
REPORT_SCHEDULE_DAILY=16:30  # ET
REPORT_SCHEDULE_MONTHLY=00:10  # ET on 1st of month

# Watchdog
WATCHDOG_CHECK_INTERVAL=60  # seconds
WATCHDOG_RESTART_THRESHOLD=3  # consecutive failures
```

### 🔐 HashiCorp Vault Integration

SpreadPilot supports HashiCorp Vault for enterprise-grade secret management:

```bash
# Initialize Vault (first time only)
cd infra/
./vault-init.sh

# Store secrets in Vault
vault kv put secret/ibkr/vertical_spreads_strategy \
  username="your_ib_username" \
  password="your_ib_password" \
  account="your_ib_account"

# Store follower credentials
vault kv put secret/ibkr/follower_123 \
  username="follower_username" \
  password="follower_password" \
  account="follower_account"

# Verify secrets
vault kv get secret/ibkr/vertical_spreads_strategy
```

**Vault Secret Paths:**
- `secret/ibkr/vertical_spreads_strategy` - Main strategy credentials
- `secret/ibkr/follower_{id}` - Follower-specific credentials
- `secret/sendgrid` - SendGrid API key
- `secret/telegram` - Telegram bot token
- `secret/gcs` - Google Cloud Storage service account key

---

## 🔒 Security

SpreadPilot implements defense-in-depth security with multiple layers of protection.

### 🛡️ Security Features

#### Authentication & Authorization (NEW in v2.0.0)

- **OAuth2 Password Flow**: RFC 6749 compliant authentication
- **JWT Tokens**: Stateless authentication with 24-hour expiration
- **bcrypt Password Hashing**: Secure credential storage with work factor 12
- **Bearer Token Authorization**: Industry-standard Authorization header
- **Automatic Session Cleanup**: 401 responses trigger immediate logout
- **Token Validation**: Verification on app initialization and all API requests

#### Infrastructure Security

- **Container Isolation**: All services run as non-root users
- **Network Segmentation**: Services communicate via private Docker networks
- **TLS Encryption**: All external communications encrypted with TLS 1.3
- **Secret Management**: HashiCorp Vault with encrypted storage at rest
- **Audit Logging**: Comprehensive logs for all sensitive operations
- **Vulnerability Scanning**: Automated Trivy scans in CI/CD pipeline

#### Application Security

- **Input Validation**: Pydantic models for all API inputs
- **SQL Injection Protection**: Parameterized queries with SQLAlchemy
- **XSS Prevention**: React's built-in XSS protection
- **CSRF Protection**: SameSite cookies and CORS restrictions
- **Rate Limiting**: Prevent brute-force attacks on authentication endpoints
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options

### 🔒 Compliance & Standards

- **OWASP Top 10**: Protection against all OWASP vulnerabilities
- **CIS Benchmarks**: Docker containers follow CIS Docker benchmark
- **GDPR Ready**: Data encryption, audit logs, right to deletion
- **SOC 2 Controls**: Logging, monitoring, access controls

### 🚨 Security Best Practices

```bash
# Generate secure credentials
./scripts/security-utils.py generate-credentials

# Run security audit
./scripts/security-utils.py audit

# Scan for vulnerabilities
./trivy_scan.sh

# Rotate secrets (Vault)
vault kv put secret/ibkr/vertical_spreads_strategy \
  username="new_username" \
  password="new_password" \
  account="account"

# Review security checklist before deployment
cat security_checklist.md
```

### 📋 Security Checklist

Before production deployment, ensure:

- ✅ All default passwords changed
- ✅ JWT_SECRET is cryptographically random (32+ bytes)
- ✅ ADMIN_PASSWORD_HASH uses bcrypt with work factor >= 12
- ✅ Vault is unsealed and backed up
- ✅ TLS certificates are valid and not self-signed
- ✅ Firewall rules restrict access to required ports only
- ✅ Container images scanned for vulnerabilities
- ✅ Audit logging enabled for all services
- ✅ Backups encrypted and stored securely
- ✅ Incident response plan documented

---

## 📚 API Documentation

### 🎛️ Admin API

**Base URL:** `/api/v1`
**Authentication:** Bearer token (JWT) required
**Content-Type:** `application/json`

#### Authentication Endpoints (NEW in v2.0.0)

```bash
# Login
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=your_password

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# Use token in subsequent requests
curl -H "Authorization: Bearer eyJhbGc..." https://api.yourdomain.com/api/v1/followers
```

#### Followers Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/followers` | List all followers | ✅ Yes |
| `GET` | `/followers/{id}` | Get follower details | ✅ Yes |
| `POST` | `/followers` | Register new follower | ✅ Yes |
| `PUT` | `/followers/{id}` | Update follower | ✅ Yes |
| `DELETE` | `/followers/{id}` | Delete follower | ✅ Yes |
| `POST` | `/followers/{id}/toggle` | Enable/disable follower | ✅ Yes |
| `POST` | `/followers/{id}/close` | Close all positions | ✅ Yes |

#### P&L Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/pnl/realtime` | Current P&L across all followers | ✅ Yes |
| `GET` | `/pnl/daily` | Daily P&L history | ✅ Yes |
| `GET` | `/pnl/monthly` | Monthly P&L summary | ✅ Yes |
| `GET` | `/pnl/follower/{id}` | P&L for specific follower | ✅ Yes |

#### Positions & Trades

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/positions` | Current positions all followers | ✅ Yes |
| `GET` | `/positions/{follower_id}` | Positions for specific follower | ✅ Yes |
| `GET` | `/trades` | Trade history | ✅ Yes |
| `GET` | `/trades/{id}` | Trade details | ✅ Yes |

#### System Operations

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/health` | System health check | ❌ No |
| `GET` | `/status` | Detailed system status | ✅ Yes |
| `POST` | `/emergency-stop` | Emergency stop all trading | ✅ Yes |
| `GET` | `/logs` | Real-time log stream (WebSocket) | ✅ Yes |

### 📊 Example Requests

**Register New Follower:**
```bash
curl -X POST https://api.yourdomain.com/api/v1/followers \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "iban": "DE89370400440532013000",
    "commission_pct": 20.0,
    "active": true,
    "credentials": {
      "username": "follower_ib_username",
      "password": "follower_ib_password",
      "account": "follower_ib_account"
    }
  }'
```

**Get Real-Time P&L:**
```bash
curl -X GET https://api.yourdomain.com/api/v1/pnl/realtime \
  -H "Authorization: Bearer your_jwt_token"

# Response
{
  "total_pnl": 15234.56,
  "total_unrealized": 1234.56,
  "total_realized": 14000.00,
  "followers": [
    {
      "id": "follower_123",
      "email": "trader@example.com",
      "pnl": 5234.56,
      "unrealized": 234.56,
      "realized": 5000.00,
      "positions": 3
    }
  ],
  "timestamp": "2025-11-11T10:30:00Z"
}
```

**Interactive API Documentation:**

Visit http://localhost:8002/docs for Swagger UI with interactive API testing.

---

## ☁️ Deployment

### 🚀 Google Cloud Platform

SpreadPilot is optimized for GCP with Cloud Run, Cloud Build, and Secret Manager.

#### Prerequisites

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth login

# Set project
gcloud config set project your-project-id

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com
```

#### Deploy to Cloud Run

```bash
# 1️⃣ Configure secrets in Secret Manager
gcloud secrets create ibkr-username --data-file=- <<< "your_username"
gcloud secrets create ibkr-password --data-file=- <<< "your_password"
gcloud secrets create jwt-secret --data-file=- <<< "$(openssl rand -hex 32)"
gcloud secrets create admin-password-hash --data-file=- <<< "$(htpasswd -bnBC 12 '' password | tr -d ':\n')"

# 2️⃣ Build and deploy via Cloud Build
gcloud builds submit --config cloudbuild.yaml

# 3️⃣ Monitor deployment
gcloud run services list --platform managed
gcloud run services describe admin-api --platform managed --region us-central1

# 4️⃣ Get service URLs
export ADMIN_API_URL=$(gcloud run services describe admin-api --platform managed --region us-central1 --format 'value(status.url)')
echo "Admin API: $ADMIN_API_URL"
```

#### Infrastructure as Code

```bash
# Deploy with Terraform
cd terraform/
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Deploy with Cloud Deployment Manager
gcloud deployment-manager deployments create spreadpilot \
  --config deployment.yaml
```

### 🐳 Docker Compose (Development/Staging)

```bash
# Development environment
docker-compose -f docker-compose.yml up -d

# Staging environment
docker-compose -f docker-compose.staging.yml up -d

# Production-like environment
docker-compose -f docker-compose.prod.yml up -d
```

### ☸️ Kubernetes

```bash
# Deploy to Kubernetes cluster
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/deployments/
kubectl apply -f kubernetes/services/
kubectl apply -f kubernetes/ingress.yaml

# Verify deployment
kubectl get pods -n spreadpilot
kubectl get services -n spreadpilot

# Access logs
kubectl logs -f deployment/trading-bot -n spreadpilot
```

### 📋 Deployment Checklist

Before production deployment:

- ✅ Secrets configured in Secret Manager/Vault
- ✅ Database backups automated and tested
- ✅ SSL certificates valid and auto-renewing
- ✅ Monitoring and alerting configured
- ✅ Runbooks documented for common issues
- ✅ Disaster recovery plan tested
- ✅ Performance load testing completed
- ✅ Security audit passed
- ✅ Stakeholders trained on dashboard
- ✅ Rollback plan documented and tested

---

## 📊 Monitoring & Operations

### 🎛️ Grafana Dashboards

Pre-built dashboards for comprehensive system monitoring:

1. **Trading Overview**: Order flow, execution rates, position exposure
2. **P&L Analytics**: Real-time P&L, daily/monthly trends, per-follower breakdown
3. **System Health**: Service uptime, resource utilization, error rates
4. **Performance Metrics**: API latency, database query performance, cache hit rates

Access Grafana at http://localhost:3000 (default credentials: admin/admin)

### 📈 Key Performance Indicators

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Order Execution Time | < 100ms | > 500ms |
| API Response Time (p99) | < 200ms | > 1000ms |
| Database Query Time (p99) | < 50ms | > 200ms |
| System Uptime | > 99.9% | < 99.5% |
| Error Rate | < 0.1% | > 1% |
| P&L Update Latency | < 30s | > 60s |

### 🚨 Alerting Rules

Alerts configured for:

- ⚠️ **Critical**: Service down, authentication failure, order rejection
- ⚠️ **High**: Position exceeds limit, margin breach, failed trade
- ⚠️ **Medium**: Slow API response, database connection issue
- ⚠️ **Low**: Report generation delay, cache miss rate high

### 🔍 Log Aggregation

```bash
# View real-time logs (development)
docker-compose logs -f trading-bot

# Search logs by keyword
docker-compose logs | grep "ERROR"

# Production log aggregation (GCP)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=trading-bot" --limit 50

# Structured query
gcloud logging read 'jsonPayload.severity="ERROR"' --limit 100 --format json
```

### 🏥 Health Checks

```bash
# Manual health check
curl http://localhost:8002/api/v1/health

# Response
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected",
    "vault": "connected",
    "ibkr": "connected"
  },
  "timestamp": "2025-11-11T10:30:00Z"
}

# Automated health check script
./infra/health-check.sh
```

---

## 🛠️ Development

### 🏃‍♂️ Local Development Setup

```bash
# 1️⃣ Clone repository
git clone https://github.com/AIgen-Solutions-s-r-l/SpreadPilot.git
cd SpreadPilot

# 2️⃣ Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3️⃣ Install dependencies
make install-all
# Or manually:
pip install -r trading-bot/requirements.txt
pip install -r admin-api/requirements.txt
pip install -r spreadpilot-core/requirements.txt

# 4️⃣ Install pre-commit hooks
pre-commit install

# 5️⃣ Start infrastructure
cd infra && ./compose-up.sh && cd ..

# 6️⃣ Run services locally
# Terminal 1: Trading Bot
cd trading-bot && uvicorn app.main:app --reload --port 8001

# Terminal 2: Admin API
cd admin-api && uvicorn app.main:app --reload --port 8002

# Terminal 3: Frontend
cd frontend && npm install && npm run dev
```

### 🎨 Code Formatting & Linting

```bash
# Format Python code (Black + isort)
make format

# Run linters (Ruff + Mypy)
make lint

# Fix auto-fixable linting issues
ruff check --fix .

# Type checking
mypy trading-bot admin-api spreadpilot-core

# Frontend linting
cd frontend && npm run lint
```

### 🧪 Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest -m e2e tests/e2e/ -v

# Run tests for specific service
pytest trading-bot/tests/ -v
pytest admin-api/tests/ -v

# Run tests in parallel
pytest -n auto tests/

# Generate HTML coverage report
pytest --cov --cov-report=html
open htmlcov/index.html
```

### 🐛 Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run service with debugger
python -m pdb trading-bot/app/main.py

# Debug in VS Code
# Add to .vscode/launch.json:
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Trading Bot",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--port",
        "8001"
      ],
      "cwd": "${workspaceFolder}/trading-bot",
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    }
  ]
}
```

---

## 🧪 Testing

### 📊 Test Coverage

Current test coverage: **90%+** across all services

| Service | Unit Tests | Integration Tests | E2E Tests | Coverage |
|---------|-----------|------------------|-----------|----------|
| Trading Bot | ✅ 95% | ✅ 90% | ✅ 85% | 92% |
| Admin API | ✅ 94% | ✅ 88% | ✅ 80% | 90% |
| Frontend | ⚠️ Pending | ⚠️ Pending | ⚠️ Pending | N/A |
| Report Worker | ✅ 93% | ✅ 87% | - | 91% |
| Alert Router | ✅ 96% | ✅ 89% | - | 93% |

### 🧪 Test Categories

**Unit Tests:** Fast, isolated tests for individual functions and classes
```bash
pytest tests/unit/ -v --cov
```

**Integration Tests:** Test interactions between services and external dependencies
```bash
pytest tests/integration/ -v
```

**End-to-End Tests:** Full workflow tests with real (paper trading) accounts
```bash
pytest -m e2e tests/e2e/ -v
```

### 🔄 CI/CD Pipeline

GitHub Actions runs on every push and pull request:

```yaml
✅ Linting (Ruff, Black, Mypy)
✅ Unit Tests (Python 3.9, 3.10, 3.11)
✅ Integration Tests
✅ Security Scans (Bandit, Trivy)
✅ Build Verification (Docker images)
✅ Frontend Build (npm build)
✅ E2E Tests (optional, on main branch)
```

View pipeline: https://github.com/AIgen-Solutions-s-r-l/SpreadPilot/actions

---

## 🔧 Troubleshooting

### 🚨 Common Issues & Solutions

#### Authentication Issues (NEW in v2.0.0)

**Problem:** Cannot log in to admin dashboard

```bash
# 1. Verify environment variables are set
echo $ADMIN_USERNAME
echo $ADMIN_PASSWORD_HASH
echo $JWT_SECRET

# 2. Generate correct password hash
htpasswd -bnBC 12 "" your_password | tr -d ':\n'

# 3. Test authentication endpoint
curl -X POST http://localhost:8002/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"

# 4. Check admin-api logs
docker-compose logs admin-api | grep -i auth
```

#### IBKR Connection Issues

**Problem:** Trading bot cannot connect to Interactive Brokers

```bash
# 1. Verify IB Gateway/TWS is running
netstat -an | grep 4001  # Live trading
netstat -an | grep 4002  # Paper trading

# 2. Check credentials in Vault
vault kv get secret/ibkr/vertical_spreads_strategy

# 3. Test connection manually
python -c "from ib_insync import IB; ib = IB(); ib.connect('127.0.0.1', 4002, clientId=1); print('Connected'); ib.disconnect()"

# 4. Check trading-bot logs
docker-compose logs trading-bot | grep -i "connection"
```

#### Database Connection Issues

**Problem:** Services cannot connect to databases

```bash
# PostgreSQL
docker-compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c '\conninfo'

# MongoDB
docker-compose exec mongodb mongosh "mongodb://$MONGO_USER:$MONGO_PASSWORD@localhost:27017/$MONGO_DB?authSource=admin" --eval "db.adminCommand('ping')"

# Redis
docker-compose exec redis redis-cli ping

# Check service logs
docker-compose logs postgres mongodb redis
```

#### Report Generation Failures

**Problem:** Reports not being generated or delivered

```bash
# 1. Check report-worker logs
docker-compose logs report-worker | tail -100

# 2. Verify GCS access
python -c "from google.cloud import storage; client = storage.Client(); print('GCS connection OK')"

# 3. Check SendGrid API key
curl -X POST https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer $SENDGRID_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"personalizations": [{"to": [{"email": "test@example.com"}]}],"from": {"email": "test@example.com"},"subject": "Test","content": [{"type": "text/plain", "value": "Test"}]}'

# 4. Manually trigger report generation
docker-compose exec report-worker python -c "from app.report_generator import generate_daily_report; generate_daily_report()"
```

#### Service Health Issues

**Problem:** Services showing as unhealthy

```bash
# Check watchdog logs
docker-compose logs watchdog

# Manually restart unhealthy service
docker-compose restart trading-bot

# Check resource usage
docker stats

# Review service health
./infra/health-check.sh
```

### 📞 Getting Help

**Before reaching out for support:**

1. ✅ Check service-specific README files in each directory
2. ✅ Review logs with `docker-compose logs [service]`
3. ✅ Enable debug logging with `LOG_LEVEL=DEBUG`
4. ✅ Consult troubleshooting section above
5. ✅ Search existing GitHub issues

**For enterprise support:**
- 📧 Email: support@aigensolutions.com
- 📞 Phone: [Contact for enterprise support]
- 💼 Enterprise SLA: 4-hour response time for critical issues

---

## 📋 Release History

For complete release history, see [CHANGELOG.md](CHANGELOG.md).

### Recent Releases

| Version | Date | Highlights |
|---------|------|------------|
| **🎉 v2.0.0.0** | 2025-11-11 | 🔐 **BREAKING:** OAuth2 authentication for admin dashboard<br/>✨ JWT token management with 24h expiration<br/>🔒 Session persistence across page reloads<br/>⚡ Automatic logout on 401 responses |
| **v1.4.2.0** | 2024-12-30 | Minor bug fixes and performance improvements |
| **v1.4.1.0** | 2024-12-29 | Enhanced error handling and logging |
| **v1.4.0.0** | 2024-12-28 | Watchdog service with auto-restart capabilities |
| **v1.3.0.0** | 2024-06-29 | Real-time P&L system with PostgreSQL<br/>Enhanced dashboard with WebSocket<br/>MinIO integration for reports<br/>Complete Vault migration |

### 🔮 Roadmap

**Q1 2025:**
- ✅ OAuth2 authentication (COMPLETED v2.0.0)
- 🔄 Frontend test infrastructure (IN PROGRESS)
- 📊 Enhanced performance metrics dashboard
- 🔐 Multi-factor authentication

**Q2 2025:**
- 👥 Multi-user support with RBAC
- 🔄 Token refresh mechanism
- 🍪 HttpOnly cookies for enhanced security
- 📱 Mobile app for iOS and Android

**Q3 2025:**
- 🤖 AI-powered trade analysis
- 📊 Advanced backtesting framework
- 🌐 Multi-broker support
- ☁️ Multi-cloud deployment

---

## 📄 License & Copyright

### Copyright Notice

```
Copyright © 2024-2025 AIgen Solutions S.r.l.
All rights reserved.
```

**AIgen Solutions S.r.l.**
Registered Office: [Address]
VAT: [VAT Number]
Company Registration: [Registration Number]

### Proprietary License

This software and associated documentation files (the "Software") are the proprietary
property of AIgen Solutions S.r.l. The Software is licensed, not sold.

**Restrictions:**

- ❌ You may NOT copy, modify, distribute, or create derivative works
- ❌ You may NOT reverse engineer, decompile, or disassemble the Software
- ❌ You may NOT remove or alter any copyright notices or proprietary legends
- ❌ You may NOT use the Software for commercial purposes without a commercial license

**Permitted Use:**

- ✅ Use the Software for evaluation purposes with AIgen Solutions' prior written consent
- ✅ Use the Software under a valid commercial license agreement with AIgen Solutions

**Warranty Disclaimer:**

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL AIGEN SOLUTIONS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Commercial Licensing

For commercial licensing inquiries, please contact:

- 📧 **Email:** licensing@aigensolutions.com
- 🌐 **Website:** https://www.aigensolutions.com
- 📞 **Phone:** [Contact for licensing]

**Available License Types:**

- **🏢 Enterprise License**: Unlimited users, priority support, custom features
- **💼 Professional License**: Up to 10 users, standard support
- **🚀 Startup License**: Special pricing for startups and small teams
- **🎓 Academic License**: Free for educational institutions

---

## 🤝 Support & Consulting

### 📧 Contact Information

**AIgen Solutions S.r.l.**

- 🌐 **Website:** https://www.aigensolutions.com
- 📧 **Email:** info@aigensolutions.com
- 💼 **Sales:** sales@aigensolutions.com
- 🛠️ **Support:** support@aigensolutions.com
- 📞 **Phone:** [Contact information]

### 🎯 Professional Services

We offer comprehensive professional services:

- **📊 Custom Strategy Development**: Build bespoke trading strategies
- **🔧 Integration Services**: Integrate with your existing systems
- **🏗️ Infrastructure Setup**: Cloud deployment and optimization
- **👨‍🏫 Training**: Hands-on training for your team
- **🛠️ Ongoing Support**: 24/7 support with SLA guarantees
- **📈 Performance Optimization**: Tune system for maximum efficiency

### 🆘 Enterprise Support Plans

| Plan | Response Time | Availability | Channels | Price |
|------|--------------|--------------|----------|-------|
| **Community** | Best effort | Forum only | GitHub Issues | Free |
| **Professional** | 2 business days | 9-5 local time | Email, Forum | Contact Sales |
| **Business** | 8 hours | 24/5 | Email, Phone, Chat | Contact Sales |
| **Enterprise** | 4 hours | 24/7/365 | Email, Phone, Chat, Slack | Contact Sales |
| **Mission Critical** | 1 hour | 24/7/365 | Dedicated team | Contact Sales |

---

## 🙏 Acknowledgments

SpreadPilot is built on top of exceptional open-source technologies and services:

### 🛠️ Core Technologies

- **Python** - Core programming language
- **FastAPI** - High-performance async web framework
- **React** - Modern frontend framework
- **TypeScript** - Type-safe JavaScript
- **PostgreSQL** - Reliable relational database
- **MongoDB** - Flexible document database
- **Redis** - In-memory data store
- **Docker** - Container platform

### ☁️ Cloud & Infrastructure

- **Google Cloud Platform** - Cloud hosting
- **HashiCorp Vault** - Secret management
- **Traefik** - Modern reverse proxy
- **Prometheus & Grafana** - Monitoring and visualization

### 📚 Libraries & Frameworks

- **ib_insync** - Interactive Brokers API wrapper
- **ReportLab** - PDF generation
- **Pandas** - Data analysis
- **SQLAlchemy** - Database ORM
- **Pydantic** - Data validation

### 🤝 Special Thanks

- **Interactive Brokers** - Trading platform API
- **SendGrid** - Email delivery service
- **Telegram** - Notification platform
- **Google Sheets** - Strategy signal source

---

<div align="center">

## 🚀 Built with Excellence by AIgen Solutions

**Professional Trading Automation • Enterprise-Grade Security • Cloud-Native Architecture**

[🌐 Website](https://www.aigensolutions.com) •
[📧 Contact](mailto:info@aigensolutions.com) •
[💼 Licensing](mailto:licensing@aigensolutions.com) •
[🛠️ Support](mailto:support@aigensolutions.com)

---

### ⭐ Star this repository if you find it valuable!

**Copyright © 2024-2025 AIgen Solutions S.r.l. - All Rights Reserved**

*Proprietary Software - Licensed Use Only*

</div>
