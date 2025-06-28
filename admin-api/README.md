# 🎛️ SpreadPilot Admin API

> 🚀 **Powerful backend service** that provides RESTful endpoints and real-time WebSocket updates for the SpreadPilot admin dashboard

The Admin API serves as the central management hub for SpreadPilot, offering comprehensive follower management, real-time monitoring, and secure authentication with JWT tokens.

## ✨ Features

### 🔐 **Authentication & Security**
- 🔑 **JWT Authentication**: Secure token-based authentication
- 🔒 **Bcrypt Password Hashing**: Industry-standard password security
- 👤 **Role-based Access**: Admin user management
- 🛡️ **CORS Protection**: Configurable cross-origin security

### 👥 **Follower Management**
- ➕ **CRUD Operations**: Complete follower lifecycle management
- 🔄 **Real-time Updates**: Live follower status and data
- 📊 **Position Tracking**: Current trading positions per follower
- 💰 **P&L Monitoring**: Real-time profit/loss calculations

### ⚡ **Real-time Features**
- 🔌 **WebSocket Support**: Live dashboard updates
- 📊 **Live Data Streaming**: Real-time follower and trading data
- 🔔 **Event Broadcasting**: System alerts and notifications
- 📈 **Dashboard Integration**: Seamless frontend connectivity

### 🗄️ **Data Management**
- 🍃 **MongoDB Integration**: Async database operations with Motor
- 📊 **FastAPI Framework**: High-performance async API
- 🎯 **RESTful Design**: Clean, predictable API endpoints
- 📝 **Auto Documentation**: Built-in Swagger/OpenAPI docs

---

## 🌐 Production Deployment with Traefik

The Admin API includes a dedicated `admin_api.py` module optimized for production deployment with Traefik reverse proxy:

### 🔧 **Features**
- 🔐 **JWT Authentication**: Full JWT security implementation
- 🏥 **Health Checks**: Multiple health endpoints for monitoring
- 🌐 **CORS Support**: Pre-configured for cross-origin requests
- 📊 **OpenAPI Docs**: Available at `/docs` and `/redoc`

### 🚀 **Deployment**
```bash
# Using docker-compose with Traefik
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d

# Or use the helper script
./scripts/start-with-traefik.sh
```

### 🔗 **Traefik Configuration**
- **Host Rule**: `Host(\`dashboard.${DOMAIN}\`)`
- **Port**: 8002 (configurable via `ADMIN_API_PORT`)
- **Health Check**: `/health` endpoint
- **Load Balancer**: Automatic with health monitoring

---

## 🚀 API Endpoints

### 🔐 **Authentication**

| Method | Endpoint | Description |
|--------|----------|-------------|
| 🔓 POST | `/api/v1/auth/token` | Authenticate and get JWT token |
| 🔍 GET | `/api/v1/auth/me` | Get current user information |

### 👥 **Follower Management**

| Method | Endpoint | Description |
|--------|----------|-------------|
| 📋 GET | `/api/v1/followers` | List all followers |
| ➕ POST | `/api/v1/followers` | Create new follower |
| 👁️ GET | `/api/v1/followers/{id}` | Get specific follower |
| ✏️ PUT | `/api/v1/followers/{id}` | Update follower |
| 🗑️ DELETE | `/api/v1/followers/{id}` | Delete follower |
| 🔄 POST | `/api/v1/followers/{id}/toggle` | Enable/disable follower |

### 📊 **Trading Operations**

| Method | Endpoint | Description |
|--------|----------|-------------|
| 📈 GET | `/api/v1/positions` | Get all positions |
| 📊 GET | `/api/v1/positions/{follower_id}` | Get follower positions |
| ❌ POST | `/api/v1/close/{follower_id}` | Close follower positions |

### 🔌 **Real-time Data**

| Method | Endpoint | Description |
|--------|----------|-------------|
| 🌐 WS | `/api/v1/ws/dashboard` | WebSocket for real-time updates |

---

## 📋 API Examples

### 🔓 Authentication

```bash
# Get JWT token
curl -X POST "http://localhost:8002/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"

# Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### 👥 Follower Management

```bash
# List all followers
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8002/api/v1/followers"

# Create new follower
curl -X POST "http://localhost:8002/api/v1/followers" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "trader@example.com",
    "iban": "DE12345678901234567890",
    "commission_pct": 20.0,
    "active": true
  }'

# Toggle follower status
curl -X POST "http://localhost:8002/api/v1/followers/follower123/toggle" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 🔌 WebSocket Connection

```javascript
// Connect to real-time updates
const ws = new WebSocket('ws://localhost:8002/api/v1/ws/dashboard');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
};

ws.onopen = function() {
  console.log('Connected to dashboard updates');
};
```

---

## 🛠️ Development Setup

### 📋 Prerequisites

- 🐍 **Python 3.9+** - Runtime environment
- 🍃 **MongoDB** - Database storage
- 🐳 **Docker & Docker Compose** - Containerization
- 🔧 **Make** - Build automation (optional)

### ⚙️ Environment Configuration

Create a `.env` file with these variables:

```bash
# 🍃 MongoDB Configuration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password
MONGO_DB_NAME=spreadpilot_admin
MONGO_URI=mongodb://admin:password@localhost:27017

# 🔐 Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=your_bcrypt_hash
JWT_SECRET=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 🌐 CORS & Networking
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
API_PORT=8002

# 📝 Logging
LOG_LEVEL=INFO
```

### 🔑 Password Hash Generation

Generate a secure password hash:

```bash
# Using the built-in script
python generate_hash.py your_admin_password

# Or manually with Python
python -c "
import bcrypt
password = 'your_password'
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(hashed.decode('utf-8'))
"
```

