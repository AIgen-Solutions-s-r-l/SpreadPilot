# SpreadPilot Deployment Guide

This guide provides step-by-step instructions for deploying the SpreadPilot system to Google Cloud Platform (GCP).

## Prerequisites

Before you begin, ensure you have the following:

- Google Cloud Platform account with billing enabled
- Google Cloud SDK installed and configured
- Docker installed locally
- Git repository access
- Interactive Brokers account and credentials
- SendGrid account for email notifications
- Telegram bot token and chat ID for alerts

## Initial Setup

### 1. Create a GCP Project

```bash
# Create a new GCP project
gcloud projects create spreadpilot-prod --name="SpreadPilot Production"

# Set the project as the default
gcloud config set project spreadpilot-prod

# Enable billing
gcloud billing projects link spreadpilot-prod --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### 2. Enable Required APIs

```bash
# Enable required GCP services
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    firestore.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    pubsub.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com
```

### 3. Set Up Firestore

```bash
# Create Firestore database in Native mode
gcloud firestore databases create --region=us-central

# Set up Firestore indexes (if needed)
gcloud firestore indexes composite create --collection-group=positions \
    --field-config field-path=follower_id,order=ascending \
    --field-config field-path=date,order=descending
```

### 4. Create Artifact Registry Repository

```bash
# Create Docker repository
gcloud artifacts repositories create spreadpilot \
    --repository-format=docker \
    --location=us-central1 \
    --description="SpreadPilot Docker images"

# Configure Docker to use the repository
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## Secret Management

### 1. Create Secrets in Secret Manager

```bash
# Create secrets for sensitive configuration
gcloud secrets create ib-username --data-file=./ib-username.txt
gcloud secrets create ib-password --data-file=./ib-password.txt
gcloud secrets create sendgrid-api-key --data-file=./sendgrid-api-key.txt
gcloud secrets create telegram-bot-token --data-file=./telegram-bot-token.txt
gcloud secrets create telegram-chat-id --data-file=./telegram-chat-id.txt
gcloud secrets create google-sheet-url --data-file=./google-sheet-url.txt
gcloud secrets create admin-username --data-file=./admin-username.txt
gcloud secrets create admin-password-hash --data-file=./admin-password-hash.txt
gcloud secrets create jwt-secret --data-file=./jwt-secret.txt
gcloud secrets create admin-email --data-file=./admin-email.txt
```

### 2. Create Service Account for Accessing Secrets

```bash
# Create service account
gcloud iam service-accounts create spreadpilot-sa \
    --display-name="SpreadPilot Service Account"

# Grant Secret Manager access
gcloud projects add-iam-policy-binding spreadpilot-prod \
    --member="serviceAccount:spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Grant MongoDB Access (Managed via Connection String)
# Access to MongoDB is typically controlled via connection strings containing usernames/passwords
# and network access rules (e.g., firewall settings, VPC peering, Atlas IP Access List).
# Ensure the service accounts or runtime environments for your services have the necessary
# credentials (usually via environment variables or secrets management) and network access
# to connect to the MongoDB instance.
# No specific IAM role binding like the one for Firestore is directly applicable here.

# Grant Pub/Sub access
gcloud projects add-iam-policy-binding spreadpilot-prod \
    --member="serviceAccount:spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"
```

## Pub/Sub Setup

### 1. Create Pub/Sub Topics

```bash
# Create topics for event-driven communication
gcloud pubsub topics create alerts
gcloud pubsub topics create daily-reports
gcloud pubsub topics create monthly-reports
```

### 2. Create Pub/Sub Subscriptions

```bash
# Create push subscriptions for services
gcloud pubsub subscriptions create alert-router-sub \
    --topic=alerts \
    --push-endpoint=https://alert-router-service-url/

gcloud pubsub subscriptions create report-worker-daily-sub \
    --topic=daily-reports \
    --push-endpoint=https://report-worker-service-url/

gcloud pubsub subscriptions create report-worker-monthly-sub \
    --topic=monthly-reports \
    --push-endpoint=https://report-worker-service-url/
```

## Cloud Run Deployment

### 1. Deploy Trading Bot Service

```bash
# Build and deploy trading-bot
gcloud builds submit --tag us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/trading-bot:latest

gcloud run deploy trading-bot \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/trading-bot:latest \
    --region=us-central1 \
    --platform=managed \
    --service-account=spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com \
    --set-secrets=IB_USERNAME=ib-username:latest,IB_PASSWORD=ib-password:latest,SENDGRID_API_KEY=sendgrid-api-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CHAT_ID=telegram-chat-id:latest,GOOGLE_SHEET_URL=google-sheet-url:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=spreadpilot-prod,IB_GATEWAY_HOST=ib-gateway-service-url,IB_GATEWAY_PORT=4002 \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=3 \
    --port=8080
```

### 2. Deploy Watchdog Service

