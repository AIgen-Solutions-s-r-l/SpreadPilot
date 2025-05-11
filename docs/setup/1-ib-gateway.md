# Interactive Brokers Gateway Setup Guide for SpreadPilot

This document provides detailed instructions for setting up the Interactive Brokers (IB) Gateway for the SpreadPilot trading system. It covers the configuration, startup, verification, and troubleshooting steps.

## Prerequisites

- Docker and Docker Compose installed on your system
- MongoDB service set up and running (see [MongoDB Setup Guide](./0-mongodb.md))
- Interactive Brokers account (paper trading account is sufficient for development)
- Basic understanding of Interactive Brokers concepts

## 1. Understanding the IB Gateway

The Interactive Brokers Gateway is a standalone application that provides a programmatic interface to the Interactive Brokers trading platform. In the SpreadPilot system, it serves as the bridge between our trading bot and the actual trading platform.

Key points:
- The IB Gateway handles authentication with Interactive Brokers
- It provides API access for placing orders, retrieving account information, and market data
- It maintains the connection to Interactive Brokers servers
- It can operate in paper trading mode for testing without real money

## 2. IB Gateway Configuration in docker-compose.yml

The SpreadPilot system uses a containerized version of the IB Gateway, configured in the `docker-compose.yml` file. Here's the relevant section:

```yaml
ib-gateway:
  image: ghcr.io/gnzsnz/ib-gateway:latest
  container_name: spreadpilot-ib-gateway
  environment:
    - TWS_USERID=${IB_USERNAME}
    - TWS_PASSWORD=${IB_PASSWORD}
    - TRADING_MODE=paper
  ports:
    - "4002:4002"
  restart: unless-stopped
```

This configuration:
- Uses the `ghcr.io/gnzsnz/ib-gateway` image, which is a containerized version of the IB Gateway
- Names the container `spreadpilot-ib-gateway`
- Sets environment variables for IB credentials (loaded from `.env` file)
- Configures paper trading mode (for testing without real money)
- Exposes port 4002 for the IB Gateway API
- Configures automatic restart unless explicitly stopped

## 3. Environment Variables Setup

IB Gateway credentials are stored in the `.env` file at the project root. You need to add:

```
# Interactive Brokers Gateway
IB_USERNAME=your_ib_username
IB_PASSWORD=your_ib_password
```

Replace `your_ib_username` and `your_ib_password` with your actual Interactive Brokers credentials.

### Paper Trading vs. Live Trading

The `TRADING_MODE=paper` environment variable in the docker-compose.yml file configures the IB Gateway to connect to Interactive Brokers' paper trading environment instead of the live trading environment. This is crucial for development and testing.

