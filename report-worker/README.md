# 📊 SpreadPilot Report Worker

> 📈 **Professional report generation service** that creates PDF and Excel reports with P&L data, commission calculations, and secure cloud storage

The Report Worker is a specialized microservice responsible for generating comprehensive monthly reports for followers and calculating daily P&L with real-time data integration.

## ✨ Features

### 📄 **Report Generation**
- 📋 **PDF Reports**: Professional layouts with ReportLab
- 📊 **Excel Reports**: Structured spreadsheets with pandas/openpyxl
- 💰 **P&L Integration**: Real-time daily P&L data from PostgreSQL
- 💳 **Commission Tracking**: Automated commission calculations with IBAN details

### ☁️ **Cloud Integration**
- 🗄️ **GCS Storage**: Secure file storage in Google Cloud Storage
- 🔗 **MinIO/S3 Support**: Alternative object storage with 180-day lifecycle
- 📎 **Pre-signed URLs**: 30-day secure download links
- 📨 **Email Delivery**: Automated report distribution via SendGrid
- 🔐 **Secret Management**: Secure credential loading from MongoDB

### 🎯 **Automation**
- ⏰ **Scheduled Jobs**: Google Cloud Pub/Sub triggered processing
- 🔄 **Real-time Data**: 30-second MTM calculations
- 📅 **Monthly Rollups**: Automated monthly aggregation at 00:10 ET
- 📧 **Weekly Email Reports**: Automated commission report emails every Monday
- 🚨 **Health Monitoring**: Built-in health check endpoints

---

## 🚀 Setup

### 📋 Prerequisites

- 🐍 **Python 3.11+** - Runtime environment
- 🍃 **MongoDB** - Data storage and secret management
- 🐘 **PostgreSQL** - P&L and commission data storage
- ☁️ **Google Cloud Storage** - Report file storage
- 📮 **Google Cloud Pub/Sub** - Job scheduling and messaging
- 📧 **SMTP Server** - Email delivery (SendGrid recommended)

### ⚙️ Environment Configuration

Create a `.env` file with the following variables:

```bash
# 🏗️ Core Settings
GCP_PROJECT_ID=spreadpilot-test
MONGO_URI=mongodb://user:password@localhost:27017
MONGO_DB_NAME=spreadpilot_admin
MONGO_DB_NAME_SECRETS=spreadpilot_secrets

# 📊 Report Settings
DEFAULT_COMMISSION_PERCENTAGE=20.0
REPORT_SENDER_EMAIL=capital@tradeautomation.it
ADMIN_EMAIL=admin@example.com

# ⏰ Timing Settings
MARKET_CLOSE_TIMEZONE=America/New_York
MARKET_CLOSE_HOUR=16
MARKET_CLOSE_MINUTE=10

# 📧 Email Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASSWORD=password
SMTP_TLS=true

# 📮 SendGrid Settings (for commission report emails)
SENDGRID_API_KEY=your_sendgrid_api_key

# ☁️ GCS Settings (for report file storage)
GCS_BUCKET_NAME=spreadpilot-reports
GCS_SERVICE_ACCOUNT_KEY_PATH=/path/to/service-account.json

# 🔗 MinIO/S3 Settings (Alternative to GCS - Optional)
MINIO_ENDPOINT_URL=https://minio.example.com
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET_NAME=spreadpilot-reports
MINIO_REGION=us-east-1
MINIO_SECURE=true

# 🐘 PostgreSQL Settings (for P&L data)
POSTGRES_URI=postgresql+asyncpg://user:password@localhost:5432/spreadpilot_pnl

# 📝 Logging
LOG_LEVEL=INFO

# 🌍 Environment
APP_ENV=development
```

---

## 🏃‍♂️ Running the Service

### 🔧 Local Development

```bash
# 1️⃣ Install dependencies
pip install -e ./spreadpilot-core
pip install -r requirements.txt

# 2️⃣ Set up environment
cp .env.template .env
# Edit .env with your configuration

# 3️⃣ Run the service
python app/main.py
```

### 🐳 Docker Deployment

