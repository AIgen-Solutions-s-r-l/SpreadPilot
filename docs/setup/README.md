# 🛠️ SpreadPilot Setup Documentation

> 🚀 **Complete setup guide** for deploying the SpreadPilot automated trading platform - step-by-step instructions for all system components

This comprehensive setup documentation will guide you through deploying SpreadPilot's microservices architecture, from basic infrastructure to advanced trading features.

---

## 🎯 System Overview

SpreadPilot is a **sophisticated automated trading platform** that executes QQQ options strategies based on signals from Google Sheets. The system comprises multiple interconnected services designed for reliability, scalability, and performance.

### 🏗️ **Architecture Components**

| 🔢 Order | 🎯 Component | 📋 Purpose | ⏱️ Setup Time |
|-----------|-------------|------------|----------------|
| 1️⃣ | 🗄️ **MongoDB** | Central database for trading data and configuration | 15 min |
| 2️⃣ | 🏦 **IB Gateway** | Interactive Brokers connection for trade execution | 30 min |
| 3️⃣ | 🤖 **Trading Bot** | Core trading engine with signal processing | 20 min |
| 4️⃣ | 🎛️ **Admin API** | Backend service for system management | 15 min |
| 5️⃣ | 🖥️ **Frontend** | React dashboard for monitoring and control | 10 min |
| 6️⃣ | 🔔 **Alert Router** | Multi-channel notification system | 10 min |
| 7️⃣ | 📊 **Report Worker** | Professional PDF/Excel report generation | 15 min |

### 🎯 **Additional Components** *(Optional)*
- 👀 **Watchdog** - System health monitoring and auto-recovery
- 🐘 **PostgreSQL** - Analytics database for P&L and commission data
- 🔴 **Redis** - High-performance caching and Pub/Sub messaging
- ☁️ **GCS Storage** - Cloud storage for reports and files

---

## 📋 Setup Sequence

### 🚀 **Quick Start (Recommended)**

For first-time setup, follow this sequence:

```mermaid
graph LR
    A[🗄️ MongoDB] --> B[🏦 IB Gateway]
    B --> C[🤖 Trading Bot]
    C --> D[🎛️ Admin API]
    D --> E[🖥️ Frontend]
    E --> F[🔔 Alert Router]
    F --> G[📊 Report Worker]
```

### 📋 **Detailed Setup Guides**

| 📄 Guide | 🎯 Component | 🔧 Complexity | 📋 Prerequisites |
|----------|-------------|----------------|-------------------|
| 🗄️ [**MongoDB Setup**](./0-mongodb.md) | Database Foundation | 🟢 Basic | Docker, Environment Variables |
| 🏦 [**IB Gateway Setup**](./1-ib-gateway.md) | Trading Infrastructure | 🟡 Moderate | IBKR Account, Credentials |
| 🤖 [**Trading Bot Setup**](./2-trading-bot.md) | Core Engine | 🟡 Moderate | MongoDB, IB Gateway |
| 🎛️ [**Admin API Setup**](./3-admin-api.md) | Management Backend | 🟢 Basic | MongoDB, JWT Secrets |
| 🖥️ [**Frontend Setup**](./4-frontend.md) | User Interface | 🟢 Basic | Admin API, Node.js |
| 🔔 [**Alert Router Setup**](./5-alert-router.md) | Notifications | 🟢 Basic | Telegram Bot, SendGrid |
| 📊 [**Report Worker Setup**](./6-report-worker.md) | Report Generation | 🟡 Moderate | PostgreSQL, GCS Bucket |

---

## ⚙️ Environment Configuration

### 📝 **Environment Variables Structure**

SpreadPilot uses a comprehensive `.env` file for configuration. Here's the structure:

```bash
# 🏗️ Core Infrastructure
MONGO_URI=mongodb://admin:password@localhost:27017
POSTGRES_URI=postgresql+asyncpg://user:password@localhost:5432/spreadpilot_pnl
REDIS_URL=redis://localhost:6379

# 🏦 Interactive Brokers
IB_GATEWAY_HOST=127.0.0.1
IB_GATEWAY_PORT=4002
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password

# 📊 Google Sheets Integration
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/...
GOOGLE_SHEETS_API_KEY=your_api_key

# 🔐 Authentication & Security
JWT_SECRET=your_jwt_secret_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=your_bcrypt_hash

# 🔔 Communications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SENDGRID_API_KEY=your_sendgrid_key

# ☁️ Cloud Services
GCS_BUCKET_NAME=spreadpilot-reports
GOOGLE_CLOUD_PROJECT=your-project-id
```

### 🔧 **Configuration Management**

- 📄 **Development** - Use `.env` file in project root
- 🚀 **Production** - Use GCP Secret Manager or HashiCorp Vault
- 🧪 **Testing** - Use separate test environment variables
- 🔐 **Security** - Never commit secrets to version control

---

## 🐳 Docker Deployment

### 🚀 **Complete System Deployment**

```bash
# 1️⃣ Clone and configure
git clone https://github.com/your-org/spreadpilot.git
cd spreadpilot
cp .env.template .env
# Edit .env with your configuration

# 2️⃣ Start infrastructure
docker-compose up -d mongodb redis postgres

# 3️⃣ Start core services
docker-compose up -d ib-gateway trading-bot

# 4️⃣ Start management services
docker-compose up -d admin-api frontend

# 5️⃣ Start auxiliary services
docker-compose up -d alert-router report-worker watchdog

# 6️⃣ Verify deployment
docker-compose ps
```

### 🎯 **Individual Service Deployment**

```bash
# 🗄️ Database services
docker-compose up -d mongodb postgres redis

# 🏦 Trading infrastructure
docker-compose up -d ib-gateway

# 🤖 Core trading services
docker-compose up -d trading-bot

# 🎛️ Management services
docker-compose up -d admin-api frontend

# 🔔 Notification services
docker-compose up -d alert-router

# 📊 Reporting services
docker-compose up -d report-worker

# 👀 Monitoring services
docker-compose up -d watchdog
```

### 📋 **Service Health Verification**

```bash
# ✅ Check all services
docker-compose ps

# 🔍 Check specific service logs
docker-compose logs trading-bot
docker-compose logs admin-api

# 🌐 Test service endpoints
curl http://localhost:8001/health  # Trading Bot
curl http://localhost:8002/health  # Admin API
curl http://localhost:8080         # Frontend
```

---

## 🎯 Feature-Specific Setup

### 💰 **P&L System Setup** *(v1.1.7.0)*

**📋 Prerequisites:**
- 🐘 PostgreSQL database
- 🔄 Alembic migrations
- 🤖 Trading Bot integration

**🚀 Setup Steps:**
1. Configure PostgreSQL connection in `.env`
2. Run database migrations: `alembic upgrade head`
3. Enable P&L service in Trading Bot configuration
4. Verify 30-second MTM calculations are running

### 📊 **Report Generation Setup** *(v1.1.7.0)*

**📋 Prerequisites:**
- ☁️ Google Cloud Storage bucket
- 📧 SendGrid API key
- 🐘 PostgreSQL with P&L data

**🚀 Setup Steps:**
1. Create GCS bucket for report storage
2. Configure GCS service account credentials
3. Set up SendGrid for email delivery
4. Configure monthly report schedules

### ⚠️ **Time Value Monitoring** *(v1.1.7.0)*

**📋 Prerequisites:**
- 🤖 Trading Bot with live market data
- 🔴 Redis for status tracking
- 🚨 Alert Router for notifications

**🚀 Setup Steps:**
1. Enable time value monitoring in Trading Bot
2. Configure liquidation threshold (default: $0.10)
3. Set up risk management alerts
4. Test automatic liquidation workflow

---

## 🔐 Security Configuration

### 🛡️ **Production Security Checklist**

#### 🔑 **Authentication & Secrets**
- ✅ Generate strong JWT secrets (256-bit minimum)
- ✅ Use bcrypt for password hashing
- ✅ Implement API key rotation schedule
- ✅ Configure HashiCorp Vault for secrets management
- ✅ Enable two-factor authentication where possible

