# 📊 SpreadPilot

> 🚀 **Sophisticated copy-trading platform** that automates QQQ options strategies from Google Sheets to Interactive Brokers accounts

SpreadPilot is a modern microservices-based trading platform designed for scalable and reliable options trading automation. Built with Python, PostgreSQL, and cloud-native technologies.

## 🏆 Features

### 🔄 **Automated Trading**
- 📈 Replicate QQQ options strategies directly from Google Sheets to IBKR
- ⚡ Advanced limit-ladder execution with pre-trade margin checks
- 🎯 Dynamic pricing strategies for optimal order placement

### 💰 **Real-time P&L Management**
- ⏱️ 30-second MTM calculations with PostgreSQL storage
- 📊 Daily & monthly P&L rollups (16:30 ET daily, 00:10 ET monthly)
- 💳 Automated commission calculation on positive P&L with IBAN tracking

### 🛡️ **Risk Management**
- ⚠️ Time value monitoring with automatic liquidation (TV < $0.10)
- 🔒 Multi-follower support with isolated IBKR connections
- 📋 Comprehensive position monitoring and assignment handling

### 📈 **Reporting & Monitoring**
- 📄 Professional PDF and Excel reports with daily P&L breakdowns
- ☁️ Secure GCS storage with signed URL access
- 🎛️ Real-time admin dashboard with live logs and system status
- 🔔 Flexible alerting via Telegram and email
- 📧 Automated weekly commission report emails with PDF attachments

### 🏗️ **Architecture**
- 🐳 Containerized microservices with Docker
- ☁️ Cloud-ready deployment on Google Cloud Platform
- 🔐 HashiCorp Vault integration for secure credential management
- 📊 OpenTelemetry observability with Prometheus and Grafana

---

## 🚀 Quick Start

### 📋 Prerequisites

- 🐳 **Docker & Docker Compose**
- 🐍 **Python 3.9+**
- 🗄️ **PostgreSQL 13+** (P&L data storage)
- 🍃 **MongoDB** (trading data & configuration)
- 🔧 **Make** (optional, for convenience commands)
- 🏦 **Interactive Brokers account** with credentials
- ☁️ **Google Cloud Platform account** (for cloud deployment)
- 📧 **SendGrid API key** (email notifications)
- 🤖 **Telegram Bot token** (Telegram notifications)
- 📊 **Google Sheets URL** for trading strategy

### ⚡ One-Command Setup

```bash
# 1️⃣ Clone and enter directory
git clone https://github.com/your-repo/spreadpilot.git
cd spreadpilot

# 2️⃣ Start infrastructure services
cd infra/
./compose-up.sh

# 3️⃣ Build and start SpreadPilot
cd ..
docker-compose up --build -d

# 4️⃣ Verify everything is running
docker-compose ps
cd infra/ && ./health-check.sh
```

### 🎯 Access Points

- 🎛️ **Admin Dashboard**: http://localhost:8080
- 📊 **Grafana Monitoring**: http://localhost:3000
- 🗄️ **PostgreSQL**: localhost:5432
- 🍃 **MongoDB**: localhost:27017

### 🌐 Production Setup with Traefik

For production deployment with HTTPS and domain routing:

```bash
# 1️⃣ Configure your domain in .env
cp .env.traefik .env
# Edit .env and set DOMAIN=yourdomain.com

# 2️⃣ Start with Traefik
./scripts/start-with-traefik.sh
```

**Production URLs:**
- 🔐 **Admin API**: https://dashboard.yourdomain.com
- 📱 **Admin Dashboard**: https://app.yourdomain.com
- 🎛️ **Traefik Dashboard**: https://traefik.yourdomain.com

---

## ⚙️ Configuration

### 📝 Environment Setup

Create a `.env` file based on `deploy/.env.dev.template`:

```bash
# 🏦 Interactive Brokers
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password

# 📊 Google Sheets Integration
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/...
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# 📧 Communication
SENDGRID_API_KEY=your_sendgrid_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 🎛️ Admin Dashboard
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=hashed_password
JWT_SECRET=your_jwt_secret

# 🗄️ Databases
MONGO_URI=mongodb://user:password@localhost:27017
POSTGRES_URI=postgresql+asyncpg://user:password@localhost:5432/spreadpilot_pnl

# 🔐 Vault (Optional)
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-only-token
VAULT_ENABLED=true

# ☁️ Google Cloud Storage
GCS_BUCKET_NAME=spreadpilot-reports
GCS_SERVICE_ACCOUNT_KEY_PATH=/path/to/gcs-key.json
```