```bash
# Build and deploy watchdog
gcloud builds submit --tag us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/watchdog:latest

gcloud run deploy watchdog \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/watchdog:latest \
    --region=us-central1 \
    --platform=managed \
    --service-account=spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com \
    --set-secrets=TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CHAT_ID=telegram-chat-id:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=spreadpilot-prod,TRADING_BOT_HOST=trading-bot-service-url,TRADING_BOT_PORT=8080,IB_GATEWAY_HOST=ib-gateway-service-url,IB_GATEWAY_PORT=4002 \
    --memory=512Mi \
    --cpu=0.5 \
    --min-instances=1 \
    --max-instances=1 \
    --port=8080
```

### 3. Deploy Admin API Service

```bash
# Build and deploy admin-api
gcloud builds submit --tag us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/admin-api:latest

gcloud run deploy admin-api \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/admin-api:latest \
    --region=us-central1 \
    --platform=managed \
    --service-account=spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com \
    --set-secrets=ADMIN_USERNAME=admin-username:latest,ADMIN_PASSWORD_HASH=admin-password-hash:latest,JWT_SECRET=jwt-secret:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=spreadpilot-prod,TRADING_BOT_HOST=trading-bot-service-url,TRADING_BOT_PORT=8080 \
    --memory=512Mi \
    --cpu=0.5 \
    --min-instances=1 \
    --max-instances=3 \
    --port=8080
```

### 4. Deploy Report Worker Service

```bash
# Build and deploy report-worker
gcloud builds submit --tag us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/report-worker:latest

gcloud run deploy report-worker \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/report-worker:latest \
    --region=us-central1 \
    --platform=managed \
    --service-account=spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com \
    --set-secrets=SENDGRID_API_KEY=sendgrid-api-key:latest,ADMIN_EMAIL=admin-email:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=spreadpilot-prod \
    --memory=512Mi \
    --cpu=0.5 \
    --min-instances=0 \
    --max-instances=3 \
    --port=8080 \
    --no-allow-unauthenticated
```

### 5. Deploy Alert Router Service

```bash
# Build and deploy alert-router
gcloud builds submit --tag us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/alert-router:latest

gcloud run deploy alert-router \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/alert-router:latest \
    --region=us-central1 \
    --platform=managed \
    --service-account=spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com \
    --set-secrets=SENDGRID_API_KEY=sendgrid-api-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CHAT_ID=telegram-chat-id:latest,ADMIN_EMAIL=admin-email:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=spreadpilot-prod,DASHBOARD_URL=https://dashboard.spreadpilot.com \
    --memory=512Mi \
    --cpu=0.5 \
    --min-instances=0 \
    --max-instances=3 \
    --port=8080 \
    --no-allow-unauthenticated
```

### 6. Deploy Frontend

```bash
# Build and deploy frontend
gcloud builds submit --tag us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/frontend:latest

gcloud run deploy frontend \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/frontend:latest \
    --region=us-central1 \
    --platform=managed \
    --memory=256Mi \
    --cpu=0.5 \
    --min-instances=1 \
    --max-instances=3 \
    --port=80
```

### 7. Deploy IB Gateway

```bash
# Build and deploy IB Gateway
gcloud builds submit --tag us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/ib-gateway:latest

gcloud run deploy ib-gateway \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/ib-gateway:latest \
    --region=us-central1 \
    --platform=managed \
    --set-secrets=TWS_USERID=ib-username:latest,TWS_PASSWORD=ib-password:latest \
    --set-env-vars=TRADING_MODE=paper \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=1 \
    --port=4002
```

## Cloud Scheduler Setup

### 1. Set Up Daily Report Scheduler

```bash
# Create service account for scheduler
gcloud iam service-accounts create scheduler-sa \
    --display-name="Scheduler Service Account"

# Grant Pub/Sub publisher role
gcloud projects add-iam-policy-binding spreadpilot-prod \
    --member="serviceAccount:scheduler-sa@spreadpilot-prod.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

# Create daily report scheduler (runs at 00:05 UTC)
gcloud scheduler jobs create pubsub daily-report-job \
    --schedule="5 0 * * *" \
    --topic=daily-reports \
    --message-body="{\"job_type\": \"daily\"}" \
    --time-zone="UTC" \
    --location=us-central1 \
    --service-account=scheduler-sa@spreadpilot-prod.iam.gserviceaccount.com
```

### 2. Set Up Monthly Report Scheduler

```bash
# Create monthly report scheduler (runs at 01:00 UTC on the 1st of each month)
gcloud scheduler jobs create pubsub monthly-report-job \
    --schedule="0 1 1 * *" \
    --topic=monthly-reports \
    --message-body="{\"job_type\": \"monthly\"}" \
    --time-zone="UTC" \
    --location=us-central1 \
    --service-account=scheduler-sa@spreadpilot-prod.iam.gserviceaccount.com
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
