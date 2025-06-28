# 🚀 SpreadPilot Deployment Guide

> ☁️ **Complete production deployment guide** for deploying SpreadPilot to Google Cloud Platform - secure, scalable, and enterprise-ready automated trading platform

This comprehensive guide walks you through deploying the entire SpreadPilot microservices architecture to Google Cloud Platform, including all v1.1.7.0 features with PostgreSQL P&L system, advanced report generation, and cloud-native observability.

---

## 📋 Prerequisites

### 🔧 **Required Tools & Accounts**

#### ☁️ **Google Cloud Platform**
- ✅ **GCP Account** - Active account with billing enabled
- 🎯 **Billing Account** - Linked and verified payment method
- 💰 **Budget Alerts** - Recommended cost monitoring setup
- 🔐 **IAM Permissions** - Admin or Editor role for deployment

#### 🛠️ **Development Tools**
- 📦 **Google Cloud SDK** - Latest version (gcloud CLI)
- 🐳 **Docker** - Version 20.10+ for container builds
- 🔧 **Git** - Repository access and deployment scripts
- 🐍 **Python 3.11+** - For local testing and development

#### 🏦 **Trading Infrastructure**
- 🏦 **Interactive Brokers Account** - Paper or live trading account
- 🔑 **IBKR Credentials** - Username, password, and API access
- 📊 **Google Sheets** - Master strategy sheet with API access
- 🔐 **Google Sheets API Key** - Service account credentials

#### 📧 **Communication Services**
- 📮 **SendGrid Account** - Email delivery service with API key
- 🤖 **Telegram Bot** - Bot token and chat ID for alerts
- 📞 **SMS Service** *(Optional)* - For critical alert delivery

### 💾 **Infrastructure Estimates**

| 🎯 Component | 💰 Monthly Cost | 📊 Resources | 🔄 Scaling |
|-------------|----------------|---------------|-------------|
| 🤖 **Trading Bot** | $15-30 | 1GB RAM, 1 CPU | Auto-scale 1-3 |
| 🎛️ **Admin API** | $10-20 | 512MB RAM, 0.5 CPU | Auto-scale 1-3 |
| 📊 **Report Worker** | $5-15 | 512MB RAM, 0.5 CPU | On-demand |
| 🔔 **Alert Router** | $5-10 | 512MB RAM, 0.5 CPU | On-demand |
| 🍃 **MongoDB Atlas** | $25-50 | M10 cluster | Managed |
| 🐘 **PostgreSQL** | $20-40 | 2GB RAM, 1 CPU | Managed |
| 📮 **Pub/Sub** | $5-10 | Message volume | Pay-per-use |
| ☁️ **Storage** | $5-15 | Reports, logs | As needed |
| **📊 Total** | **$90-190** | - | Scales with usage |

### 🔐 **Security Preparation**

#### 🔑 **Required Secrets**
- ✅ **IB Username/Password** - Interactive Brokers credentials
- ✅ **JWT Secret** - 256-bit random key for authentication
- ✅ **Admin Password Hash** - Bcrypt hashed admin password
- ✅ **SendGrid API Key** - Email service authentication
- ✅ **Telegram Bot Token** - Alert delivery service
- ✅ **Google Sheets API** - Service account JSON or API key

#### 🛡️ **Network Security**
- 🌐 **Domain Name** - Custom domain for dashboard access
- 🔒 **SSL Certificate** - Automatic via Cloud Run
- 🔥 **Firewall Rules** - Restricted admin access
- 🎯 **Load Balancer** - Health checks and failover

---

## 🏗️ Initial GCP Setup

### 1️⃣ **Create GCP Project**

```bash
# Create a new GCP project
gcloud projects create spreadpilot-prod --name="SpreadPilot Production"

# Set the project as the default
gcloud config set project spreadpilot-prod

# Enable billing
gcloud billing projects link spreadpilot-prod --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### 2️⃣ **Enable Required APIs**

```bash
# 🚀 Enable core Cloud Run services
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com

# 🗄️ Enable database and storage services  
gcloud services enable sql.googleapis.com \
    storage.googleapis.com \
    firestore.googleapis.com