### 🔐 Vault Integration

SpreadPilot supports HashiCorp Vault for secure credential management:

- 📊 `secret/ibkr/vertical_spreads_strategy` - Main strategy credentials
- 👥 `secret/ibkr/follower_[id]` - Follower-specific credentials
- 🔧 `secret/ibkr/original_strategy` - Legacy EMA strategy credentials

---

## 🏗️ Architecture

### 🎯 Core Services

| Service | Description | Port |
|---------|-------------|------|
| 🤖 **Trading Bot** | Executes trades, manages positions | 8001 |
| 🎛️ **Admin API** | Backend for dashboard, follower management | 8002 |
| 🖥️ **Frontend** | React admin dashboard | 8080 |
| 📱 **Admin Dashboard** | Vue 3 mobile-responsive SPA | 3001 |
| 👀 **Watchdog** | Autonomous container health monitoring & restart | - |
| 📊 **Report Worker** | PDF/Excel report generation | 8004 |
| 🔔 **Alert Router** | Telegram/email notifications | 8005 |

### 🗄️ Data Stores

- 🐘 **PostgreSQL**: P&L data, commission calculations
- 🍃 **MongoDB**: Trading data, follower configuration
- 🔴 **Redis**: Alert streams, Pub/Sub messaging, signal caching
- 🔐 **Vault**: Secure credential storage
- ☁️ **GCS**: Report file storage

### 📊 Data Flow

```mermaid
graph LR
    A[📊 Google Sheets] --> B[📡 Signal Listener]
    B --> C[🔴 Redis Pub/Sub]
    C --> D[🤖 Trading Bot]
    D --> E[🏦 IB Gateway]
    E --> F[🐘 PostgreSQL]
    F --> G[📊 Report Worker]
    G --> H[☁️ GCS Storage]
```

---

## 🛠️ Development

### 🏃‍♂️ Running Locally

```bash
# 🔧 Initialize development environment
make init-dev

# 📦 Install all dependencies
make install-all

# 🧪 Run tests
make test

# 🎨 Format code
make format

# 🔍 Run linting
make lint

# 📊 Test with coverage
make test-coverage
```

### 🧪 Testing

```bash
# 🧪 All tests
make test

# ⚡ Unit tests only
pytest tests/unit/

# 🔗 Integration tests only
pytest tests/integration/

# 🌐 End-to-End tests (requires Docker)
pytest -m e2e tests/e2e/

# 📊 Coverage report
make test-coverage
```

#### 🌐 End-to-End Testing

SpreadPilot includes comprehensive E2E tests that validate the complete workflow:

```bash
# Start E2E test environment
docker-compose -f docker-compose.e2e.yml up -d

# Run E2E tests
pytest -m e2e tests/e2e/e2e_test.py -v

# View email capture UI
open http://localhost:8025

# Clean up
docker-compose -f docker-compose.e2e.yml down -v
```

The E2E test suite validates:
- ✅ Signal ingestion from Google Sheets
- ✅ Trade execution through IBKR
- ✅ Position management and tracking
- ✅ PDF report generation and email delivery
- ✅ Error handling and retry mechanisms
- ✅ Performance metrics calculation

### 🐳 Docker Development

```bash
# 🏗️ Build all services
docker-compose build

# 🚀 Start all services
docker-compose up -d

# 📋 Check service status
docker-compose ps

# 📄 View logs
docker-compose logs trading-bot

# 🔄 Restart a service
docker-compose restart trading-bot

# 🧹 Clean up
docker-compose down
```

---

## 🌐 API Documentation

### 🎛️ Admin API Endpoints

Base URL: `/api/v1`

#### 👥 Followers Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| 📋 GET | `/followers` | List all followers |
| ➕ POST | `/followers` | Register new follower |
| 🔄 POST | `/followers/{id}/toggle` | Enable/disable follower |
| ❌ POST | `/close/{id}` | Close all positions |

#### 📊 Example Response

```json
{
  "id": "follower123",
  "email": "trader@example.com",
  "iban": "DE12345678901234567890",
  "commission_pct": 20.0,
  "active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## 🔒 Security

SpreadPilot implements comprehensive security best practices:

### 🛡️ Security Features

- **🔍 Vulnerability Scanning**: Automated Trivy scans for dependencies and containers
- **🐳 Container Security**: All services run as non-root users
- **🌐 Security Headers**: CSP, HSTS, X-Frame-Options configured
- **🔐 Database TLS**: Encrypted connections for MongoDB and PostgreSQL
- **👤 Least Privilege**: IAM policies follow principle of least privilege
- **🔑 PIN Verification**: 0312 PIN required for dangerous operations

### 🚀 Security Tools

```bash
# Run security scan
./trivy_scan.sh

