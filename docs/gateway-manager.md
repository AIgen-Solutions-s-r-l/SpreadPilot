# Gateway Manager Documentation

## Overview

The Gateway Manager is a core component of SpreadPilot that automatically manages IBGateway Docker containers for each enabled follower. It provides isolated connections to Interactive Brokers for multiple followers, with automatic port allocation, health monitoring, and retry logic.

## Features

- **Multi-Follower Support**: Automatically creates and manages one IBGateway container per enabled follower
- **Isolated Connections**: Each follower gets their own dedicated IBGateway instance with unique ports and client IDs
- **Automatic Resource Management**: Dynamic port and client ID allocation with conflict resolution
- **Health Monitoring**: Continuous health checks every 30 seconds using `ib_insync.isConnected()`
- **Exponential Backoff**: Retry logic for connection failures with configurable parameters
- **Container Lifecycle Management**: Automatic start, stop, and cleanup of Docker containers
- **Vault Integration**: Secure credential retrieval from HashiCorp Vault with `IB_USER` and `IB_PASS`
- **Graceful Shutdown**: 30-second timeout for container stops with force removal fallback

## Architecture

```
┌─────────────────┐    ┌────────────────────┐    ┌─────────────────┐
│   Trading Bot   │───▶│ Gateway Manager    │───▶│ IBGateway       │
└─────────────────┘    └────────────────────┘    │ (Follower 1)    │
                                │                 │ Port: 4100      │
                                │                 │ Client ID: 1234 │
                                │                 └─────────────────┘
                                │
                                ├─────────────────▶┌─────────────────┐
                                │                 │ IBGateway       │
                                │                 │ (Follower 2)    │
                                │                 │ Port: 4101      │
                                │                 │ Client ID: 5678 │
                                │                 └─────────────────┘
                                │
                                └─────────────────▶┌─────────────────┐
                                                  │ IBGateway       │
                                                  │ (Follower N)    │
                                                  │ Port: 410N      │
                                                  │ Client ID: XXXX │
                                                  └─────────────────┘
```

## Configuration

### Environment Variables

- `GATEWAY_IMAGE`: Docker image for IBGateway (default: `ghcr.io/gnzsnz/ib-gateway:latest`)
- `PORT_RANGE_START`: Start of port range for gateways (default: `4100`)
- `PORT_RANGE_END`: End of port range for gateways (default: `4200`)
- `CLIENT_ID_RANGE_START`: Start of TWS client ID range (default: `1000`)
- `CLIENT_ID_RANGE_END`: End of TWS client ID range (default: `9999`)
- `HEALTHCHECK_INTERVAL`: Interval between health checks in seconds (default: `30`)
- `MAX_STARTUP_TIME`: Maximum container startup time in seconds (default: `120`)
- `VAULT_ENABLED`: Enable Vault integration for credentials (default: `true`)

### Container Environment Variables

Each IBGateway container is started with:
- `IB_USER`: IBKR username (from Vault or follower configuration)
- `IB_PASS`: IBKR password (from Vault or placeholder)
- `TRADING_MODE`: Trading mode (`paper` or `live`)
- `TWS_SETTINGS_PATH`: IBC configuration path
- `DISPLAY`: X display for headless operation

### Initialization Parameters

```python
manager = GatewayManager(
    gateway_image="ghcr.io/gnzsnz/ib-gateway:latest",
    port_range_start=4100,
    port_range_end=4200,
    client_id_range_start=1000,
    client_id_range_end=9999,
    container_prefix="ibgateway-follower",
    healthcheck_interval=30,
    max_startup_time=120,
    vault_enabled=True  # Enable Vault integration
)
```

## Usage

### Starting the Gateway Manager

```python
# Initialize and start the gateway manager
await manager.start()
```

This will:
1. Load all enabled followers from the MongoDB database
2. Start IBGateway containers for each follower
3. Begin health monitoring

### Getting IB Clients

```python
# Get a ready IB client for a follower
ib_client = await manager.get_client('follower-123')
if ib_client:
    # Use the client for trading operations
    positions = await ib_client.reqPositionsAsync()
```

### Managing Followers

```python
# Reload followers from database (adds new, removes disabled)
await manager.reload_followers()

# Get gateway status for a follower
status = manager.get_gateway_status('follower-123')

# List all gateways and their status
gateways = manager.list_gateways()

# Stop a specific follower's gateway
await manager.stop_follower_gateway('follower-123')
```

### Stopping the Gateway Manager

```python
# Stop all gateways and cleanup resources
await manager.stop()
```

## Gateway Lifecycle

### 1. Container Creation
- Allocates unique port and client ID
- Creates Docker container with environment variables
- Sets up port mappings for TWS API access

### 2. Health Monitoring
- Monitors container status every 30 seconds
- Verifies IB client connections using `isConnected()`
- Handles startup timeout detection
- Performs automatic reconnection with exponential backoff
- Updates gateway status based on connection health

### 3. Status Management
Gateway instances can be in one of four states:
- `STARTING`: Container starting up, waiting for IB connectivity
- `RUNNING`: Container and IB connection healthy
- `STOPPED`: Container stopped or not found
- `FAILED`: Container failed to start within timeout

### 4. Resource Cleanup
- Stops and removes Docker containers
- Disconnects IB clients
- Releases allocated ports and client IDs

## Integration

### With Trading Bot

```python
from spreadpilot_core.ibkr.gateway_manager import GatewayManager

class TradingBotService:
    def __init__(self):
        self.gateway_manager = GatewayManager()
    
    async def start(self):
        await self.gateway_manager.start()
    
    async def execute_trade(self, follower_id: str, signal: Dict):
        ib_client = await self.gateway_manager.get_client(follower_id)
        if ib_client:
            # Execute trade with dedicated client
            result = await ib_client.place_vertical_spread(...)
```