# 🔐 Enable security and secrets management
gcloud services enable secretmanager.googleapis.com \
    iam.googleapis.com \
    cloudresourcemanager.googleapis.com

# 📮 Enable messaging and monitoring
gcloud services enable pubsub.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    cloudtrace.googleapis.com
```

### 3️⃣ **Set Up Database Infrastructure**

#### 🍃 **MongoDB Setup (Recommended: MongoDB Atlas)**

```bash
# For production, use MongoDB Atlas (managed service)
# Create cluster at https://cloud.mongodb.com/

# 🔐 Create database user
# In Atlas Console: Database Access > Add New User
# Username: spreadpilot_admin
# Password: [Generate secure password]
# Role: Atlas Admin

# 🌐 Configure network access
# In Atlas Console: Network Access > Add IP Address
# Add GCP region IP ranges or 0.0.0.0/0 for testing
```

#### 🐘 **PostgreSQL Setup**

```bash
# 🐘 Create PostgreSQL instance for P&L system
gcloud sql instances create spreadpilot-postgres \
    --database-version=POSTGRES_15 \
    --tier=db-g1-small \
    --region=us-central1 \
    --availability-type=zonal \
    --backup-start-time=02:00 \
    --enable-bin-log \
    --storage-type=SSD \
    --storage-size=20GB

# 🔐 Create database user
gcloud sql users create spreadpilot_user \
    --instance=spreadpilot-postgres \
    --password=[SECURE_PASSWORD]

# 📊 Create P&L database
gcloud sql databases create spreadpilot_pnl \
    --instance=spreadpilot-postgres

# 🔗 Create connection name for Cloud Run
gcloud sql instances describe spreadpilot-postgres \
    --format="value(connectionName)"
```

#### ☁️ **GCS Storage Setup**

```bash
# 📁 Create bucket for report storage
gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://spreadpilot-reports-$PROJECT_ID

# 🔐 Set bucket permissions
gsutil iam ch serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://spreadpilot-reports-$PROJECT_ID

# ⏰ Set lifecycle policy for automatic cleanup
echo '{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}' > lifecycle.json

gsutil lifecycle set lifecycle.json gs://spreadpilot-reports-$PROJECT_ID
```

### 4️⃣ **Create Artifact Registry Repository**

```bash
# Create Docker repository
gcloud artifacts repositories create spreadpilot \
    --repository-format=docker \
    --location=us-central1 \
    --description="SpreadPilot Docker images"

# Configure Docker to use the repository
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## 🔐 Secret Management

### 1️⃣ **Create Secrets in Secret Manager**

#### 🏦 **Trading Credentials**

```bash
# 🏦 Interactive Brokers credentials
echo "your_ib_username" | gcloud secrets create ib-username --data-file=-
echo "your_ib_password" | gcloud secrets create ib-password --data-file=-

# 📊 Google Sheets integration
echo "https://docs.google.com/spreadsheets/d/your_sheet_id" | gcloud secrets create google-sheet-url --data-file=-
echo '{"type": "service_account", ...}' | gcloud secrets create google-sheets-credentials --data-file=-
```

#### 🔐 **Authentication & Security**

```bash
# 🔑 Generate and store JWT secret (256-bit)
echo "$(openssl rand -base64 32)" | gcloud secrets create jwt-secret --data-file=-

# 👤 Admin credentials
echo "admin" | gcloud secrets create admin-username --data-file=-
echo "$(python3 -c 'import bcrypt; print(bcrypt.hashpw(b"your_admin_password", bcrypt.gensalt()).decode())')" | gcloud secrets create admin-password-hash --data-file=-
```

#### 📧 **Communication Services**

```bash
# 📮 SendGrid email service
echo "your_sendgrid_api_key" | gcloud secrets create sendgrid-api-key --data-file=-
echo "admin@spreadpilot.com" | gcloud secrets create admin-email --data-file=-

# 🤖 Telegram notifications
echo "your_telegram_bot_token" | gcloud secrets create telegram-bot-token --data-file=-
echo "your_telegram_chat_id" | gcloud secrets create telegram-chat-id --data-file=-
```

#### 🗄️ **Database Connections**