# Generate secure PIN
./scripts/security-utils.py generate-pin

# Check security compliance
./scripts/security-utils.py audit
```

### 📋 Security Checklist

Review `security_checklist.md` before each deployment to ensure all security requirements are met.

---

## ☁️ Deployment

### 🚀 Google Cloud Platform

```bash
# 🔧 Configure GCP
gcloud config set project your-project-id

# 🏗️ Build and deploy
gcloud builds submit --config cloudbuild.yaml

# 📊 Monitor deployment
gcloud run services list
```

### 📋 Deployment Checklist

- ✅ GCP project configured
- ✅ Cloud Build, Cloud Run, Artifact Registry APIs enabled
- ✅ Secret Manager configured with credentials
- ✅ Pub/Sub topics created for alerts/reports
- ✅ Cloud Scheduler jobs configured
- ✅ Firewall rules configured
- ✅ Domain and SSL certificates set up

---

## 🔧 Troubleshooting

### 🚨 Common Issues

#### 🐳 Container Issues
```bash
# Check container status
docker-compose ps

# View service logs
docker-compose logs trading-bot

# Restart services
docker-compose restart
```

#### 🏦 IBKR Connection
- ✅ Verify IB Gateway is running
- ✅ Check credentials in Vault/environment
- ✅ Ensure firewall allows connections
- ✅ Validate account permissions

#### 📊 Google Sheets Access
- ✅ Service account has Sheet access
- ✅ Google credentials file is valid
- ✅ Sheet URL is correct format

#### 🗄️ Database Connections
```bash
# Test PostgreSQL
psql postgresql://user:pass@localhost:5432/spreadpilot_pnl

# Test MongoDB
mongosh mongodb://user:pass@localhost:27017/spreadpilot_admin
```

### 📞 Getting Help

- 📖 Check service-specific READMEs in each directory
- 📄 Review logs with `docker-compose logs [service]`
- 🔍 Enable debug logging with `LOG_LEVEL=DEBUG`
- 🐛 Report issues on GitHub (if applicable)

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

### 📋 Contribution Process

1. 🍴 **Fork** the repository
2. 🌿 **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. 🎨 **Format** code (`make format`)
4. 🧪 **Test** changes (`make test`)
5. 📝 **Commit** with conventional format (`feat: add amazing feature`)
6. 📤 **Push** to branch (`git push origin feature/amazing-feature`)
7. 🔄 **Create** Pull Request

### 📏 Code Standards

- 🐍 Python 3.9+ compatibility
- 🎨 Black code formatting
- 📏 Flake8 linting compliance
- 🧪 95%+ test coverage for new features
- 📝 Conventional Commits for messages
- 📚 Documentation for public APIs

### 🏗️ Development Workflow

```bash
# 🔧 Set up development environment
make init-dev

# 🎨 Format before committing
make format

# 🧪 Run full test suite
make test

# 🔍 Check linting
make lint
```

---

## 📋 Version History

| Version | Date | Changes |
|---------|------|---------|
| 🎯 **v1.1.7.0** | 2024-12-28 | ➕ Enhanced PDF/Excel reports with GCS integration |
| 💰 **v1.1.6.0** | 2024-12-27 | ➕ Monthly commission calculation system |
| 📊 **v1.1.5.0** | 2024-12-26 | ➕ Real-time P&L system with PostgreSQL |
| ⚠️ **v1.1.4.0** | 2024-12-25 | ➕ Time value monitoring and liquidation |

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- 🏦 **Interactive Brokers** for trading platform
- 📊 **Google Sheets** for strategy signals
- 🐳 **Docker & Docker Compose** for containerization
- ☁️ **Google Cloud Platform** for cloud infrastructure
- 🔐 **HashiCorp Vault** for secrets management
- 📧 **SendGrid** for email delivery
- 🤖 **Telegram** for instant notifications

---

<div align="center">

**🚀 Built with ❤️ for automated trading**

[📖 Documentation](./docs/) • [🐛 Issues](https://github.com/your-repo/spreadpilot/issues) • [💬 Discussions](https://github.com/your-repo/spreadpilot/discussions)

</div>