#### 🌐 **Network Security**
- ✅ Configure private VPC for service communication
- ✅ Implement firewall rules for port restrictions
- ✅ Enable TLS/SSL for all HTTP communications
- ✅ Use load balancers with health checks
- ✅ Restrict admin interface access by IP

#### 🗄️ **Database Security**
- ✅ Use dedicated database users with minimal privileges
- ✅ Enable database encryption at rest
- ✅ Configure automated backups with encryption
- ✅ Implement database connection pooling
- ✅ Regular security patch updates

#### 📊 **Application Security**
- ✅ Input validation and sanitization
- ✅ Rate limiting on API endpoints
- ✅ Error handling without information disclosure
- ✅ Secure file upload and storage
- ✅ Regular dependency security scans

---

## 🔧 Advanced Configuration

### 🏗️ **High Availability Setup**

```bash
# 🔄 Load-balanced services
docker-compose -f docker-compose.yml -f docker-compose.ha.yml up -d

# 🗄️ Database clustering
docker-compose -f docker-compose.yml -f docker-compose.db-cluster.yml up -d

# 📊 Monitoring stack
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### 📈 **Performance Optimization**

- ⚡ **Connection Pooling** - Configure optimal pool sizes for databases
- 💾 **Caching Strategy** - Implement Redis caching for frequently accessed data
- 📊 **Query Optimization** - Add database indexes for P&L analytics
- 🔄 **Async Processing** - Use async patterns for non-blocking operations

### 🔍 **Monitoring & Observability**

- 📈 **Metrics Collection** - Prometheus for service metrics
- 📊 **Visualization** - Grafana dashboards for system health
- 📄 **Centralized Logging** - ELK stack for log aggregation
- 🔍 **Distributed Tracing** - OpenTelemetry for request tracing

---

## 🚨 Troubleshooting Guide

### 🔧 **Common Issues & Solutions**

#### 🏦 **IB Gateway Connection Issues**
```bash
# Check IB Gateway status
curl http://localhost:5000/v1/api/portal/sso/validate

# Verify credentials
docker logs ib-gateway

# Test connectivity
telnet localhost 4002
```

#### 🗄️ **Database Connection Problems**
```bash
# MongoDB connection test
mongosh mongodb://admin:password@localhost:27017

# PostgreSQL connection test
psql postgresql://user:password@localhost:5432/spreadpilot_pnl

# Redis connection test
redis-cli -h localhost -p 6379 ping
```

#### 🤖 **Service Health Issues**
```bash
# Check service logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]

# Full system restart
docker-compose down && docker-compose up -d
```

### 📞 **Getting Help**

1. 📋 **Check Prerequisites** - Verify all dependencies are properly configured
2. 📄 **Review Logs** - Examine service logs for error messages
3. 🔍 **Validate Configuration** - Ensure environment variables are correct
4. 🧪 **Test Connections** - Verify database and external service connectivity
5. 📖 **Consult Documentation** - Review specific component setup guides

---

## 🎯 Next Steps

### 📚 **Post-Setup Documentation**

After completing the setup, refer to these guides:

- 🔧 [**Operations Guide**](../04-operations-guide.md) - Daily operations and maintenance
- 🚀 [**Deployment Guide**](../02-deployment-guide.md) - Production deployment strategies
- 🛠️ [**Development Guide**](../03-development-guide.md) - Local development environment

### 🔄 **System Validation**

1. ✅ **Verify all services are running** - Check `docker-compose ps`
2. 🌐 **Test web interfaces** - Access Frontend at http://localhost:8080
3. 📊 **Check system health** - Monitor service endpoints
4. 🧪 **Run integration tests** - Validate end-to-end workflows
5. 📋 **Review monitoring** - Ensure alerts and logging are working

---

<div align="center">

**🛠️ Your complete SpreadPilot setup companion**

[🏗️ Architecture Overview](../01-system-architecture.md) • [🚀 Deployment Guide](../02-deployment-guide.md) • [🔧 Operations Guide](../04-operations-guide.md)

---

**📈 SpreadPilot v1.1.7.0** - *Professional Trading Platform Setup*

</div>