```bash
# 🍃 MongoDB connection (if using Atlas)
echo "mongodb+srv://user:password@cluster.mongodb.net/spreadpilot_admin" | gcloud secrets create mongo-uri --data-file=-

# 🐘 PostgreSQL connection
echo "postgresql+asyncpg://spreadpilot_user:password@/spreadpilot_pnl?host=/cloudsql/PROJECT_ID:us-central1:spreadpilot-postgres" | gcloud secrets create postgres-uri --data-file=-

# ☁️ GCS bucket name
echo "spreadpilot-reports-$PROJECT_ID" | gcloud secrets create gcs-bucket-name --data-file=-
```

### 2️⃣ **Create Service Accounts**

#### 🤖 **Main Application Service Account**

```bash
# 🤖 Create main application service account
gcloud iam service-accounts create spreadpilot-sa \
    --display-name="SpreadPilot Main Service Account" \
    --description="Primary service account for SpreadPilot microservices"

# 🔐 Grant Secret Manager access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# 📮 Grant Pub/Sub access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber"

# 🐘 Grant Cloud SQL access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# ☁️ Grant Storage access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# 📊 Grant monitoring access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/monitoring.metricWriter"

# 📄 Grant logging access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
```

#### ⏰ **Scheduler Service Account**

```bash
# ⏰ Create dedicated scheduler service account
gcloud iam service-accounts create scheduler-sa \
    --display-name="Cloud Scheduler Service Account" \
    --description="Service account for Cloud Scheduler jobs"

# 📮 Grant Pub/Sub publisher role for scheduler
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"
```

---

## 📮 Pub/Sub Messaging Setup

### 1️⃣ **Create Pub/Sub Topics**

```bash
# 🚨 Alert system topics
gcloud pubsub topics create alerts
gcloud pubsub topics create critical-alerts

# 📊 Report generation topics
gcloud pubsub topics create daily-reports
gcloud pubsub topics create monthly-reports
gcloud pubsub topics create commission-reports

# 💰 P&L system topics
gcloud pubsub topics create pnl-updates
gcloud pubsub topics create commission-calculations

# 🔧 System monitoring topics
gcloud pubsub topics create system-health
gcloud pubsub topics create service-status
```

### 2️⃣ **Create Pub/Sub Subscriptions**

```bash
# 🔔 Alert Router subscriptions
gcloud pubsub subscriptions create alert-router-sub \
    --topic=alerts \
    --push-endpoint=https://alert-router-[SERVICE-URL]/api/v1/alerts \
    --ack-deadline=60

gcloud pubsub subscriptions create critical-alert-router-sub \
    --topic=critical-alerts \
    --push-endpoint=https://alert-router-[SERVICE-URL]/api/v1/critical-alerts \
    --ack-deadline=30

# 📊 Report Worker subscriptions
gcloud pubsub subscriptions create report-worker-daily-sub \
    --topic=daily-reports \
    --push-endpoint=https://report-worker-[SERVICE-URL]/api/v1/jobs/daily \
    --ack-deadline=600

gcloud pubsub subscriptions create report-worker-monthly-sub \
    --topic=monthly-reports \
    --push-endpoint=https://report-worker-[SERVICE-URL]/api/v1/jobs/monthly \
    --ack-deadline=1200

gcloud pubsub subscriptions create commission-report-sub \
    --topic=commission-reports \
    --push-endpoint=https://report-worker-[SERVICE-URL]/api/v1/jobs/commission \
    --ack-deadline=900

# 💰 P&L system subscriptions
gcloud pubsub subscriptions create pnl-processor-sub \
    --topic=pnl-updates \
    --push-endpoint=https://trading-bot-[SERVICE-URL]/api/v1/pnl/process \
    --ack-deadline=120

# Note: Replace [SERVICE-URL] with actual Cloud Run service URLs after deployment
```

---

## 🚀 Cloud Run Deployment

### 🛠️ **Pre-deployment Configuration**

```bash
# 📋 Set project variables
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export SA_EMAIL=spreadpilot-sa@$PROJECT_ID.iam.gserviceaccount.com

# 🔗 Get Cloud SQL connection name
export SQL_CONNECTION=$(gcloud sql instances describe spreadpilot-postgres --format="value(connectionName)")

# ☁️ Set GCS bucket name
export GCS_BUCKET=spreadpilot-reports-$PROJECT_ID

echo "Project ID: $PROJECT_ID"
echo "Service Account: $SA_EMAIL"
echo "SQL Connection: $SQL_CONNECTION"
echo "GCS Bucket: $GCS_BUCKET"
```