```bash
# 🏗️ Build the image
docker build -t spreadpilot-report-worker .

# 🚀 Run with environment file
docker run -p 8084:8084 --env-file .env spreadpilot-report-worker

# 📋 Check container status
docker ps | grep report-worker
```

### 🎯 Service Endpoints

- 🔍 **Health Check**: `GET /health`
- 📨 **Pub/Sub Handler**: `POST /` (receives job messages)
- 📊 **Metrics**: `GET /metrics` (Prometheus format)

---

## 🎯 Job Types

The Report Worker handles two main job types triggered via Google Cloud Pub/Sub:

### 📅 **Daily P&L Calculation**
```json
{
  "job_type": "daily",
  "date": "2024-12-28"
}
```
- ⏱️ Calculates and stores daily P&L for specified date
- 🔄 Updates PostgreSQL with mark-to-market values
- 📊 Aggregates data at follower level
- ⏰ Typically triggered at 16:30 ET after market close

### 📊 **Monthly Report Generation**
```json
{
  "job_type": "monthly", 
  "year": 2024,
  "month": 12,
  "follower_id": "optional_specific_follower"
}
```
- 📄 **Report Contents**:
  - 📋 Daily P&L table for the month
  - 💰 Total P&L and commission calculations
  - 💳 IBAN information for payment processing
  - 📈 Professional PDF and Excel formats

- ☁️ **Processing Flow**:
  - 🏗️ Generate PDF/Excel reports using ReportLab and pandas
  - 📤 Upload to MinIO/S3 or Google Cloud Storage
  - 🔗 Create pre-signed URLs (30-day expiration for MinIO, 24-hour for GCS)
  - 📧 Email reports with download links or attachments
  - 💾 Update database with report_sent status
  - 🔔 Send admin notifications

### 📧 **Weekly Commission Email Reports**
The Report Worker includes a cron job for automated weekly commission report emails:

- **🗓️ Schedule**: Every Monday at 9:00 AM UTC
- **📋 Process**:
  - Query commission_monthly table for unsent reports (sent=false)
  - Generate PDF reports with commission details
  - Attach PDF and include signed Excel download link
  - Send via SendGrid with admin CC
  - Mark reports as sent in database
- **🔄 Retry Logic**: 3 attempts with exponential backoff
- **📁 Cron Setup**: 
  ```bash
  # Install crontab (included in Docker image)
  crontab /app/crontab
  
  # Manual execution
  python app/cron_email_reports.py
  ```

---

## 🔗 MinIO/S3 Integration

The Report Worker supports MinIO as an alternative to Google Cloud Storage for report storage:

### **Features**:
- 📁 **Object Storage**: Store PDF/Excel reports in MinIO buckets
- ⏳ **Lifecycle Management**: Automatic 180-day object expiration
- 🔐 **Pre-signed URLs**: 30-day secure download links
- 🔄 **Fallback Support**: Seamless fallback to email attachments if MinIO is unavailable

### **Configuration**:
When MinIO environment variables are configured, the service will:
1. Upload generated reports to MinIO with 180-day lifecycle
2. Generate pre-signed URLs valid for 30 days
3. Send emails with download links instead of attachments
4. Store URLs in database for tracking

If MinIO is not configured or upload fails, the service automatically falls back to sending reports as email attachments.

---

## 🛠️ Development

### 🧪 Testing

```bash
# 🧪 Run all tests
pytest

# ⚡ Run specific test module
pytest tests/unit/service/test_report_generator.py

# 📊 Run with coverage
pytest --cov=app --cov-report=html

# 🔍 Run with verbose output
pytest -v
```

### 🎨 Code Quality

```bash
# 🎨 Format code
black app/ tests/

# 📏 Check linting
flake8 app/ tests/

# 🔍 Type checking
mypy app/
```

### 🐛 Debugging

```bash
# 📄 View logs
docker-compose logs report-worker

# 🔍 Debug mode
LOG_LEVEL=DEBUG python app/main.py

# 📊 Test report generation locally
python -c "
from app.service.report_generator import generate_follower_reports
from app.config import get_settings
# Test report generation with sample data
"