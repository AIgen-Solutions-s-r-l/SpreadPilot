# HashiCorp Vault Migration Guide

This guide explains how to migrate SpreadPilot from environment variable-based secrets to HashiCorp Vault for improved security and centralized secret management.

## Overview

SpreadPilot now supports HashiCorp Vault for managing sensitive configuration data such as:
- Authentication credentials (JWT secrets, admin passwords)
- Database connection strings
- API keys (Google Sheets, SendGrid, Telegram)
- SMTP credentials
- Cloud storage credentials
- IBKR trading credentials

## Benefits of Vault

1. **Centralized Management**: All secrets in one secure location
2. **Access Control**: Fine-grained permissions per service
3. **Audit Trail**: Complete logging of secret access
4. **Secret Rotation**: Easy rotation without service restarts
5. **Dynamic Secrets**: Generate temporary credentials on-demand
6. **Encryption**: All secrets encrypted at rest and in transit

## Prerequisites

1. HashiCorp Vault installed and running
2. Vault initialized and unsealed
3. Authentication token with appropriate permissions
4. SpreadPilot services updated to latest version

## Migration Steps

### 1. Set Up Vault

First, ensure Vault is running and accessible:

```bash
# Start Vault in dev mode (for testing only)
vault server -dev

# For production, use proper configuration
vault server -config=/etc/vault/vault.hcl
```

### 2. Configure Vault Access

Set environment variables for Vault access:

```bash
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="your-vault-token"
```

### 3. Prepare Secrets for Migration

Create a `.env` file with all your current secrets:

```bash
# Authentication
JWT_SECRET=your-jwt-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...
SECURITY_PIN_HASH=$2b$12$...

# Database
MONGO_URI=mongodb://username:password@localhost:27017
DATABASE_URL=postgresql://user:pass@localhost:5432/spreadpilot
REDIS_URL=redis://:password@localhost:6379

# External APIs
GOOGLE_SHEETS_API_KEY=your-api-key
SENDGRID_API_KEY=your-sendgrid-key
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Email/SMTP
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SMTP_URI=smtp://user:pass@smtp.example.com:587

# Cloud Storage
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key

# IBKR
IB_USER=your-ib-username
IB_PASS=your-ib-password
```

### 4. Run Migration Script

Use the provided migration script to move secrets to Vault:

```bash
# Dry run to see what will be migrated
python scripts/migrate_secrets_to_vault.py --dry-run --env-file .env

# Perform actual migration
python scripts/migrate_secrets_to_vault.py --env-file .env
```

### 5. Verify Migration

Check that secrets were properly stored in Vault:

```bash
# List secret paths
vault kv list secret/spreadpilot

# Read specific secrets (be careful not to expose in logs)
vault kv get secret/spreadpilot/auth/jwt
vault kv get secret/spreadpilot/database/mongodb
```

### 6. Update Service Configuration

Each service now automatically attempts to fetch secrets from Vault with fallback to environment variables.

No code changes required if using the latest version. The services will:
1. Try to fetch from Vault first
2. Fall back to environment variables if Vault is unavailable
3. Use default values for non-required secrets

### 7. Test Services

Start services and verify they can access secrets:

```bash
# Check service logs for Vault connection
docker-compose logs admin-api | grep -i vault

# Test authentication endpoint
curl -X POST http://localhost:8083/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

## Vault Secret Organization

Secrets are organized in Vault with the following structure:

```
secret/spreadpilot/
├── auth/
│   ├── jwt           # JWT_SECRET
│   ├── admin         # ADMIN_USERNAME, ADMIN_PASSWORD_HASH
│   └── security      # SECURITY_PIN_HASH
├── database/
│   ├── mongodb       # MONGO_URI
│   ├── postgres      # POSTGRES_URI
│   └── redis         # REDIS_URL
├── external/
│   ├── google        # GOOGLE_SHEETS_API_KEY
│   ├── sendgrid      # SENDGRID_API_KEY
│   └── telegram      # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
├── email/
│   └── smtp          # SMTP_USER, SMTP_PASSWORD, SMTP_URI
├── storage/
│   ├── minio         # MINIO_ACCESS_KEY, MINIO_SECRET_KEY
│   └── gcs           # GCS_SERVICE_ACCOUNT_KEY
└── ibkr/
    └── credentials   # IB_USER, IB_PASS
```

## Advanced Configuration

### Using Vault Policies

Create policies for different services:

```hcl
# Policy for admin-api service
path "secret/data/spreadpilot/auth/*" {
  capabilities = ["read"]
}

path "secret/data/spreadpilot/database/mongodb" {
  capabilities = ["read"]
}

# Policy for trading-bot service
path "secret/data/spreadpilot/ibkr/*" {
  capabilities = ["read"]
}

path "secret/data/spreadpilot/external/google" {
  capabilities = ["read"]
}
```

### Using AppRole Authentication

For production, use AppRole instead of tokens:

```bash
# Enable AppRole auth
vault auth enable approle

# Create role for services
vault write auth/approle/role/spreadpilot \
    token_ttl=1h \
    token_max_ttl=4h \
    policies="spreadpilot-policy"

# Get role ID and secret ID
vault read auth/approle/role/spreadpilot/role-id
vault write -f auth/approle/role/spreadpilot/secret-id
```

### Dynamic Database Credentials

Configure Vault to generate temporary database credentials:

```bash
# Enable database secrets engine
vault secrets enable database

# Configure MongoDB connection
vault write database/config/mongodb \
    plugin_name=mongodb-database-plugin \
    allowed_roles="spreadpilot-role" \
    connection_url="mongodb://{{username}}:{{password}}@localhost:27017/admin" \
    username="vault-admin" \
    password="vault-password"

# Create role for dynamic credentials
vault write database/roles/spreadpilot-role \
    db_name=mongodb \
    creation_statements='{ "db": "spreadpilot_admin", "roles": [{ "role": "readWrite" }] }' \
    default_ttl="1h" \
    max_ttl="24h"
```

## Troubleshooting

### Service Cannot Connect to Vault

1. Check Vault is running and unsealed:
   ```bash
   vault status
   ```

2. Verify network connectivity:
   ```bash
   curl -s $VAULT_ADDR/v1/sys/health
   ```

3. Check authentication token:
   ```bash
   vault token lookup
   ```

### Secrets Not Found

1. Verify secret path:
   ```bash
   vault kv get secret/spreadpilot/auth/jwt
   ```

2. Check service logs for exact error:
   ```bash
   docker-compose logs -f admin-api | grep -E "(vault|secret)"
   ```

### Permission Denied

1. Check token policies:
   ```bash
   vault token lookup -accessor <accessor>
   ```

2. Verify policy allows read access to required paths

## Rollback Plan

If you need to rollback to environment variables:

1. Ensure all secrets are still in `.env` files
2. Set `USE_VAULT=false` in environment
3. Restart services

The secret manager will automatically fall back to environment variables when Vault is unavailable.

## Security Best Practices

1. **Never commit secrets**: Keep `.env` files in `.gitignore`
2. **Use least privilege**: Create specific policies per service
3. **Rotate regularly**: Set up automatic rotation for credentials
4. **Monitor access**: Enable Vault audit logging
5. **Secure Vault**: Use TLS, proper authentication, and access controls
6. **Backup Vault**: Regular backups of Vault data
7. **High Availability**: Run Vault in HA mode for production

## Next Steps

1. Set up Vault UI for easier secret management
2. Implement automatic secret rotation
3. Configure Vault auto-unseal
4. Set up monitoring and alerting
5. Implement break-glass procedures