### 1️⃣ **Deploy Trading Bot Service**

```bash
# 🏗️ Build trading-bot container
cd trading-bot/
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/trading-bot:latest

# 🤖 Deploy trading-bot service
gcloud run deploy trading-bot \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/trading-bot:latest \
    --region=$REGION \
    --platform=managed \
    --service-account=$SA_EMAIL \
    --set-secrets=IB_USERNAME=ib-username:latest,IB_PASSWORD=ib-password:latest,MONGO_URI=mongo-uri:latest,POSTGRES_URI=postgres-uri:latest,SENDGRID_API_KEY=sendgrid-api-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CHAT_ID=telegram-chat-id:latest,GOOGLE_SHEET_URL=google-sheet-url:latest,GOOGLE_SHEETS_CREDENTIALS=google-sheets-credentials:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID,IB_GATEWAY_PORT=4002,LOG_LEVEL=INFO,ENVIRONMENT=production \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --memory=2Gi \
    --cpu=2 \
    --concurrency=1000 \
    --timeout=3600 \
    --min-instances=1 \
    --max-instances=5 \
    --port=8001 \
    --allow-unauthenticated

# 🔗 Get service URL
export TRADING_BOT_URL=$(gcloud run services describe trading-bot --region=$REGION --format="value(status.url)")
echo "Trading Bot URL: $TRADING_BOT_URL"
```

### 2️⃣ **Deploy Admin API Service**

```bash
# 🏗️ Build admin-api container
cd ../admin-api/
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/admin-api:latest

# 🎛️ Deploy admin-api service
gcloud run deploy admin-api \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/admin-api:latest \
    --region=$REGION \
    --platform=managed \
    --service-account=$SA_EMAIL \
    --set-secrets=MONGO_URI=mongo-uri:latest,ADMIN_USERNAME=admin-username:latest,ADMIN_PASSWORD_HASH=admin-password-hash:latest,JWT_SECRET=jwt-secret:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID,LOG_LEVEL=INFO,ENVIRONMENT=production,CORS_ORIGINS=https://dashboard.spreadpilot.com \
    --memory=1Gi \
    --cpu=1 \
    --concurrency=1000 \
    --timeout=3600 \
    --min-instances=1 \
    --max-instances=5 \
    --port=8002 \
    --allow-unauthenticated

# 🔗 Get service URL
export ADMIN_API_URL=$(gcloud run services describe admin-api --region=$REGION --format="value(status.url)")
echo "Admin API URL: $ADMIN_API_URL"
```

### 3️⃣ **Deploy Report Worker Service**

```bash
# 🏗️ Build report-worker container
cd ../report-worker/
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/report-worker:latest

# 📊 Deploy report-worker service
gcloud run deploy report-worker \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/report-worker:latest \
    --region=$REGION \
    --platform=managed \
    --service-account=$SA_EMAIL \
    --set-secrets=POSTGRES_URI=postgres-uri:latest,SENDGRID_API_KEY=sendgrid-api-key:latest,ADMIN_EMAIL=admin-email:latest,GCS_BUCKET_NAME=gcs-bucket-name:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID,LOG_LEVEL=INFO,ENVIRONMENT=production \
    --add-cloudsql-instances=$SQL_CONNECTION \
    --memory=2Gi \
    --cpu=2 \
    --concurrency=10 \
    --timeout=3600 \
    --min-instances=0 \
    --max-instances=10 \
    --port=8080 \
    --no-allow-unauthenticated

# 🔗 Get service URL
export REPORT_WORKER_URL=$(gcloud run services describe report-worker --region=$REGION --format="value(status.url)")
echo "Report Worker URL: $REPORT_WORKER_URL"
```

### 4️⃣ **Deploy Alert Router Service**

