# Email Preview Mode with MailHog

Email Preview Mode captures and displays all outgoing emails in a web interface instead of actually sending them. This is perfect for local development and testing.

## Overview

**MailHog** is an email testing tool that:
- Captures SMTP emails
- Displays them in a web UI
- Requires no configuration or credentials
- Works completely offline

**Web UI**: http://localhost:8025
**SMTP Server**: localhost:1025

---

## Quick Start

### Option 1: Development Profile (Recommended)

Start services with MailHog enabled:

```bash
# Start with dev profile (includes MailHog)
docker-compose --profile dev up -d

# Check MailHog is running
docker ps | grep mailhog

# Access web UI
open http://localhost:8025
```

### Option 2: E2E Testing (Already Configured)

MailHog is automatically included in E2E tests:

```bash
# Run E2E tests (MailHog starts automatically)
docker-compose -f docker-compose.e2e.yml up

# Access MailHog UI during tests
open http://localhost:8025
```

---

## Configuration

### Services Using Email

Configure these services to use MailHog in development:

#### Trading Bot

```bash
# Environment variables
SENDGRID_API_KEY=  # Leave empty or use fake key
SMTP_SERVER=localhost  # Or 'mailhog' in Docker network
SMTP_PORT=1025
SMTP_USE_TLS=false
ADMIN_EMAIL=admin@spreadpilot.local
```

#### Report Worker

```bash
SMTP_SERVER=localhost  # Or 'mailhog' in Docker network
SMTP_PORT=1025
SMTP_USERNAME=test@example.com  # Any value works
SMTP_PASSWORD=password  # Any value works
SMTP_USE_TLS=false
FROM_EMAIL=reports@spreadpilot.local
TO_EMAIL=admin@spreadpilot.local
```

#### Alert Router

```bash
SMTP_SERVER=localhost  # Or 'mailhog' in Docker network
SMTP_PORT=1025
SMTP_USERNAME=test@example.com  # Any value works
SMTP_PASSWORD=password  # Any value works
SMTP_USE_TLS=false
ALERT_EMAIL_FROM=alerts@spreadpilot.local
ALERT_EMAIL_TO=admin@spreadpilot.local
```

### Docker Compose Override (Local Development)

Create `docker-compose.override.yml` for local dev settings:

```yaml
version: '3.8'

services:
  trading-bot:
    environment:
      - SMTP_SERVER=mailhog
      - SMTP_PORT=1025
      - SMTP_USE_TLS=false
      - ADMIN_EMAIL=admin@spreadpilot.local

  report-worker:
    environment:
      - SMTP_SERVER=mailhog
      - SMTP_PORT=1025
      - SMTP_USE_TLS=false
      - FROM_EMAIL=reports@spreadpilot.local

  alert-router:
    environment:
      - SMTP_SERVER=mailhog
      - SMTP_PORT=1025
      - SMTP_USE_TLS=false
      - ALERT_EMAIL_FROM=alerts@spreadpilot.local
```

Then start normally (override is auto-applied):

```bash
docker-compose up -d
```

---

## Using the Web UI

### Accessing MailHog

```bash
# Local machine
http://localhost:8025

# From another container
http://mailhog:8025
```

### Features

**Inbox View**:
- See all captured emails
- Click to view full content
- See HTML and plain text versions
- View email headers

**Search**:
- Search by from, to, subject
- Filter by date

**Delete**:
- Delete individual emails
- Clear all emails

**API Access**:
```bash
# Get all messages (JSON)
curl http://localhost:8025/api/v2/messages

# Get specific message
curl http://localhost:8025/api/v2/messages/{id}

# Delete all messages
curl -X DELETE http://localhost:8025/api/v1/messages
```

---

## Testing Email Flows

### Manual Testing

1. **Start services with MailHog**:
   ```bash
   docker-compose --profile dev up -d
   ```

2. **Open MailHog UI**:
   ```bash
   open http://localhost:8025
   ```

