# HashiCorp Vault Integration

This document describes the HashiCorp Vault integration in SpreadPilot for secure credential management.

## Overview

SpreadPilot now supports HashiCorp Vault for storing and retrieving sensitive credentials, particularly IBKR (Interactive Brokers) credentials. This integration provides enhanced security and centralized secret management.

## Configuration

### Environment Variables

Configure Vault integration using the following environment variables:

- `VAULT_ADDR`: Vault server URL (default: `http://vault:8200`)
- `VAULT_TOKEN`: Vault authentication token (default: `dev-only-token`)
- `VAULT_MOUNT_POINT`: KV mount point (default: `secret`)
- `VAULT_ENABLED`: Enable/disable Vault integration (default: `true`)

### Example Configuration

```bash
export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="dev-only-token"
export VAULT_MOUNT_POINT="secret"
export VAULT_ENABLED="true"
```

## Secret Storage Format

IBKR credentials should be stored in Vault using the following format:

### Path Structure
```
secret/ibkr/[strategy_name]
```

### Secret Data Format
```json
{
  "IB_USER": "your_ib_username",
  "IB_PASS": "your_ib_password"
}
```

Alternative key formats are also supported:
```json
{
  "username": "your_ib_username",
  "password": "your_ib_password"
}
```

## Usage Examples

### Storing Credentials in Vault

Using Vault CLI:
```bash
# For original strategy
vault kv put secret/ibkr/original_strategy IB_USER=your_username IB_PASS=your_password

# For vertical spreads strategy  
vault kv put secret/ibkr/vertical_spreads_strategy IB_USER=your_username IB_PASS=your_password

# For follower-specific credentials
vault kv put secret/ibkr/follower_001 IB_USER=follower_username IB_PASS=follower_password
```

### Reading Credentials

The system automatically retrieves credentials from Vault when:
1. Starting IBGateway containers for followers
2. Initializing trading strategies
3. Connecting to IBKR services

## Integration Points

### 1. Trading Bot Configuration (`trading-bot/app/config.py`)

The `Settings` class includes Vault configuration and a method to retrieve IBKR credentials:

```python
settings = Settings()
credentials = settings.get_ibkr_credentials_from_vault("ibkr/vertical_spreads_strategy")
```

### 2. Gateway Manager (`spreadpilot-core/spreadpilot_core/ibkr/gateway_manager.py`)

The `GatewayManager` automatically retrieves credentials when starting IBGateway containers:

```python
gateway_manager = GatewayManager(vault_enabled=True)
# Credentials are automatically retrieved when starting gateways
```

### 3. Trading Service (`trading-bot/app/service/base.py`)

The `TradingService` includes a method to get IBKR credentials with Vault preference:

```python
credentials = trading_service.get_ibkr_credentials("ibkr/strategy_name")
```

## Fallback Behavior

The system maintains backward compatibility by falling back to existing credential storage methods when:

1. Vault is disabled (`vault_enabled=false`)
2. Vault credentials are not found
3. Vault is unreachable or returns errors

## Security Considerations

### Development Environment
- Uses Vault in development mode with the token `dev-only-token`
- Suitable for local development and testing
- Data is not persisted across Vault restarts

### Production Environment
- Use proper Vault seal configuration
- Implement token rotation and proper authentication
- Configure TLS for Vault communication
- Set up proper access policies and role-based access

## Testing

The integration includes comprehensive unit tests with mocked hvac clients:

```bash
# Run Vault-specific tests
pytest tests/unit/test_vault_client.py
pytest tests/unit/test_gateway_manager_vault.py  
pytest tests/unit/test_config_vault.py
```

## Troubleshooting

### Common Issues

1. **Vault Connection Errors**
   - Check `VAULT_ADDR` environment variable
   - Verify Vault service is running
   - Check network connectivity

2. **Authentication Failures**
   - Verify `VAULT_TOKEN` is correct
   - Check token has required permissions
   - Ensure token is not expired

3. **Credentials Not Found**
   - Verify secret path is correct
   - Check mount point configuration
   - Ensure credentials are stored in expected format

### Debug Logging

Enable debug logging to troubleshoot Vault integration:

```python
import logging
logging.getLogger('spreadpilot_core.utils.vault').setLevel(logging.DEBUG)
```

## Migration from Legacy Systems

### From Google Cloud Secret Manager

1. Export existing secrets from Google Cloud Secret Manager
2. Import secrets into Vault using the expected format
3. Update secret references in configuration
4. Test credential retrieval
5. Disable Google Cloud Secret Manager integration

### From Environment Variables

1. Create Vault secrets from environment variables
2. Update configuration to use Vault secret references
3. Remove sensitive environment variables
4. Test the integration

## Infrastructure Integration

The Vault integration works seamlessly with the SpreadPilot infrastructure:

```bash
# Start infrastructure with Vault
cd infra/
./compose-up.sh

# Vault is available at http://localhost:8200
# Credentials are automatically initialized
```

For more information about the infrastructure setup, see `infra/README.md`.