```bash
# 🏗️ Build alert-router container
cd ../alert-router/
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/alert-router:latest

# 🔔 Deploy alert-router service
gcloud run deploy alert-router \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/alert-router:latest \
    --region=$REGION \
    --platform=managed \
    --service-account=$SA_EMAIL \
    --set-secrets=SENDGRID_API_KEY=sendgrid-api-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CHAT_ID=telegram-chat-id:latest,ADMIN_EMAIL=admin-email:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID,LOG_LEVEL=INFO,ENVIRONMENT=production,DASHBOARD_URL=https://dashboard.spreadpilot.com \
    --memory=1Gi \
    --cpu=1 \
    --concurrency=1000 \
    --timeout=600 \
    --min-instances=0 \
    --max-instances=5 \
    --port=8080 \
    --no-allow-unauthenticated

# 🔗 Get service URL
export ALERT_ROUTER_URL=$(gcloud run services describe alert-router --region=$REGION --format="value(status.url)")
echo "Alert Router URL: $ALERT_ROUTER_URL"
```

### 5️⃣ **Deploy Frontend Service**

```bash
# 🏗️ Build frontend container
cd ../frontend/
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/frontend:latest

# 🖥️ Deploy frontend service
gcloud run deploy frontend \
    --image=$REGION-docker.pkg.dev/$PROJECT_ID/spreadpilot/frontend:latest \
    --region=$REGION \
    --platform=managed \
    --set-env-vars=REACT_APP_API_URL=$ADMIN_API_URL,REACT_APP_WS_URL=${ADMIN_API_URL/https/wss} \
    --memory=512Mi \
    --cpu=1 \
    --concurrency=1000 \
    --timeout=300 \
    --min-instances=1 \
    --max-instances=3 \
    --port=80 \
    --allow-unauthenticated

# 🔗 Get service URL
export FRONTEND_URL=$(gcloud run services describe frontend --region=$REGION --format="value(status.url)")
echo "Frontend URL: $FRONTEND_URL"
```

### 6️⃣ **Update Pub/Sub Subscriptions with Service URLs**

```bash
# 🔄 Update Pub/Sub subscriptions with actual service URLs
echo "Updating Pub/Sub subscriptions with service URLs..."

# 🔔 Update alert router subscriptions
gcloud pubsub subscriptions modify-push-config alert-router-sub \
    --push-endpoint="$ALERT_ROUTER_URL/api/v1/alerts"

gcloud pubsub subscriptions modify-push-config critical-alert-router-sub \
    --push-endpoint="$ALERT_ROUTER_URL/api/v1/critical-alerts"

# 📊 Update report worker subscriptions
gcloud pubsub subscriptions modify-push-config report-worker-daily-sub \
    --push-endpoint="$REPORT_WORKER_URL/api/v1/jobs/daily"

gcloud pubsub subscriptions modify-push-config report-worker-monthly-sub \
    --push-endpoint="$REPORT_WORKER_URL/api/v1/jobs/monthly"

gcloud pubsub subscriptions modify-push-config commission-report-sub \
    --push-endpoint="$REPORT_WORKER_URL/api/v1/jobs/commission"

# 💰 Update P&L subscriptions
gcloud pubsub subscriptions modify-push-config pnl-processor-sub \
    --push-endpoint="$TRADING_BOT_URL/api/v1/pnl/process"

echo "✅ Pub/Sub subscriptions updated successfully"
```

### 7️⃣ **Deploy IB Gateway (Optional for Cloud)**

> **⚠️ Note**: IB Gateway requires VNC/X11 for the login process. For production, consider running IB Gateway on a dedicated VM or using IB Cloud services.

#### 🖥️ **VM-based IB Gateway Deployment**

```bash
# 🖥️ Create VM for IB Gateway (recommended approach)
gcloud compute instances create ib-gateway-vm \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --subnet=default \
    --network-tier=PREMIUM \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-standard \
    --service-account=$SA_EMAIL \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=ib-gateway,allow-trading

# 🔥 Create firewall rule for IB Gateway
gcloud compute firewall-rules create allow-ib-gateway \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:4002,tcp:7497 \
    --source-ranges=10.0.0.0/8 \
    --target-tags=ib-gateway

# 📋 Get VM IP for configuration
export IB_GATEWAY_IP=$(gcloud compute instances describe ib-gateway-vm --zone=us-central1-a --format="get(networkInterfaces[0].networkIP)")
echo "IB Gateway VM IP: $IB_GATEWAY_IP"

# 🔄 Update Trading Bot with IB Gateway IP
gcloud run services update trading-bot \
    --region=$REGION \
    --update-env-vars=IB_GATEWAY_HOST=$IB_GATEWAY_IP
```