---

## 🏃‍♂️ Running the Service

### 🐳 Docker Compose (Recommended)

```bash
# 🚀 Start all services
docker-compose up -d

# 📋 Check service status
docker-compose ps

# 📄 View logs
docker-compose logs admin-api

# 🧹 Clean up
docker-compose down
```

### 🔧 Local Development

```bash
# 1️⃣ Install dependencies
pip install -e ../spreadpilot-core
pip install -r requirements.txt

# 2️⃣ Set up environment
cp .env.template .env
# Edit .env with your configuration

# 3️⃣ Start MongoDB (if not using Docker)
mongod --dbpath ./data

# 4️⃣ Run the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

### 🎯 Service Access Points

- 📖 **API Documentation**: http://localhost:8002/docs
- 🔄 **ReDoc Documentation**: http://localhost:8002/redoc
- 🔍 **Health Check**: http://localhost:8002/health
- 📊 **Metrics**: http://localhost:8002/metrics

---

## 🧪 Testing & Development

### 🧪 Running Tests

```bash
# 🧪 All tests
pytest

# ⚡ Unit tests only
pytest tests/unit/

# 🔗 Integration tests
pytest tests/integration/

# 📊 Coverage report
pytest --cov=app --cov-report=html

# 🔍 Verbose output
pytest -v
```

### 🎨 Code Quality

```bash
# 🎨 Format code
black app/ tests/

# 📏 Linting
flake8 app/ tests/

# 🔍 Type checking
mypy app/

# 📋 Sort imports
isort app/ tests/
```

### 🐛 Debugging

```bash
# 📄 View detailed logs
docker logs admin-api

# 🔍 Debug mode
LOG_LEVEL=DEBUG uvicorn app.main:app --reload

# 🍃 Test MongoDB connection
python -c "
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test_db():
    client = AsyncIOMotorClient('mongodb://admin:password@localhost:27017')
    result = await client.admin.command('ping')
    print('MongoDB connected:', result)

asyncio.run(test_db())
"
```

---

## 🔌 WebSocket Integration

### 📊 Real-time Dashboard Updates

The WebSocket endpoint provides live updates for:

- 👥 **Follower Status Changes**: Enable/disable, configuration updates
- 📊 **Trading Data**: New positions, P&L updates, trade executions
- 🔔 **System Alerts**: Error notifications, health status changes
- 📈 **Performance Metrics**: Real-time system statistics

### 🛠️ WebSocket Message Format

```json
{
  "type": "follower_update",
  "data": {
    "follower_id": "follower123",
    "active": true,
    "last_trade": "2024-12-28T15:30:00Z"
  },
  "timestamp": "2024-12-28T15:30:05Z"
}
```

### 📋 Supported Message Types

- 📊 `follower_update` - Follower status changes
- 💰 `pnl_update` - P&L calculations
- 📈 `position_update` - Trading position changes
- 🔔 `alert` - System alerts and notifications
- 💓 `heartbeat` - Connection health checks

---

## 🚀 Production Deployment

### ☁️ Google Cloud Platform

```bash
# 🏗️ Build for Cloud Run
docker build -t gcr.io/your-project/admin-api:latest .

# 📤 Push to registry
docker push gcr.io/your-project/admin-api:latest

# 🚀 Deploy to Cloud Run
gcloud run deploy admin-api \
  --image gcr.io/your-project/admin-api:latest \
  --platform managed \
  --port 8002 \
  --allow-unauthenticated
```

### 🔐 Security Considerations

- 🔑 Use strong JWT secrets in production
- 🛡️ Configure CORS origins appropriately
- 🔒 Enable HTTPS with proper TLS certificates
- 📊 Monitor API usage and implement rate limiting
- 🔐 Rotate secrets regularly
- 📋 Use environment-specific configurations

---

## 🔧 Troubleshooting

### 🍃 **MongoDB Connection Issues**

```bash
# ✅ Test MongoDB connection
mongosh mongodb://admin:password@localhost:27017

# ✅ Check MongoDB logs
docker logs mongodb

# ✅ Verify user permissions
mongosh --eval "db.adminCommand('listUsers')"
```

### 🔐 **Authentication Problems**

- ✅ Verify password hash generation
- ✅ Check JWT secret configuration
- ✅ Validate token expiration settings
- ✅ Test login endpoints manually

### 🔌 **WebSocket Issues**

- ✅ Check CORS configuration
- ✅ Verify WebSocket endpoint path
- ✅ Test connection with WebSocket client tools
- ✅ Monitor connection logs

### 📞 **Getting Help**

- 📄 Check logs: `docker logs admin-api`
- 🔍 Enable debug: `LOG_LEVEL=DEBUG`
- 📖 API docs: http://localhost:8002/docs
- 🧪 Test endpoints with Swagger UI

---

## 🎯 Key Features

### ⚡ **High Performance**
- 🚀 FastAPI async framework
- 🔄 Async MongoDB operations
- 📊 Efficient data serialization
- ⚡ Connection pooling

### 🛡️ **Security**
- 🔐 JWT token authentication
- 🔒 Bcrypt password hashing
- 🛡️ CORS protection
- 📋 Input validation

### 📊 **Monitoring**
- 📈 Prometheus metrics
- 📄 Structured logging
- 🔍 Health check endpoints
- 🎯 Performance tracking

---

<div align="center">

**🎛️ Powering SpreadPilot administration with modern API architecture**

[📖 API Docs](http://localhost:8002/docs) • [🔌 WebSocket Guide](./docs/websockets.md) • [🔐 Auth Guide](./docs/authentication.md)

</div>