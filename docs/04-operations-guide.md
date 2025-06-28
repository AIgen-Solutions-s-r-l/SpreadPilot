# 🔧 SpreadPilot Operations Guide

This comprehensive guide provides instructions for monitoring, maintaining, and troubleshooting the SpreadPilot system in production environments.

## 📋 Table of Contents

- [Monitoring](#-monitoring)
- [Alerting](#-alerting)
- [Routine Maintenance](#-routine-maintenance)
- [Troubleshooting](#-troubleshooting)
- [Performance Tuning](#-performance-tuning)
- [Security](#-security)
- [Disaster Recovery](#-disaster-recovery)
- [Compliance and Auditing](#-compliance-and-auditing)
- [Quick Reference](#-quick-reference)

## 📊 Monitoring

### ☁️ Cloud Monitoring

SpreadPilot uses Google Cloud Monitoring with OpenTelemetry instrumentation for comprehensive observability.

#### 🔍 Accessing Cloud Monitoring

1. Navigate to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Go to **Monitoring** → **Overview**

#### 📈 Key Dashboards

| Dashboard | Description | Key Metrics |
|-----------|-------------|-------------|
| **SpreadPilot Overview** | System health summary | Service uptime, error rates, request counts |
| **Trading Bot Performance** | Trading operations metrics | Order execution rate, position counts, latency |
| **Service Health** | Individual service status | Health check results, resource usage |
| **Error Rates** | Error tracking across services | Error counts by service and type |

#### 🎨 Creating Custom Dashboards

```bash
# Example: Create a dashboard via API
gcloud monitoring dashboards create --config-from-file=dashboard.yaml
```

Dashboard configuration example:
```yaml
displayName: "Custom Trading Metrics"
mosaicLayout:
  columns: 12
  tiles:
  - width: 6
    height: 4
    widget:
      title: "Order Execution Rate"
      xyChart:
        dataSets:
        - timeSeriesQuery:
            timeSeriesFilter:
              filter: metric.type="custom.googleapis.com/trading/orders_executed"
```

### 📊 Grafana Monitoring

Advanced visualization platform for detailed metrics analysis.

#### 🌐 Access Points

- **Local Development**: `http://localhost:3000`
- **Production**: `https://grafana.your-domain.com`

Default credentials:
```
Username: admin
Password: admin  # ⚠️ Change in production!
```

#### 📈 Available Dashboards

1. **System Overview** - Overall health metrics
2. **Trading Performance** - Order execution and P&L tracking
3. **Service Performance** - Detailed service metrics
4. **Error Tracking** - Error patterns and analysis

### 📝 Logging

Structured logging integrated with Cloud Logging for comprehensive system insights.

#### 🔍 Common Log Queries

**Service-specific logs:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="trading-bot"
severity>=INFO
```

**Error tracking:**
```
severity>=ERROR
jsonPayload.service=~"trading-bot|admin-api"
timestamp>="2024-01-01T00:00:00Z"
```

**Follower operations:**
```
jsonPayload.follower_id="FOLLOWER_ID"
jsonPayload.operation=~"execute_order|update_position"
```

**Performance analysis:**
```
jsonPayload.latency_ms>1000
jsonPayload.operation="signal_processing"
```

#### 📊 Log Severity Levels

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed debugging info | Variable values, function entry/exit |
| **INFO** | Normal operations | Order executed, position updated |
| **WARNING** | Potential issues | High latency, retry attempts |
| **ERROR** | Recoverable errors | API timeout, invalid data |
| **CRITICAL** | System failures | Database connection lost |

## 🚨 Alerting

### 📢 Alert Configuration

#### 🎯 Predefined Alert Policies

| Alert | Condition | Notification |
|-------|-----------|--------------|
| **Service Down** | Health check fails >2 min | Email, Telegram, PagerDuty |
| **High Error Rate** | Error rate >5% for 5 min | Email, Telegram |
| **Trading Bot Offline** | No heartbeat >5 min | Email, Telegram, SMS |
| **IB Gateway Disconnected** | Connection lost >1 min | All channels |
| **Assignment Detected** | Option assignment event | All channels + Dashboard |

#### ➕ Creating Custom Alerts

```bash
# Create alert policy via CLI
gcloud alpha monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="High Memory Usage" \
    --condition-display-name="Memory >80%" \
    --condition="CONDITION_THRESHOLD" \
    --if="ABOVE" \
    --threshold-value=0.8 \
    --duration="300s"
```

### 📨 Notification Channels

Configure multiple notification channels for redundancy:

1. **📧 Email** - Primary notifications
2. **💬 Telegram** - Real-time alerts
3. **📱 SMS** - Critical alerts only
4. **🚨 PagerDuty** - On-call rotation

#### 🔧 Channel Configuration

```bash
# Add Telegram channel
gcloud alpha monitoring channels create \
    --display-name="Telegram Alerts" \
    --type=telegram \
    --channel-labels=bot_token=YOUR_BOT_TOKEN,chat_id=YOUR_CHAT_ID
```

## 🛠️ Routine Maintenance

### 💾 Backup and Restore

#### 🗄️ MongoDB Backup Strategies

**Local Docker Environment:**
```bash
# Create backup
docker-compose exec mongo mongodump --out /backup/$(date +%Y%m%d_%H%M%S)
docker cp mongo:/backup ./local_backups/

# Automated daily backup script
#!/bin/bash
BACKUP_DIR="./backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR
docker-compose exec -T mongo mongodump --out /data/backup
docker cp mongo:/data/backup $BACKUP_DIR
find ./backups -mtime +7 -type d -exec rm -rf {} +  # Keep 7 days
```

**Production (MongoDB Atlas):**
- Enable automated backups in Atlas console
- Configure retention policy (recommended: 7 days continuous, 4 weekly snapshots)
- Set up cross-region backup replication

**Self-Hosted Production:**
```bash
# Cron job for automated backups
0 2 * * * /usr/bin/mongodump --uri="mongodb://user:pass@host:port/db" --out=/backup/$(date +\%Y\%m\%d) && gsutil -m cp -r /backup/$(date +\%Y\%m\%d) gs://backup-bucket/
```

#### 🔄 Restore Procedures

```bash
# Restore from mongodump
mongorestore --drop --uri="mongodb://localhost:27017" /path/to/backup/

# Restore specific collections
mongorestore --drop --uri="mongodb://localhost:27017" --nsInclude="spreadpilot.followers" /backup/

# Point-in-time restore (Atlas)
# Use Atlas UI or API for PITR within retention window
```

### 📦 Service Updates

#### 🚀 Deployment Process

```bash
# Deploy new version with validation
NEW_VERSION="v1.2.0"
SERVICE="trading-bot"

# 1. Deploy to staging
gcloud run deploy $SERVICE-staging \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/$SERVICE:$NEW_VERSION \
    --region=us-central1 \
    --no-traffic

# 2. Run smoke tests
./scripts/smoke-test.sh $SERVICE-staging

# 3. Gradual rollout
gcloud run services update-traffic $SERVICE \
    --to-revisions=$SERVICE-$NEW_VERSION=10 \
    --region=us-central1

# 4. Monitor metrics, increase traffic
gcloud run services update-traffic $SERVICE \
    --to-revisions=$SERVICE-$NEW_VERSION=50 \
    --region=us-central1

# 5. Complete rollout
gcloud run services update-traffic $SERVICE \
    --to-revisions=$SERVICE-$NEW_VERSION=100 \
    --region=us-central1
```

#### ↩️ Rollback Procedures

```bash
# Quick rollback
gcloud run services update-traffic $SERVICE \
    --to-revisions=$SERVICE-previous=100 \
    --region=us-central1

# List available revisions
gcloud run revisions list --service=$SERVICE --region=us-central1
```

### 🔐 Secret Rotation

#### 🔄 Rotating Secrets Safely

```bash
# 1. Add new secret version
echo -n "new-secret-value" | gcloud secrets versions add $SECRET_NAME --data-file=-

# 2. Update services to use new version
gcloud run services update $SERVICE \
    --update-secrets=$SECRET_NAME=projects/$PROJECT/secrets/$SECRET_NAME/versions/latest

# 3. Verify services are using new version
gcloud run services describe $SERVICE --region=us-central1 | grep $SECRET_NAME

# 4. Disable old version
gcloud secrets versions disable 1 --secret=$SECRET_NAME
```

### 📅 Scheduled Jobs

#### ⏰ Automated Tasks

| Job | Schedule | Service | Description |
|-----|----------|---------|-------------|
| **Daily P&L Calculation** | 16:30 ET Daily | Report Worker | Calculate and store daily P&L |
| **Monthly Report Generation** | 00:10 ET 1st of Month | Report Worker | Generate monthly reports |
| **Commission Email Reports** | 09:00 UTC Monday | Report Worker | Email weekly commission reports |
| **Database Backup** | 02:00 UTC Daily | MongoDB/PostgreSQL | Automated backup to GCS |

#### 📧 Commission Email Job Configuration

**Cron Schedule:**
```bash
# Weekly commission report emails (Monday 9AM UTC)
0 9 * * 1 cd /app && python app/cron_email_reports.py
```

**Manual Execution:**
```bash
# Run commission email job manually
docker exec -it spreadpilot-report-worker python app/cron_email_reports.py

# Check job logs
docker logs spreadpilot-report-worker | grep "commission report"
tail -f /var/log/commission_reports.log
```

**Monitoring Email Jobs:**
```bash
# Check pending reports
psql -U postgres -d spreadpilot_pnl -c "
SELECT follower_id, year, month, commission_amount 
FROM commission_monthly 
WHERE sent = false AND is_payable = true;"

# Check recently sent reports
psql -U postgres -d spreadpilot_pnl -c "
SELECT follower_id, sent_at, commission_amount 
FROM commission_monthly 
WHERE sent = true 
ORDER BY sent_at DESC 
LIMIT 10;"
```

## 🔍 Troubleshooting

### 🚫 Common Issues

#### 🤖 Trading Bot Not Executing Orders

**Symptoms:**
- ❌ No new orders in logs
- ⚠️ Signals processed but not executed
- 📊 Dashboard shows stale data

**Diagnosis & Resolution:**
```bash
# 1. Check IB Gateway connection
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    https://trading-bot-url/health | jq '.ib_gateway'

# 2. Verify Google Sheets access
gcloud logging read 'jsonPayload.operation="fetch_signals"' --limit=10

# 3. Check trading hours
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    https://trading-bot-url/api/v1/market-status

# 4. Force reconnection if needed
curl -X POST -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    https://trading-bot-url/api/v1/reconnect
```

#### 👁️ Watchdog Service Issues

**Monitoring Watchdog Health:**
```bash
# Check watchdog status
docker logs spreadpilot-watchdog --tail 50

# Monitor service failures
docker logs spreadpilot-watchdog | grep "consecutive failures"

# Check alert storage
mongo spreadpilot_admin --eval "db.alerts.find({}).sort({timestamp: -1}).limit(10)"
```

**Common Issues & Resolution:**

**1. False Positives (Unnecessary restarts):**
```bash
# Adjust environment variables
docker-compose stop watchdog
export CHECK_INTERVAL_SECONDS=30  # Increase from 15
export MAX_CONSECUTIVE_FAILURES=5  # Increase from 3
export HEALTH_CHECK_TIMEOUT=10    # Increase from 5
docker-compose up -d watchdog
```

**2. Docker Socket Permission Issues:**
```bash
# Check Docker socket access
docker exec spreadpilot-watchdog docker ps

# Fix permissions if needed
docker exec spreadpilot-watchdog chmod 666 /var/run/docker.sock
```

**3. Service Not Being Monitored:**
```bash
# Verify health endpoint
docker exec spreadpilot-watchdog curl http://trading-bot:8080/health

# Check network connectivity
docker exec spreadpilot-watchdog ping trading-bot
```

#### 📊 Report Generation Failures

**Debug Checklist:**
```bash
# 1. Check MongoDB connectivity
docker-compose exec report-worker python -c "from app.db import test_connection; test_connection()"

# 2. Verify SendGrid quota
curl -H "Authorization: Bearer $SENDGRID_API_KEY" \
    https://api.sendgrid.com/v3/stats

# 3. Test report generation manually
gcloud pubsub topics publish daily-reports \
    --message='{"job_type": "daily", "test": true}'

# 4. Check PDF generation
docker-compose exec report-worker python -m app.utils.pdf --test
```

### 🔬 Diagnostic Tools

#### 🏥 Health Check Script

```bash
#!/bin/bash
# comprehensive-health-check.sh

SERVICES=("trading-bot" "admin-api" "watchdog" "report-worker" "alert-router")

for service in "${SERVICES[@]}"; do
    echo "Checking $service..."
    HEALTH=$(curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
        https://$service-url/health)
    
    if [[ $(echo $HEALTH | jq -r '.status') == "healthy" ]]; then
        echo "✅ $service is healthy"
    else
        echo "❌ $service is unhealthy: $HEALTH"
    fi
done
```

#### 📊 Performance Profiling

```python
# Add to any service for profiling
import cProfile
import pstats

def profile_operation():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your operation here
    process_signals()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

## ⚡ Performance Tuning

### 🎯 Resource Optimization

#### 📊 Service Resource Allocation

```bash
# Analyze current usage
gcloud monitoring read-time-series \
    --filter='metric.type="run.googleapis.com/container/cpu/utilizations"' \
    --interval-start-time=2024-01-01T00:00:00Z

# Optimize based on usage patterns
gcloud run services update trading-bot \
    --memory=4Gi \
    --cpu=2 \
    --min-instances=2 \
    --max-instances=10 \
    --concurrency=100 \
    --region=us-central1
```

#### 🔧 Performance Best Practices

1. **Connection Pooling**
   ```python
   # MongoDB connection pool
   client = AsyncIOMotorClient(
       MONGODB_URL,
       maxPoolSize=50,
       minPoolSize=10,
       maxIdleTimeMS=30000
   )
   ```

2. **Caching Strategy**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_follower_config(follower_id: str):
       # Cached for performance
       return db.followers.find_one({"_id": follower_id})
   ```

3. **Batch Operations**
   ```python
   # Batch position updates
   async def update_positions_batch(updates: List[PositionUpdate]):
       operations = [
           UpdateOne(
               {"_id": u.position_id},
               {"$set": u.dict()}
           ) for u in updates
       ]
       await db.positions.bulk_write(operations)
   ```

## 🔒 Security

### 🛡️ Security Operations

#### 🔍 Daily Security Tasks

1. **Run vulnerability scan**:
   ```bash
   ./trivy_scan.sh --severity CRITICAL,HIGH
   ```

2. **Review security alerts**:
   ```bash
   docker-compose logs alert-router | grep SECURITY_AUDIT
   ```

3. **Check PIN verification logs**:
   ```bash
   docker-compose logs admin-api | grep "PIN verified\|locked out"
   ```

#### 📋 Security Checklist Verification

Run through the security checklist before deployments:

```bash
# Automated security audit
./scripts/security-utils.py audit

# Manual checklist review
cat security_checklist.md | grep -E "^\- \[ \]"
```

#### 🔑 PIN Management

**Generate new PIN**:
```bash
# Generate secure PIN
./scripts/security-utils.py generate-pin --length 6

# Update PIN in production
export NEW_PIN_HASH=$(./scripts/security-utils.py hash-pin YOUR_NEW_PIN)
gcloud secrets versions add security-pin-hash --data-text="$NEW_PIN_HASH"
```

**Monitor PIN usage**:
```bash
# Check failed PIN attempts
docker-compose logs admin-api | grep "Invalid PIN" | tail -20

# View locked out users
docker-compose exec admin-api python -c "
from app.core.security import locked_users
print(f'Locked users: {locked_users}')
"
```

### 🛡️ Access Control

#### 👥 IAM Best Practices

```bash
# Principle of least privilege
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:trading-bot@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --condition="resource.name.startsWith('projects/$PROJECT/secrets/trading-bot')"

# Regular access review
gcloud projects get-iam-policy $PROJECT --format=json | \
    jq '.bindings[] | select(.members[] | contains("user:"))'
```

#### 🔐 Secret Management

```bash
# Rotate service account keys
gcloud iam service-accounts keys create new-key.json \
    --iam-account=trading-bot@$PROJECT.iam.gserviceaccount.com

# Update secret
gcloud secrets versions add sa-key --data-file=new-key.json

# Delete old key
gcloud iam service-accounts keys delete $OLD_KEY_ID \
    --iam-account=trading-bot@$PROJECT.iam.gserviceaccount.com
```

### 📝 Audit Logging

#### 🔍 Security Monitoring

```bash
# Monitor admin activities
gcloud logging read '
    protoPayload.methodName=~".*Delete.*|.*Update.*|.*Create.*"
    protoPayload.authenticationInfo.principalEmail!~".*gserviceaccount.com"
' --limit=50

# Detect anomalies
gcloud logging read '
    jsonPayload.event="login_attempt"
    jsonPayload.success=false
' --limit=100
```

## 🚨 Disaster Recovery

### 💾 Backup Strategy

#### 🔄 Automated Backup Pipeline

```yaml
# backup-pipeline.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mongodb-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: mongo:6
            command:
            - /bin/bash
            - -c
            - |
              mongodump --uri="$MONGO_URI" --gzip --archive=/tmp/backup.gz
              gsutil cp /tmp/backup.gz gs://$BACKUP_BUCKET/$(date +%Y%m%d_%H%M%S).gz
              # Cleanup old backups
              gsutil ls gs://$BACKUP_BUCKET | sort | head -n -30 | xargs -I {} gsutil rm {}
```

### 🔥 Recovery Procedures

#### 📋 Complete System Recovery

```bash
#!/bin/bash
# disaster-recovery.sh

# 1. Verify backup integrity
gsutil cp gs://$BACKUP_BUCKET/latest.gz /tmp/
mongorestore --gzip --archive=/tmp/latest.gz --dry-run

# 2. Create new environment
gcloud projects create $NEW_PROJECT --name="SpreadPilot DR"
gcloud config set project $NEW_PROJECT

# 3. Enable APIs
APIS=(
    "run.googleapis.com"
    "secretmanager.googleapis.com"
    "cloudscheduler.googleapis.com"
    "pubsub.googleapis.com"
    "monitoring.googleapis.com"
)
for api in "${APIS[@]}"; do
    gcloud services enable $api
done

# 4. Restore secrets
./scripts/restore-secrets.sh

# 5. Deploy services
./scripts/deploy-all-services.sh

# 6. Restore data
mongorestore --uri="$NEW_MONGO_URI" --gzip --archive=/tmp/latest.gz

# 7. Update DNS
gcloud dns record-sets update spreadpilot.com \
    --type=A --ttl=300 --rrdatas=$NEW_IP --zone=$DNS_ZONE

# 8. Verify system
./scripts/comprehensive-health-check.sh
```

## 📊 Compliance and Auditing

### 📜 Regulatory Compliance

#### 🗄️ Data Retention Policies

```javascript
// MongoDB TTL indexes for compliance
db.audit_logs.createIndex(
    { "timestamp": 1 },
    { expireAfterSeconds: 7776000 }  // 90 days
)

db.trade_history.createIndex(
    { "executed_at": 1 },
    { expireAfterSeconds: 31536000 }  // 365 days
)
```

#### 🔍 Audit Trail Requirements

```python
# Comprehensive audit logging
async def log_audit_event(
    user: str,
    action: str,
    resource: str,
    details: dict,
    ip_address: str
):
    await db.audit_logs.insert_one({
        "timestamp": datetime.utcnow(),
        "user": user,
        "action": action,
        "resource": resource,
        "details": details,
        "ip_address": ip_address,
        "session_id": get_session_id(),
        "request_id": get_request_id()
    })
```

### 🛡️ Security Auditing

#### 🔍 Vulnerability Management

```bash
# Container scanning
gcloud container images scan IMAGE_URL

# View vulnerabilities
gcloud container images describe IMAGE_URL \
    --show-package-vulnerability

# Automated scanning in CI/CD
- name: 'gcr.io/cloud-builders/docker'
  entrypoint: 'bash'
  args:
  - '-c'
  - |
    docker build -t IMAGE_URL .
    gcloud container images scan IMAGE_URL
    gcloud container images describe IMAGE_URL \
        --show-package-vulnerability \
        --format='value(package_vulnerability.summary.critical)' > critical_count.txt
    if [ $(cat critical_count.txt) -gt 0 ]; then
        echo "Critical vulnerabilities found!"
        exit 1
    fi
```

## 🎯 Quick Reference

### 🛠️ Essential Commands

```bash
# Service Management
gcloud run services list --region=us-central1
gcloud run services describe SERVICE --region=us-central1
gcloud run services update SERVICE --tag=staging --no-traffic

# Monitoring
gcloud logging read "severity>=ERROR" --limit=50 --format=json
gcloud monitoring dashboards list
gcloud alpha monitoring policies list

# Secrets
gcloud secrets list
gcloud secrets versions list SECRET_NAME
gcloud secrets versions access latest --secret=SECRET_NAME

# Pub/Sub
gcloud pubsub topics list
gcloud pubsub subscriptions list
gcloud pubsub topics publish TOPIC --message='{"test": true}'

# Quick Diagnostics
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://SERVICE_URL/health
gcloud logging tail "resource.labels.service_name=SERVICE" --format=json
```

### 📊 Service Matrix

| Service | Port | Health | Metrics | Dependencies |
|---------|------|--------|---------|--------------|
| trading-bot | 8081 | `/health` | `/metrics` | IB Gateway, MongoDB, Sheets |
| admin-api | 8082 | `/health` | `/metrics` | MongoDB, trading-bot |
| watchdog | 8083 | `/health` | `/metrics` | All services |
| report-worker | 8084 | `/health` | `/metrics` | MongoDB, SendGrid |
| alert-router | 8085 | `/health` | `/metrics` | Telegram, SendGrid |

### 🚨 Emergency Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| Primary On-Call | oncall@spreadpilot.com | PagerDuty |
| Infrastructure Lead | infra@spreadpilot.com | Slack: #infra-urgent |
| Security Team | security@spreadpilot.com | 24/7 Hotline |
| Database Admin | dba@spreadpilot.com | PagerDuty |

### 📈 KPI Targets

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Uptime | 99.9% | <99.5% |
| API Latency (p95) | <500ms | >1000ms |
| Error Rate | <0.1% | >1% |
| Order Success Rate | >99% | <95% |
| Report Delivery | 100% | Any failure |

## 📚 Additional Resources

- [System Architecture](./01-system-architecture.md)
- [Development Guide](./03-development-guide.md)
- [API Documentation](./api/)
- [Runbook Repository](./runbooks/)
- [Incident Response Plan](./incident-response.md)