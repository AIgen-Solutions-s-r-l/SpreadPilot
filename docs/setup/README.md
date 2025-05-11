# SpreadPilot Setup Documentation

This directory contains detailed setup guides for the SpreadPilot trading system. Each component has its own setup guide with step-by-step instructions.

## System Overview

SpreadPilot is an automated trading system that executes vertical spread option trades based on signals from Google Sheets. It consists of several components:

1. **MongoDB**: The central database for storing follower information, positions, trades, and alerts.
2. **IB Gateway**: The connection to Interactive Brokers for executing trades.
3. **Trading Bot**: The core service that polls for signals, executes trades, and monitors positions.
4. **Admin API**: The backend service that provides administrative functionality.
5. **Frontend**: The web-based user interface for monitoring and managing the system.
6. **Watchdog**: A monitoring service that checks the health of other components.
7. **Report Worker**: A service that generates and sends reports to followers.
8. **Alert Router**: A service that routes alerts to administrators via Telegram and email.

## Setup Guides

Follow these guides in order to set up the complete SpreadPilot system:

1. [MongoDB Setup Guide](./0-mongodb.md)
2. [IB Gateway Setup Guide](./1-ib-gateway.md)
3. [Trading Bot Setup Guide](./2-trading-bot.md)
4. [Admin API Setup Guide](./3-admin-api.md)
5. [Frontend Setup Guide](./4-frontend.md)

## Environment Variables

The SpreadPilot system uses environment variables for configuration. These are defined in the `.env` file at the project root. See each component's setup guide for details on the required environment variables.

## Docker Compose

The SpreadPilot system is containerized using Docker and orchestrated using Docker Compose. The `docker-compose.yml` file at the project root defines all the services and their configurations.

To start the entire system:

```bash
docker-compose up -d
```

To start individual components:

```bash
docker-compose up -d [component-name]
```

For example:

```bash
docker-compose up -d mongodb
docker-compose up -d ib-gateway
docker-compose up -d trading-bot
docker-compose up -d admin-api
docker-compose up -d frontend
```

## Troubleshooting

Each setup guide includes a troubleshooting section specific to that component. For general troubleshooting:

1. Check the logs of the relevant container:
   ```bash
   docker logs [container-name]
   ```

2. Verify that all required environment variables are set in the `.env` file.

3. Ensure that dependencies are running before starting dependent services.

4. Check system resources (CPU, memory, disk space).

## Security Considerations

For production environments:

1. Use strong, unique passwords and API keys.
2. Implement proper secrets management.
3. Use HTTPS for all web interfaces.
4. Restrict access to administrative interfaces.
5. Regularly update dependencies to patch security vulnerabilities.
6. Implement monitoring and alerting for system health.
7. Regularly back up the MongoDB database.

## Next Steps

After setting up the SpreadPilot system, refer to the [Operations Guide](../04-operations-guide.md) for information on day-to-day operations, maintenance, and troubleshooting.