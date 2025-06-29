# Admin API Endpoints Documentation

## Overview

The SpreadPilot Admin API provides secure endpoints for managing followers, monitoring P&L, accessing logs, and performing manual operations. All endpoints (except `/health`) require JWT authentication.

## Authentication

### JWT Token

All protected endpoints require a Bearer token in the Authorization header:

```bash
Authorization: Bearer <jwt_token>
```

### Login Endpoint

```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=your_password
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## P&L Endpoints

### Get Today's P&L

```http
GET /api/v1/pnl/today
Authorization: Bearer <token>
```

Response:
```json
{
  "date": "2025-06-29",
  "total_pnl": 1500.50,
  "realized_pnl": 1000.00,
  "unrealized_pnl": 500.50,
  "trades": [
    {
      "symbol": "QQQ",
      "pnl": 1000.00,
      "quantity": 10
    }
  ]
}
```

### Get Monthly P&L

```http
GET /api/v1/pnl/month?year=2025&month=6
Authorization: Bearer <token>
```

Parameters:
- `year` (optional): Year for P&L data (defaults to current year)
- `month` (optional): Month for P&L data (1-12, defaults to current month)

Response:
```json
{
  "year": 2025,
  "month": 6,
  "total_pnl": 5250.75,
  "realized_pnl": 4000.00,
  "unrealized_pnl": 1250.75,
  "daily_breakdown": [
    {
      "date": "2025-06-01",
      "total_pnl": 250.50,
      "realized_pnl": 200.00,
      "unrealized_pnl": 50.50
    }
  ],
  "days_with_data": 20
}
```

## Logs Endpoint

### Get Recent Logs

```http
GET /api/v1/logs/recent?n=100&service=trading-bot&level=ERROR&search=timeout
Authorization: Bearer <token>
```

Query Parameters:
- `n` (optional): Number of log entries (1-1000, default: 200)
- `service` (optional): Filter by service name
- `level` (optional): Filter by log level (INFO, WARNING, ERROR)
- `search` (optional): Search text in log messages

Response:
```json
{
  "count": 2,
  "requested": 100,
  "filters": {
    "service": "trading-bot",
    "level": "ERROR",
    "search": "timeout"
  },
  "logs": [
    {
      "timestamp": "2025-06-29T10:30:00",
      "service": "trading-bot",
      "level": "ERROR",
      "message": "Connection timeout for follower ABC123",
      "extra": {
        "follower_id": "ABC123",
        "retry_count": 3
      }
    }
  ]
}
```

## Manual Operations

### Manual Close Positions

```http
POST /api/v1/manual-close
Authorization: Bearer <token>
Content-Type: application/json

{
  "follower_id": "follower_123",
  "pin": "0312",
  "close_all": true,
  "reason": "Emergency market conditions"
}
```

Request Body:
- `follower_id` (required): ID of the follower
- `pin` (required): Security PIN (must be "0312")
- `close_all` (optional): Close all positions (default: true)
- `position_ids` (optional): Specific positions to close if close_all is false
- `reason` (optional): Reason for manual close

Response:
```json
{
  "success": true,
  "message": "Manual close operation created successfully. Operation ID: 507f1f77bcf86cd799439011",
  "closed_positions": 5,
  "follower_id": "follower_123",
  "timestamp": "2025-06-29T15:30:00Z"
}
```

### Error Responses

#### Invalid PIN (403 Forbidden):
```json
{
  "detail": "Invalid PIN"
}
```

#### Follower Not Found (404):
```json
{
  "detail": "Follower follower_999 not found"
}
```

## Common Features

### Authentication Required

All endpoints except `/health` return 401 Unauthorized if no valid JWT token is provided:

```json
{
  "detail": "Not authenticated"
}
```

### Rate Limiting

The API implements rate limiting to prevent abuse:
- 100 requests per minute per IP
- 1000 requests per hour per authenticated user

### CORS Support

The API supports CORS for browser-based applications. Configure allowed origins in the environment:

```bash
CORS_ORIGINS=http://localhost:3000,https://app.spreadpilot.com
```

## Swagger Documentation

Interactive API documentation is available at:
- Swagger UI: `http://api.spreadpilot.com/docs`
- ReDoc: `http://api.spreadpilot.com/redoc`

## Example Usage

### Python Client

```python
import httpx

# Login
login_data = {"username": "admin", "password": "your_password"}
response = httpx.post("http://api.spreadpilot.com/api/v1/auth/token", data=login_data)
token = response.json()["access_token"]

# Create authenticated client
headers = {"Authorization": f"Bearer {token}"}
client = httpx.Client(headers=headers)

# Get today's P&L
pnl = client.get("http://api.spreadpilot.com/api/v1/pnl/today").json()
print(f"Today's P&L: ${pnl['total_pnl']}")

# Get recent errors
logs = client.get(
    "http://api.spreadpilot.com/api/v1/logs/recent",
    params={"n": 50, "level": "ERROR"}
).json()
print(f"Found {logs['count']} errors")

# Manual close (requires PIN)
close_data = {
    "follower_id": "follower_123",
    "pin": "0312",
    "close_all": True,
    "reason": "Market volatility"
}
result = client.post(
    "http://api.spreadpilot.com/api/v1/manual-close",
    json=close_data
).json()
print(f"Closed {result['closed_positions']} positions")
```

### JavaScript/TypeScript Client

```typescript
// Login
const loginResponse = await fetch('http://api.spreadpilot.com/api/v1/auth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=admin&password=your_password'
});
const { access_token } = await loginResponse.json();

// Setup headers
const headers = { 'Authorization': `Bearer ${access_token}` };

// Get monthly P&L
const pnlResponse = await fetch('http://api.spreadpilot.com/api/v1/pnl/month?year=2025&month=6', {
  headers
});
const monthlyPnl = await pnlResponse.json();
console.log(`Monthly P&L: $${monthlyPnl.total_pnl}`);

// Get logs with search
const logsResponse = await fetch('http://api.spreadpilot.com/api/v1/logs/recent?search=timeout&n=100', {
  headers
});
const logs = await logsResponse.json();
console.log(`Found ${logs.count} logs matching 'timeout'`);
```

## Security Considerations

1. **JWT Expiration**: Tokens expire after 30 minutes by default
2. **PIN Protection**: Manual operations require additional PIN verification
3. **HTTPS Only**: Always use HTTPS in production
4. **IP Whitelisting**: Consider restricting API access by IP in production
5. **Audit Logging**: All manual operations are logged for audit trail