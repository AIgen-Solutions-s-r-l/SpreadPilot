# 🗄️ MongoDB Setup Guide for SpreadPilot

This comprehensive guide provides detailed instructions for setting up MongoDB for the SpreadPilot trading system, covering initial setup, configuration, user management, and best practices.

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [MongoDB Configuration](#-mongodb-configuration)
- [Environment Setup](#-environment-setup)
- [Starting MongoDB](#-starting-mongodb)
- [Verification](#-verification)
- [Database Setup](#-database-setup)
- [Troubleshooting](#-troubleshooting)
- [Security Best Practices](#-security-best-practices)
- [Monitoring & Maintenance](#-monitoring--maintenance)

## 🔧 Prerequisites

- **Docker** and **Docker Compose** installed
- Basic understanding of MongoDB concepts
- Access to the SpreadPilot repository
- Terminal/command line access
- At least 2GB free disk space

## 🐳 MongoDB Configuration

### Docker Compose Configuration

The SpreadPilot system uses MongoDB 7.x as its primary database. Here's the configuration in `docker-compose.yml`:

```yaml
mongodb:
  image: mongo:7
  container_name: spreadpilot-mongodb
  environment:
    MONGO_INITDB_ROOT_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
    MONGO_INITDB_ROOT_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
  volumes:
    - mongo_data:/data/db
  ports:
    - "27017:27017" # Expose to host for dev access
  restart: unless-stopped
  healthcheck:
    test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
    interval: 10s
    timeout: 10s
    retries: 5
    start_period: 40s
```

### Configuration Features

| Feature | Description | Purpose |
|---------|-------------|---------|
| **Image** | `mongo:7` | Latest stable MongoDB 7.x version |
| **Container Name** | `spreadpilot-mongodb` | Consistent naming for easy management |
| **Volumes** | `mongo_data:/data/db` | Persistent data storage |
| **Port** | `27017:27017` | Standard MongoDB port exposed for development |
| **Restart Policy** | `unless-stopped` | Automatic recovery from failures |
| **Health Check** | MongoDB ping command | Ensures database availability |

## 🔐 Environment Setup

### 1️⃣ Create Environment File

Create a `.env` file in the project root with MongoDB credentials:

```bash
# MongoDB Root Credentials
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=your_secure_password_here

# Application Database Credentials
MONGODB_DATABASE=spreadpilot
MONGODB_USERNAME=spreadpilot_user
MONGODB_PASSWORD=your_app_password_here
```

### 2️⃣ Generate Secure Passwords

For production environments, generate strong passwords:

```bash
# Generate secure password
openssl rand -base64 32

# Or using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🚀 Starting MongoDB

### 1️⃣ Start MongoDB Container

```bash
# Start MongoDB in detached mode
docker-compose up -d mongodb

# View logs
docker-compose logs -f mongodb
```

### 2️⃣ Wait for Initialization

MongoDB needs time to initialize. Check readiness:

```bash
# Check container status
docker ps --filter name=spreadpilot-mongodb

# Wait for healthy status
while ! docker inspect spreadpilot-mongodb --format='{{.State.Health.Status}}' | grep -q healthy; do
    echo "Waiting for MongoDB to be healthy..."
    sleep 5
done
echo "MongoDB is ready!"
```

## ✅ Verification

### 🔍 Check Container Status

```bash
# View running containers
docker ps | grep mongodb

# Expected output:
# CONTAINER ID   IMAGE     STATUS                    PORTS                      NAMES
# 59e1188004c8   mongo:7   Up 2 minutes (healthy)    0.0.0.0:27017->27017/tcp   spreadpilot-mongodb
```

### 📊 Check Logs

```bash
# View MongoDB logs
docker logs spreadpilot-mongodb --tail 20

# Look for successful initialization:
# "Waiting for connections", "port": 27017
```

### 🔌 Test Connection

```bash
# Test connection using mongosh
docker exec -it spreadpilot-mongodb mongosh --eval "db.adminCommand('ping')"

# Expected output:
# { ok: 1 }
```

## 🗄️ Database Setup

### 1️⃣ Connect as Root User

```bash
docker exec -it spreadpilot-mongodb mongosh \
    --username $MONGO_INITDB_ROOT_USERNAME \
    --password $MONGO_INITDB_ROOT_PASSWORD \
    --authenticationDatabase admin
```

### 2️⃣ Create Application Database and User

Execute the following commands in the MongoDB shell:

```javascript
// Switch to application database
use spreadpilot

// Create application user with specific permissions
db.createUser({
  user: "spreadpilot_user",
  pwd: "your_app_password_here",
  roles: [
    { role: "readWrite", db: "spreadpilot" },
    { role: "dbAdmin", db: "spreadpilot" }
  ]
})

// Create collections with validation
db.createCollection("followers", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["account_id", "status", "created_at"],
      properties: {
        account_id: { bsonType: "string" },
        status: { enum: ["active", "paused", "inactive"] }
      }
    }
  }
})

db.createCollection("positions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["follower_id", "symbol", "quantity"]
    }
  }
})

db.createCollection("trades")
db.createCollection("alerts")

// Create indexes for performance
db.followers.createIndex({ "account_id": 1 }, { unique: true })
db.positions.createIndex({ "follower_id": 1, "symbol": 1 })
db.trades.createIndex({ "executed_at": -1 })
db.alerts.createIndex({ "created_at": -1 })

// Verify collections
show collections
```

### 3️⃣ Verify Application User Access

```bash
# Exit root session
exit

# Connect as application user
docker exec -it spreadpilot-mongodb mongosh \
    --username spreadpilot_user \
    --password your_app_password_here \
    --authenticationDatabase spreadpilot \
    spreadpilot

# Test permissions
db.followers.insertOne({ 
    account_id: "TEST001", 
    status: "active", 
    created_at: new Date() 
})

# Verify insert
db.followers.findOne({ account_id: "TEST001" })

# Clean up test data
db.followers.deleteOne({ account_id: "TEST001" })
```

## 🔧 Troubleshooting

### 🚫 Common Issues

#### Authentication Failures

```bash
# Check credentials in .env
cat .env | grep MONGO

# Verify environment variables are loaded
docker-compose config | grep -A5 mongodb

# Reset MongoDB (WARNING: Deletes all data!)
docker-compose down -v mongodb
docker-compose up -d mongodb
```

#### Connection Refused

```bash
# Check if MongoDB is listening
docker exec spreadpilot-mongodb netstat -tlnp | grep 27017

# Check firewall rules
sudo iptables -L | grep 27017

# Test internal connectivity
docker exec spreadpilot-mongodb mongosh --eval "db.adminCommand('ping')"
```

#### Performance Issues

```javascript
// Check current operations
db.currentOp()

// View collection statistics
db.followers.stats()

// Analyze query performance
db.followers.find({ status: "active" }).explain("executionStats")
```

## 🔒 Security Best Practices

### 🛡️ Production Security Checklist

1. **Strong Authentication**
   ```javascript
   // Enable SCRAM-SHA-256
   db.adminCommand({
     setParameter: 1,
     authenticationMechanisms: "SCRAM-SHA-256"
   })
   ```

2. **Network Security**
   ```yaml
   # Restrict port exposure in production
   mongodb:
     ports: []  # Remove port mapping
     networks:
       - internal
   ```

3. **Encryption at Rest**
   ```yaml
   # Add to docker-compose.yml
   command: mongod --enableEncryption --encryptionKeyFile /etc/mongodb-keyfile
   ```

4. **Regular Backups**
   ```bash
   # Automated backup script
   #!/bin/bash
   BACKUP_DIR="/backups/mongodb/$(date +%Y%m%d_%H%M%S)"
   mkdir -p $BACKUP_DIR
   
   docker exec spreadpilot-mongodb mongodump \
     --username $MONGO_USERNAME \
     --password $MONGO_PASSWORD \
     --authenticationDatabase admin \
     --out /dump
   
   docker cp spreadpilot-mongodb:/dump $BACKUP_DIR
   ```

5. **Audit Logging**
   ```javascript
   // Enable audit logging
   db.adminCommand({
     setParameter: 1,
     auditAuthorizationSuccess: true
   })
   ```

## 📊 Monitoring & Maintenance

### 📈 Performance Monitoring

```javascript
// Monitor database statistics
db.serverStatus()

// Check collection sizes
db.stats()

// Monitor active connections
db.serverStatus().connections

// View slow queries
db.setProfilingLevel(1, { slowms: 100 })
db.system.profile.find().limit(5).sort({ ts: -1 }).pretty()
```

### 🧹 Maintenance Tasks

```javascript
// Compact collections (reduces disk usage)
db.runCommand({ compact: "followers" })

// Rebuild indexes
db.followers.reIndex()

// Validate data integrity
db.followers.validate({ full: true })
```

### 📊 Monitoring Script

Create `scripts/monitor-mongodb.sh`:

```bash
#!/bin/bash

echo "=== MongoDB Health Check ==="
docker exec spreadpilot-mongodb mongosh \
  --username $MONGODB_USERNAME \
  --password $MONGODB_PASSWORD \
  --authenticationDatabase spreadpilot \
  --eval '
    const status = db.serverStatus();
    print("Uptime: " + status.uptime + " seconds");
    print("Connections: " + status.connections.current + "/" + status.connections.available);
    print("Operations: " + JSON.stringify(status.opcounters));
    
    const dbStats = db.stats();
    print("Database Size: " + (dbStats.dataSize / 1024 / 1024).toFixed(2) + " MB");
    print("Collections: " + dbStats.collections);
  '
```

## 🎯 Next Steps

After successfully setting up MongoDB:

1. ✅ Configure the [Interactive Brokers Gateway](./1-ib-gateway.md)
2. ✅ Set up the [Trading Bot Service](./2-trading-bot.md)
3. ✅ Configure the [Admin API](./3-admin-api.md)
4. ✅ Set up monitoring with [Watchdog](./4-watchdog.md)

## 📚 Additional Resources

- [MongoDB Documentation](https://docs.mongodb.com/)
- [Docker MongoDB Image](https://hub.docker.com/_/mongo)
- [MongoDB Security Checklist](https://docs.mongodb.com/manual/administration/security-checklist/)
- [MongoDB Performance Tuning](https://docs.mongodb.com/manual/administration/analyzing-mongodb-performance/)