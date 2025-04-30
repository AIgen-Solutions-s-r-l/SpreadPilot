# SpreadPilot Operations Guide

This guide provides instructions for monitoring, maintaining, and troubleshooting the SpreadPilot system in production.

## Monitoring

### Cloud Monitoring

SpreadPilot uses Google Cloud Monitoring for observability. The system is instrumented with OpenTelemetry to collect metrics, traces, and logs.

#### Accessing Cloud Monitoring

1. Go to the Google Cloud Console: https://console.cloud.google.com
2. Select your project
3. Navigate to **Monitoring** > **Overview**

#### Key Dashboards

The following dashboards are available in Cloud Monitoring:

1. **SpreadPilot Overview**: High-level system health and key metrics
2. **Trading Bot Performance**: Detailed metrics for the trading bot service
3. **Service Health**: Health status of all services
4. **Error Rates**: Error counts and rates across services

#### Creating Custom Dashboards

To create a custom dashboard:

1. Go to **Monitoring** > **Dashboards**
2. Click **Create Dashboard**
3. Add widgets for the metrics you want to monitor
4. Configure the widgets with appropriate filters and aggregations
5. Save the dashboard

### Grafana

For more advanced visualization, SpreadPilot also includes Grafana dashboards.

#### Accessing Grafana

- **Local Development**: http://localhost:3000
- **Production**: https://grafana.your-domain.com (if configured)

Default credentials:
- Username: admin
- Password: admin (should be changed in production)

#### Key Dashboards

1. **System Overview**: High-level system metrics
2. **Trading Performance**: Trading-related metrics
3. **Service Performance**: Detailed service performance metrics
4. **Error Tracking**: Error rates and patterns

### Logging

SpreadPilot uses structured logging with Cloud Logging integration.

#### Accessing Logs

1. Go to the Google Cloud Console: https://console.cloud.google.com
2. Select your project
3. Navigate to **Logging** > **Logs Explorer**

#### Common Log Queries

**View logs for a specific service:**

```
resource.type="cloud_run_revision"
resource.labels.service_name="trading-bot"
```

**View error logs:**

```
severity>=ERROR
```

**View logs for a specific follower:**

```
jsonPayload.follower_id="FOLLOWER_ID"
```

**View logs for a specific operation:**

```
jsonPayload.operation="execute_order"
```

#### Log Levels

SpreadPilot uses the following log levels:

- **DEBUG**: Detailed debugging information
- **INFO**: General operational information
- **WARNING**: Warning events that might require attention
- **ERROR**: Error events that might still allow the application to continue running
- **CRITICAL**: Critical events that might cause the application to terminate

## Alerting

### Cloud Monitoring Alerts

SpreadPilot uses Cloud Monitoring alerting policies to notify operators of potential issues.

#### Predefined Alerts

1. **Service Availability**: Alerts when any service becomes unavailable
2. **Error Rate**: Alerts when the error rate exceeds a threshold
3. **Trading Bot Health**: Alerts when the trading bot fails health checks
4. **IB Gateway Connection**: Alerts when the connection to IB Gateway is lost
5. **Assignment Detection**: Alerts when an assignment is detected

#### Creating Custom Alerts

To create a custom alert:

1. Go to **Monitoring** > **Alerting**
2. Click **Create Policy**
3. Select the metric to alert on
4. Configure the condition (threshold, duration, etc.)
5. Configure the notification channels
6. Save the policy

### Notification Channels

Alerts can be sent to the following channels:

1. **Email**: Sent to the configured admin email
2. **Telegram**: Sent to the configured Telegram chat
3. **SMS**: Sent to configured phone numbers (if set up)
4. **PagerDuty**: Integrated with PagerDuty for on-call rotation (if set up)

#### Configuring Notification Channels

1. Go to **Monitoring** > **Alerting** > **Notification channels**
2. Click **Add New** for the desired channel type
3. Configure the channel settings
4. Save the channel

## Routine Maintenance

### Backup and Restore

#### MongoDB Backup

Backup strategies for MongoDB depend on the deployment:

*   **Local Docker (`docker-compose.yml`):** Data is stored in a Docker volume (e.g., `spreadpilot_mongo_data`). Backups can be performed by:
    *   Stopping the container (`docker-compose stop mongo`).
    *   Copying the volume data (`docker cp mongo:/data/db ./backup_folder`) or using volume backup tools.
    *   Using `mongodump` from within the container or another container linked to the same network:
        ```bash
        # Example: Run mongodump inside the container
        docker-compose exec mongo mongodump --out /backup/$(date +%Y-%m-%d)
        # Then copy the backup out of the container
        docker cp mongo:/backup ./host_backup_location
        ```
*   **Managed Service (e.g., MongoDB Atlas):** Use the backup features provided by the service (e.g., scheduled snapshots, point-in-time recovery). Refer to the Atlas documentation.
*   **Self-Hosted Production:** Implement regular `mongodump` backups stored securely (e.g., to cloud storage).

To restore from a backup:

```bash
# Restore MongoDB data from backup
# For mongodump backups:
mongorestore --drop /path/to/backup/YYYY-MM-DD

# For Docker volume copies, restore the volume data.
# For managed services, use their restore procedures.
```

### Service Updates

#### Updating Services

To update a service to a new version:

```bash
# Deploy a new version of a service
gcloud run deploy trading-bot \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/trading-bot:NEW_VERSION \
    --region=us-central1
```

#### Rolling Back Services

To roll back a service to a previous version:

```bash
# List revisions
gcloud run revisions list --service=trading-bot --region=us-central1

# Roll back to a specific revision
gcloud run services update-traffic trading-bot \
    --to-revisions=trading-bot-00001-abc=100 \
    --region=us-central1
```

### Secret Rotation

#### Rotating Secrets

To rotate a secret in Secret Manager:

```bash
# Add a new version of a secret
gcloud secrets versions add ib-password --data-file=./new-ib-password.txt
```

After rotating a secret, you may need to restart the affected services to pick up the new value.

## Troubleshooting

### Common Issues

#### Trading Bot Not Executing Orders

**Symptoms:**
- No new orders are being executed
- Log messages indicate signal processing but no order execution

**Possible Causes:**
1. Connection to IB Gateway lost
2. Google Sheets API rate limiting
3. Invalid trading signals

**Resolution Steps:**
1. Check IB Gateway connection status in logs
2. Verify Google Sheets API quota and usage
3. Validate trading signals in the Google Sheet
4. Restart the trading bot service if necessary

#### Watchdog False Positives

**Symptoms:**
- Watchdog reports services as unhealthy when they are functioning correctly
- Unnecessary service restarts

**Possible Causes:**
1. Health check timeout too short
2. Network latency between services
3. Temporary service overload

**Resolution Steps:**
1. Adjust health check timeout in watchdog configuration
2. Check network latency between services
3. Increase resources for affected services

#### Report Generation Failures

**Symptoms:**
- Reports not being generated or sent
- Error logs in report-worker service

**Possible Causes:**
1. Missing or invalid position data
2. SendGrid API issues
3. PDF generation errors

**Resolution Steps:**
1. Check MongoDB for position data integrity (using `mongosh` or a GUI tool)
2. Verify SendGrid API key and quota
3. Check report-worker logs for specific errors
4. Manually trigger report generation for testing

#### Alert Routing Failures

**Symptoms:**
- Alerts not being sent to configured channels
- Error logs in alert-router service

**Possible Causes:**
1. Invalid Telegram bot token or chat ID
2. SendGrid API issues
3. Malformed alert data

**Resolution Steps:**
1. Verify Telegram bot token and chat ID
2. Check SendGrid API key and quota
3. Inspect alert data format in logs
4. Manually trigger test alerts

### Diagnostic Procedures

#### Health Check Endpoints

Each service provides a health check endpoint at `/health` that returns the service status:

```bash
# Check trading-bot health
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://trading-bot-service-url/health
```

#### Service Logs

To view logs for a specific service:

```bash
# View recent logs for trading-bot
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=trading-bot" --limit=50
```

#### Database Inspection

To inspect MongoDB data:

1. Go to the Google Cloud Console: https://console.cloud.google.com
2. Select your project
3. Connect using `mongosh` or a GUI tool (like MongoDB Compass) using the appropriate connection string.
4. Use commands like `use <database_name>`, `db.<collection_name>.find()` to browse data.

#### Manual Testing

To manually test the report generation:

```bash
# Publish a message to the daily-reports topic
gcloud pubsub topics publish daily-reports --message='{"job_type": "daily"}'
```