3. **Trigger email** (e.g., create a test alert):
   ```bash
   curl -X POST http://localhost:8083/api/v1/alerts \
     -H "Content-Type: application/json" \
     -d '{"type": "test", "severity": "high", "message": "Test alert"}'
   ```

4. **Check MailHog** - Email should appear immediately

### Automated Testing

MailHog is already configured in E2E tests:

```python
# tests/e2e/test_email.py
import httpx

def test_alert_email_sent():
    # Trigger alert
    response = httpx.post("http://admin-api:8000/api/v1/alerts", ...)

    # Check MailHog received email
    mailhog_response = httpx.get("http://mailhog:8025/api/v2/messages")
    messages = mailhog_response.json()["items"]

    # Verify email content
    assert len(messages) > 0
    assert "Test alert" in messages[0]["Content"]["Body"]
```

---

## Comparison: Production vs Development

| Aspect | Production (SendGrid) | Development (MailHog) |
|--------|----------------------|----------------------|
| **SMTP Server** | smtp.sendgrid.net | localhost:1025 or mailhog:1025 |
| **Authentication** | API key required | None (any credentials work) |
| **TLS** | Required | Disabled |
| **Emails** | Actually sent | Captured locally |
| **Cost** | SendGrid credits | Free |
| **Setup** | API key from SendGrid | `docker-compose up` |
| **Web UI** | SendGrid dashboard | http://localhost:8025 |

---

## Troubleshooting

### MailHog not starting

```bash
# Check if port 1025 or 8025 is in use
lsof -i :1025
lsof -i :8025

# Check MailHog container logs
docker logs spreadpilot-mailhog

# Restart MailHog
docker-compose --profile dev restart mailhog
```

### Emails not appearing

1. **Verify SMTP configuration**:
   ```bash
   # Check service env vars
   docker exec spreadpilot-trading-bot env | grep SMTP
   ```

2. **Test SMTP connection**:
   ```bash
   # From host
   telnet localhost 1025

   # From container
   docker exec spreadpilot-trading-bot sh -c "nc -zv mailhog 1025"
   ```

3. **Check application logs**:
   ```bash
   # Look for email sending attempts
   docker logs spreadpilot-trading-bot | grep -i "email\|smtp"
   ```

### MailHog UI not accessible

```bash
# Check MailHog is running
docker ps | grep mailhog

# Check port mapping
docker port spreadpilot-mailhog

# Try direct container access
docker exec spreadpilot-mailhog wget -O- http://localhost:8025
```

---

## Production Deployment

**Important**: MailHog should **NOT** be used in production!

**Production checklist**:
- ✅ Remove `--profile dev` flag
- ✅ Configure real SMTP credentials (SendGrid API key)
- ✅ Enable TLS (`SMTP_USE_TLS=true`)
- ✅ Use production email addresses
- ✅ MailHog service won't start (it's dev-only)

**Production environment**:
```bash
SENDGRID_API_KEY=SG.real_key_here
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
ADMIN_EMAIL=actual@email.com
```

---

## Benefits

1. **No Spam**: Won't accidentally send test emails to real users
2. **No Credentials**: No need for SendGrid API key during development
3. **Offline**: Works without internet connection
4. **Fast**: Instant email capture (no network delays)
5. **Debugging**: See exact email content and headers
6. **Testing**: Automate email verification in tests

---

## Additional Resources

- **MailHog GitHub**: https://github.com/mailhog/MailHog
- **Docker Hub**: https://hub.docker.com/r/mailhog/mailhog
- **API Documentation**: https://github.com/mailhog/MailHog/blob/master/docs/API.md

---

**Related**:
- E2E Testing: `docker-compose.e2e.yml` (MailHog already configured)
- Production Email: Uses SendGrid (configured via env vars)
- Alert Emails: Implemented in `trading-bot/app/service/alerts.py`
- Report Emails: Implemented in `report-worker/`