---

## ⏰ Cloud Scheduler Setup

### 1️⃣ **Set Up Report Scheduling**

#### 📊 **Daily P&L Reports**

```bash
# 📊 Daily P&L report (16:35 ET = 20:35 UTC in winter, 21:35 UTC in summer)
gcloud scheduler jobs create pubsub daily-pnl-report \
    --schedule="35 21 * * MON-FRI" \
    --topic=daily-reports \
    --message-body='{"job_type": "daily_pnl", "report_date": "today"}' \
    --time-zone="America/New_York" \
    --location=$REGION \
    --service-account=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com

# 📈 Daily position summary (09:35 ET = 13:35 UTC in winter, 14:35 UTC in summer)
gcloud scheduler jobs create pubsub daily-position-summary \
    --schedule="35 9 * * MON-FRI" \
    --topic=daily-reports \
    --message-body='{"job_type": "position_summary", "report_date": "today"}' \
    --time-zone="America/New_York" \
    --location=$REGION \
    --service-account=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com
```

#### 📅 **Monthly Reports & Commission Calculation**

```bash
# 📊 Monthly P&L reports (00:15 ET on 1st of month)
gcloud scheduler jobs create pubsub monthly-pnl-report \
    --schedule="15 0 1 * *" \
    --topic=monthly-reports \
    --message-body='{"job_type": "monthly_pnl", "target_month": "previous"}' \
    --time-zone="America/New_York" \
    --location=$REGION \
    --service-account=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com

# 💳 Commission calculation (00:45 ET on 1st of month)
gcloud scheduler jobs create pubsub commission-calculation \
    --schedule="45 0 1 * *" \
    --topic=commission-reports \
    --message-body='{"job_type": "commission_calculation", "target_month": "previous"}' \
    --time-zone="America/New_York" \
    --location=$REGION \
    --service-account=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com

# 📧 Monthly report distribution (08:00 ET on 1st of month)
gcloud scheduler jobs create pubsub monthly-report-distribution \
    --schedule="0 8 1 * *" \
    --topic=monthly-reports \
    --message-body='{"job_type": "distribute_monthly_reports", "target_month": "previous"}' \
    --time-zone="America/New_York" \
    --location=$REGION \
    --service-account=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### 2️⃣ **Set Up Database Maintenance Scheduling**

```bash
# 🧹 Daily database cleanup (02:00 ET)
gcloud scheduler jobs create pubsub db-maintenance \
    --schedule="0 2 * * *" \
    --topic=system-health \
    --message-body='{"job_type": "db_cleanup", "retention_days": 90}' \
    --time-zone="America/New_York" \
    --location=$REGION \
    --service-account=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com

# 📊 Weekly P&L rollup verification (Sundays at 03:00 ET)
gcloud scheduler jobs create pubsub weekly-pnl-verification \
    --schedule="0 3 * * SUN" \
    --topic=system-health \
    --message-body='{"job_type": "pnl_verification", "weeks_back": 4}' \
    --time-zone="America/New_York" \
    --location=$REGION \
    --service-account=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com
```

## CI/CD Setup

### 1. Create Cloud Build Triggers

```bash
# Create trigger for main branch
gcloud builds triggers create github \
    --repo-name=spreadpilot \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern=main \
    --build-config=cloudbuild-prod.yaml \
    --description="Deploy to production on main branch push"

# Create trigger for dev branch
gcloud builds triggers create github \
    --repo-name=spreadpilot \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern=dev \
    --build-config=cloudbuild-dev.yaml \
    --description="Deploy to development on dev branch push"