To manually test the alert router:

```bash
# Publish a message to the alerts topic
gcloud pubsub topics publish alerts --message='{"type": "test", "message": "This is a test alert", "severity": "info"}'
```

### Recovery Procedures

#### Service Recovery

If a service is unresponsive or failing:

```bash
# Restart a service by deploying the same image
gcloud run deploy trading-bot \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/trading-bot:current-version \
    --region=us-central1
```

#### IB Gateway Recovery

If the IB Gateway is unresponsive:

```bash
# Restart the IB Gateway service
gcloud run deploy ib-gateway \
    --image=us-central1-docker.pkg.dev/spreadpilot-prod/spreadpilot/ib-gateway:current-version \
    --region=us-central1
```

#### Database Recovery

If MongoDB data is corrupted or lost:

```bash
# Restore from the most recent backup
gcloud firestore import gs://your-backup-bucket/backups/YYYY-MM-DD
```

## Performance Tuning

### Resource Allocation

#### Adjusting Service Resources

To adjust the resources allocated to a service:

```bash
# Increase memory and CPU for trading-bot
gcloud run services update trading-bot \
    --memory=2Gi \
    --cpu=2 \
    --region=us-central1
```

#### Scaling Configuration

To adjust the scaling configuration for a service:

```bash
# Update min and max instances for trading-bot
gcloud run services update trading-bot \
    --min-instances=2 \
    --max-instances=5 \
    --region=us-central1
```

### Performance Monitoring

#### Key Performance Metrics

1. **Request Latency**: Time taken to process requests
2. **CPU Utilization**: CPU usage percentage
3. **Memory Usage**: Memory consumption
4. **Error Rate**: Percentage of requests resulting in errors
5. **Instance Count**: Number of running instances

#### Performance Dashboards

To view performance metrics:

1. Go to **Monitoring** > **Dashboards**
2. Select the **Service Performance** dashboard

## Security

### Access Control

#### Managing Service Account Permissions

To update service account permissions:

```bash
# Grant additional roles to the service account
gcloud projects add-iam-policy-binding spreadpilot-prod \
    --member="serviceAccount:spreadpilot-sa@spreadpilot-prod.iam.gserviceaccount.com" \
    --role="roles/logging.logWriter"
```

#### Managing User Access

To manage user access to the GCP project:

1. Go to **IAM & Admin** > **IAM**
2. Add or remove users and adjust their roles

### Audit Logging

#### Viewing Audit Logs

To view audit logs:

1. Go to **Logging** > **Logs Explorer**
2. Use the following query:

```
protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"
```

#### Configuring Audit Logging

To configure audit logging:

1. Go to **IAM & Admin** > **Audit Logs**
2. Select the services you want to audit
3. Configure the log types (Admin Activity, Data Access, etc.)

## Disaster Recovery

### Backup Strategy

#### Automated Backups

Set up automated MongoDB backups:
*   **Managed Service:** Configure backup schedules in the service console (e.g., Atlas).
*   **Self-Hosted:** Use `cron` or a similar scheduler to run `mongodump` regularly and upload backups to secure storage.
*   **Local Docker:** Less critical, but can be scripted if needed.

```bash
# Create a Cloud Scheduler job for daily backups
gcloud scheduler jobs create http firestore-backup-daily \
    --schedule="0 0 * * *" \
    --uri="https://firestore.googleapis.com/v1/projects/spreadpilot-prod/databases/(default):exportDocuments" \
    --http-method=POST \
    --oauth-service-account-email=backup-sa@spreadpilot-prod.iam.gserviceaccount.com \
    --message-body="{\"outputUriPrefix\": \"gs://your-backup-bucket/backups/$(date +%Y-%m-%d)\"}" \
    --time-zone="UTC"
```

### Recovery Plan

#### Complete System Recovery

In case of a catastrophic failure:

1. Create a new GCP project if necessary
2. Enable required APIs
3. Set up MongoDB (ensure instance/cluster is running and accessible)
4. Restore MongoDB data from backup
5. Deploy all services from the latest stable images
6. Configure secrets and environment variables
7. Update DNS records if necessary
8. Verify system functionality

## Compliance and Auditing

### Regulatory Compliance

#### Data Retention

Configure MongoDB TTL (Time to Live) Indexes for data that needs to be automatically deleted after a certain period:

```bash
# Set TTL for a collection
gcloud firestore fields ttls create \
    --collection-group=audit-logs \
    --field=timestamp \
    --enable-ttl \
    --ttl-duration=2592000s  # 30 days
```

#### Audit Trails

Ensure comprehensive audit logging is enabled for all services:

1. Go to **IAM & Admin** > **Audit Logs**
2. Enable database auditing features if required (e.g., MongoDB Enterprise auditing, Atlas audit logs) and configure appropriate logging for other critical services. GCP Audit Logs might capture API calls if using a GCP-managed MongoDB, but not internal database operations directly unless configured.

### Security Auditing

#### Vulnerability Scanning

Set up Container Analysis for vulnerability scanning:

```bash
# Enable Container Analysis API
gcloud services enable containeranalysis.googleapis.com

# Configure vulnerability scanning for container images
gcloud container analysis notes create vulnerability-note \
    --note-id=vulnerability-note \
    --type=VULNERABILITY
```

#### Security Monitoring

Set up Security Command Center for security monitoring:

```bash
# Enable Security Command Center API
gcloud services enable securitycenter.googleapis.com

# Configure Security Command Center
gcloud scc settings update \
    --organization=ORGANIZATION_ID \
    --enable-security-center
```

## Appendix

### Useful Commands

#### Service Management

```bash
# List all services
gcloud run services list --platform=managed --region=us-central1

# Get service details
gcloud run services describe trading-bot --region=us-central1

# View service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=trading-bot" --limit=50
```

#### Pub/Sub Management

```bash
# List topics
gcloud pubsub topics list

# List subscriptions
gcloud pubsub subscriptions list

# Publish a message
gcloud pubsub topics publish alerts --message='{"type": "test", "message": "Test alert", "severity": "info"}'
```

#### Secret Management

```bash
# List secrets
gcloud secrets list

# Add a new secret version
gcloud secrets versions add my-secret --data-file=./my-secret.txt

# Access a secret
gcloud secrets versions access latest --secret=my-secret
```

### Reference Architecture

![SpreadPilot Reference Architecture](./images/reference-architecture.png)

### Service Dependencies

| Service | Dependencies |
|---------|---------------|
| trading-bot | IB Gateway, MongoDB, Google Sheets |
| watchdog | trading-bot, IB Gateway, MongoDB |
| admin-api | trading-bot, MongoDB |
| report-worker | MongoDB, SendGrid |
| alert-router | MongoDB, SendGrid, Telegram |
| frontend | admin-api |

### Environment Variables

| Service | Environment Variable | Description |
|---------|----------------------|-------------|
| trading-bot | IB_GATEWAY_HOST | Hostname of the IB Gateway service |
| trading-bot | IB_GATEWAY_PORT | Port of the IB Gateway service |
| trading-bot | GOOGLE_SHEET_URL | URL of the Google Sheet with trading signals |
| watchdog | TRADING_BOT_HOST | Hostname of the trading bot service |
| watchdog | TRADING_BOT_PORT | Port of the trading bot service |
| watchdog | IB_GATEWAY_HOST | Hostname of the IB Gateway service |
| watchdog | IB_GATEWAY_PORT | Port of the IB Gateway service |
| admin-api | TRADING_BOT_HOST | Hostname of the trading bot service |
| admin-api | TRADING_BOT_PORT | Port of the trading bot service |
| admin-api | JWT_SECRET | Secret for JWT authentication |
| report-worker | ADMIN_EMAIL | Email address for admin notifications |
| alert-router | DASHBOARD_URL | URL of the admin dashboard |
| alert-router | ADMIN_EMAIL | Email address for admin notifications |

### Monitoring Metrics

| Metric | Description | Service |
|--------|-------------|--------|
| request_count | Number of requests | All services |
| request_latency | Request processing time | All services |
| error_count | Number of errors | All services |
| cpu_utilization | CPU usage percentage | All services |
| memory_usage | Memory consumption | All services |
| active_connections | Number of active connections | trading-bot |
| order_count | Number of orders executed | trading-bot |
| position_count | Number of open positions | trading-bot |
| follower_count | Number of active followers | trading-bot |
| health_check_status | Health check status | watchdog |
| report_generation_time | Time taken to generate reports | report-worker |
| alert_count | Number of alerts processed | alert-router |