**Important Paper Trading Notes:**
- You must use credentials for a paper trading account, not your live trading account
- Paper trading accounts have different credentials than live accounts
- You can create a paper trading account at the [Interactive Brokers website](https://www.interactivebrokers.com/en/trading/paper-trading.php)
- Paper trading accounts typically have usernames that start with "paper" or "demo" followed by your account number
- If you're getting authentication errors, verify that:
  - You're using paper trading credentials (not live trading credentials)
  - The account is properly set up and activated
  - You've accepted any required agreements for the paper trading account
  - The account hasn't been locked due to too many failed login attempts

**Other Important Notes:**
- For development and testing, always use a paper trading account
- For production, use a dedicated trading account with appropriate risk controls
- Never commit real credentials to version control
- Consider using a secrets management solution for production environments

## 4. Starting the IB Gateway

To start the IB Gateway container:

```bash
docker-compose up -d ib-gateway
```

This command:
- Starts the IB Gateway in detached mode (`-d`)
- Uses the configuration from `docker-compose.yml`
- Creates and initializes the IB Gateway container with the credentials from `.env`

## 5. Verifying the IB Gateway is Running

Check if the IB Gateway container is running with:

```bash
docker ps | grep ib-gateway
```

You should see output similar to:

```
CONTAINER ID   IMAGE                          COMMAND                  CREATED          STATUS          PORTS                    NAMES
abcdef123456   ghcr.io/gnzsnz/ib-gateway:latest   "/init"                 5 minutes ago    Up 5 minutes    0.0.0.0:4002->4002/tcp   spreadpilot-ib-gateway
```

## 6. Checking IB Gateway Logs

To verify that the IB Gateway is properly connecting to Interactive Brokers:

```bash
docker logs spreadpilot-ib-gateway
```

Look for messages indicating successful connection to Interactive Brokers servers. The exact messages will depend on the specific version of the IB Gateway image, but you should see indications of:
- Successful startup of the IB Gateway
- Connection attempts to Interactive Brokers servers
- Successful login (if credentials are correct)
- No critical errors

## 7. Testing the IB Gateway Connection

The IB Gateway exposes an API on port 4002. You can test this connection using a simple telnet command:

```bash
telnet localhost 4002
```

If the connection is successful, you'll see a blank screen with a cursor. Press Ctrl+C to exit.

For a more comprehensive test, you can use the trading bot's health check endpoint (if implemented) or a simple Python script using the `ib_insync` library:

```python
from ib_insync import IB

ib = IB()
try:
    ib.connect('localhost', 4002, clientId=1)
    print("Successfully connected to IB Gateway")
    print(f"Server Version: {ib.client.serverVersion()}")
    print(f"Connected to TWS: {ib.isConnected()}")
    ib.disconnect()
except Exception as e:
    print(f"Failed to connect: {e}")
```

Save this as `test_ib_connection.py` and run it with Python to verify the connection.

## 8. Troubleshooting

### Authentication Issues

If the IB Gateway fails to authenticate with Interactive Brokers:

1. Verify your credentials in the `.env` file
2. Check if your account has any restrictions or requires additional verification
3. For paper trading accounts, ensure you're using the paper trading credentials (not live trading credentials)
4. Check if your account requires two-factor authentication, which may need special handling
5. If you see "Too many failed login attempts" error:
   - Wait for the specified time period (usually 59 seconds) before trying again
   - Restart the IB Gateway container after waiting: `docker-compose restart ib-gateway`
   - Verify that your paper trading account is active and not locked
6. Paper trading accounts may have different login requirements:
   - Ensure you've completed all registration steps for the paper trading account
   - Check if you need to log in to the Interactive Brokers website first to accept any agreements
   - Some paper trading accounts require a specific format for the username (e.g., "paper123" instead of just "123")

### Connection Issues

If the IB Gateway container starts but doesn't connect to Interactive Brokers:

1. Check the container logs: `docker logs spreadpilot-ib-gateway`
2. Verify your internet connection
3. Check if Interactive Brokers services are experiencing downtime
4. Ensure port 4002 is not blocked by a firewall

### Container Issues

If the IB Gateway container fails to start:

1. Check Docker logs: `docker logs spreadpilot-ib-gateway`
2. Verify the image exists: `docker images | grep ib-gateway`
3. Try pulling the image explicitly: `docker pull ghcr.io/gnzsnz/ib-gateway:latest`
4. Check system resources (CPU, memory, disk space)

## 9. Security Considerations

For production environments:

1. Use a dedicated Interactive Brokers account with appropriate risk controls
2. Implement proper secrets management for IB credentials
3. Consider network isolation for the IB Gateway container
4. Implement monitoring and alerting for the IB Gateway status
5. Regularly audit trading activities and permissions
6. Consider using read-only API access when possible

## 10. Next Steps

After setting up the IB Gateway, you can proceed to configure the Trading Bot, which will interact with the IB Gateway to execute trades.

The Trading Bot will need to be configured with:
- The hostname of the IB Gateway container (`ib-gateway` within the Docker network)
- The port number (4002)
- Client ID for the connection

These settings are typically configured in the Trading Bot's environment variables or configuration files.