### With Admin API

```python
@app.get("/api/v1/gateways")
async def list_gateways():
    """List all gateway instances and their status."""
    return gateway_manager.list_gateways()

@app.post("/api/v1/followers/{follower_id}/reload")
async def reload_follower_gateway(follower_id: str):
    """Reload gateway for a specific follower."""
    await gateway_manager.reload_followers()
```

## Error Handling

### Connection Failures
The Gateway Manager implements exponential backoff retry logic for connection failures:

```python
@backoff.on_exception(
    backoff.expo,
    (ConnectionError, OSError, Exception),
    max_tries=5,
    max_time=60
)
async def _connect_ib_client(self, gateway: GatewayInstance) -> IB:
    # Connection logic with retries
```

### Resource Exhaustion
When all ports or client IDs are allocated:

```python
try:
    port = manager._allocate_port()
except RuntimeError as e:
    # Handle "No available ports" error
    logger.error(f"Port allocation failed: {e}")
```

### Container Failures
Failed containers are detected during health checks and marked as `FAILED`. The gateway manager will attempt to restart them on the next follower reload.

## Monitoring

### Logs
The Gateway Manager provides comprehensive logging:
- Container lifecycle events
- Connection attempts and failures
- Health check results
- Resource allocation/deallocation

### Metrics
Key metrics exposed through OpenTelemetry:
- Active gateway count
- Port allocation efficiency
- Connection failure rates
- Health check status

## Testing

The Gateway Manager includes comprehensive integration tests with mocked components:

```bash
pytest tests/integration/test_gateway_manager.py -v
```

Test coverage includes:
- Follower loading and container creation
- Client connection and echo functionality
- Retry logic with exponential backoff
- Resource allocation and exhaustion handling
- Gateway status management
- Cleanup and resource release

## Security Considerations

### Container Isolation
Each follower's IBGateway runs in an isolated Docker container with:
- Separate network namespaces
- Unique port mappings
- Individual authentication credentials

### Credential Management
IBGateway credentials are managed through:
- HashiCorp Vault integration (primary method)
- Environment variables `IB_USER` and `IB_PASS`
- Follower-specific vault secret references
- Fallback to stored username with placeholder password
- No hardcoded passwords in configuration

### Network Security
- Only necessary ports are exposed from containers
- Containers communicate only with IB servers
- No inter-container communication allowed

## Performance

### Resource Requirements
Per gateway container:
- Memory: ~512MB
- CPU: ~0.1 cores
- Disk: ~100MB

### Scalability
The Gateway Manager can handle:
- Up to 100 concurrent gateway containers (configurable)
- Port ranges of 1000+ ports
- Client ID ranges of 8000+ IDs

### Optimization
- Lazy loading of IB clients
- Connection pooling per follower
- Efficient health check scheduling
- Resource cleanup on follower disable

## Troubleshooting

### Common Issues

#### Gateway Won't Start
```
ERROR: Gateway for follower xyz failed to start within 120s
```
Solutions:
- Check Docker daemon status
- Verify IBGateway image availability
- Increase `max_startup_time` parameter

#### Port Allocation Failed
```
ERROR: No available ports for IBGateway
```
Solutions:
- Increase port range
- Check for port conflicts
- Clean up stopped containers

#### IB Connection Failed
```
ERROR: Failed to connect IB client for follower xyz
```
Solutions:
- Verify IBGateway container is running
- Check IBKR credentials
- Confirm network connectivity

### Debug Commands

```bash
# Check running containers
docker ps | grep ibgateway

# View container logs
docker logs ibgateway-follower-123

# Inspect port usage
netstat -tlnp | grep 410

# Monitor gateway manager logs
docker logs trading-bot | grep "GatewayManager"
```

## API Reference

### GatewayManager Class

#### Constructor
```python
def __init__(
    self,
    gateway_image: str = "ghcr.io/gnzsnz/ib-gateway:latest",
    port_range_start: int = 4100,
    port_range_end: int = 4200,
    client_id_range_start: int = 1000,
    client_id_range_end: int = 9999,
    container_prefix: str = "ibgateway-follower",
    healthcheck_interval: int = 30,
    max_startup_time: int = 120,
    vault_enabled: bool = True
)
```

#### Methods

##### async start() -> None
Starts the gateway manager and loads enabled followers.

##### async stop() -> None
Stops all gateways and cleans up resources.

##### async get_client(follower_id: str) -> Optional[IB]
Returns a ready IB client instance for the specified follower.

##### async reload_followers() -> None
Reloads followers from database and updates gateways accordingly.

##### async stop_follower_gateway(follower_id: str) -> None
Stops the IBGateway container for a specific follower with graceful shutdown.

##### get_gateway_status(follower_id: str) -> Optional[GatewayStatus]
Returns the current status of a gateway for the specified follower.

##### list_gateways() -> Dict[str, dict]
Returns a dictionary of all gateways and their current status.

### GatewayStatus Enum

- `STARTING`: Container is starting up
- `RUNNING`: Container and IB connection are healthy
- `STOPPED`: Container is stopped
- `FAILED`: Container failed to start or connect

### GatewayInstance Dataclass

```python
@dataclass
class GatewayInstance:
    follower_id: str
    container_id: str
    host_port: int
    client_id: int
    status: GatewayStatus
    container: Optional[docker.models.containers.Container] = None
    ib_client: Optional[IB] = None
    last_healthcheck: Optional[float] = None
```