```

### 2. Create Cloud Build Configuration Files

Create `cloudbuild-prod.yaml` in the root of your repository:

```yaml
steps:
  # Install dependencies and build core library
  - name: 'gcr.io/cloud-builders/pip'
    entrypoint: pip
    args: ['install', '-e', './spreadpilot-core']

  # Build and push trading-bot
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/trading-bot:$COMMIT_SHA', '-f', 'trading-bot/Dockerfile', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/trading-bot:$COMMIT_SHA']

  # Build and push watchdog
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/watchdog:$COMMIT_SHA', '-f', 'watchdog/Dockerfile', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/watchdog:$COMMIT_SHA']

  # Build and push admin-api
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/admin-api:$COMMIT_SHA', '-f', 'admin-api/Dockerfile', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/admin-api:$COMMIT_SHA']

  # Build and push report-worker
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/report-worker:$COMMIT_SHA', '-f', 'report-worker/Dockerfile', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/report-worker:$COMMIT_SHA']

  # Build and push alert-router
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/alert-router:$COMMIT_SHA', '-f', 'alert-router/Dockerfile', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/alert-router:$COMMIT_SHA']

  # Build and push frontend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/frontend:$COMMIT_SHA', '-f', 'frontend/Dockerfile', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/frontend:$COMMIT_SHA']

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'trading-bot', '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/trading-bot:$COMMIT_SHA', '--region', 'us-central1', '--platform', 'managed']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'watchdog', '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/watchdog:$COMMIT_SHA', '--region', 'us-central1', '--platform', 'managed']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'admin-api', '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/admin-api:$COMMIT_SHA', '--region', 'us-central1', '--platform', 'managed']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'report-worker', '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/report-worker:$COMMIT_SHA', '--region', 'us-central1', '--platform', 'managed']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'alert-router', '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/alert-router:$COMMIT_SHA', '--region', 'us-central1', '--platform', 'managed']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'frontend', '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/frontend:$COMMIT_SHA', '--region', 'us-central1', '--platform', 'managed']

images:
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/trading-bot:$COMMIT_SHA'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/watchdog:$COMMIT_SHA'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/admin-api:$COMMIT_SHA'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/report-worker:$COMMIT_SHA'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/alert-router:$COMMIT_SHA'
  - 'us-central1-docker.pkg.dev/$PROJECT_ID/spreadpilot/frontend:$COMMIT_SHA'
```

Create a similar `cloudbuild-dev.yaml` file with appropriate modifications for the development environment.

## Domain and SSL Setup

### 1. Configure Custom Domain

```bash
# Map custom domain to frontend service
gcloud beta run domain-mappings create \
    --service=frontend \
    --domain=dashboard.spreadpilot.com \
    --region=us-central1
```

### 2. Configure SSL Certificate

GCP automatically provisions and manages SSL certificates for custom domains mapped to Cloud Run services.

## Verification

### 1. Verify Service Deployment

```bash
# List deployed services
gcloud run services list --platform=managed --region=us-central1

# Describe a specific service
gcloud run services describe trading-bot --region=us-central1
```

### 2. Verify Pub/Sub Configuration

```bash
# List topics
gcloud pubsub topics list

# List subscriptions
gcloud pubsub subscriptions list
```

### 3. Verify Cloud Scheduler Jobs

```bash
# List scheduler jobs
gcloud scheduler jobs list --location=us-central1
```

### 4. Verify Secret Manager Secrets

```bash
# List secrets
gcloud secrets list
```

## Troubleshooting

### 1. View Service Logs

```bash
# View logs for a specific service
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=trading-bot" --limit=10
```

### 2. Check Service Health

```bash
# Check service health
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://trading-bot-service-url/health
```

### 3. Manually Trigger Pub/Sub Messages

```bash
# Publish a message to a topic
gcloud pubsub topics publish daily-reports --message='{"job_type": "daily"}'
```

## Maintenance

### 1. Update Services

```bash
# Update a service
gcloud run services update trading-bot \
    --memory=2Gi \
    --cpu=2 \
    --region=us-central1
```

### 2. Rollback to Previous Revision

```bash
# List revisions
gcloud run revisions list --service=trading-bot --region=us-central1

# Rollback to a specific revision
gcloud run services update-traffic trading-bot \
    --to-revisions=trading-bot-00001-abc=100 \
    --region=us-central1
```

### 3. Update Secrets

```bash
# Update a secret
gcloud secrets versions add ib-password --data-file=./new-ib-password.txt
```
