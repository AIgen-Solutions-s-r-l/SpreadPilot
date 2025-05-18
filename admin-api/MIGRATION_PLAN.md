# Admin API Migration Plan

This document outlines the steps to migrate from the existing multiple Admin API implementations to the new consolidated version.

## Current Implementations

1. `admin_api/` (with underscore)
   - Complex implementation with advanced features
   - Uses AsyncIOMotorClient for MongoDB
   - Has a structured project layout with multiple modules
   - Uses the spreadpilot_core library

2. `admin-api/` (with hyphen)
   - Simpler implementation
   - Uses AsyncIOMotorClient for MongoDB
   - Has a basic authentication system
   - Also uses the spreadpilot_core library

3. `simple-admin-api/` (simplified version)
   - Very simple, standalone implementation
   - Everything in a single app.py file
   - Uses MongoDB directly with pymongo (not motor)
   - Includes a WebSocket endpoint

## New Implementation

The new implementation in `new-admin-api/` combines the best aspects of all three:
- Structured project layout from `admin_api/`
- Authentication system from `admin-api/`
- WebSocket support from `simple-admin-api/`
- Async MongoDB connection with proper error handling
- Background tasks for real-time updates
- Comprehensive API documentation
- Docker and Docker Compose support

## Migration Steps

1. **Backup Existing Implementations**
   ```bash
   mkdir -p backup
   cp -r admin_api backup/
   cp -r admin-api backup/
   cp -r simple-admin-api backup/
   ```

2. **Move New Implementation to Target Location**
   ```bash
   # Remove existing implementations
   rm -rf admin_api admin-api simple-admin-api
   
   # Move new implementation to admin-api (using hyphen convention)
   mv new-admin-api admin-api
   ```

3. **Update Docker Compose References**
   - Update any references in docker-compose files to point to the new implementation
   - Ensure the docker-compose.admin-api-setup.yml file is updated to use the new Dockerfile

4. **Update Documentation**
   - Update any references in documentation to point to the new implementation
   - Ensure the ADMIN-API-SETUP.md file is updated to reflect the new implementation

5. **Test the New Implementation**
   ```bash
   cd admin-api
   docker-compose up -d
   ```

6. **Update Import Statements in Other Services**
   - If any other services import from the admin_api module, update those imports to use admin-api instead

## Rollback Plan

If issues are encountered with the new implementation:

1. **Stop the New Implementation**
   ```bash
   cd admin-api
   docker-compose down
   ```

2. **Restore from Backup**
   ```bash
   rm -rf admin-api
   cp -r backup/admin_api .
   cp -r backup/admin-api .
   cp -r backup/simple-admin-api .
   ```

3. **Restart the Previous Implementation**
   ```bash
   # Choose which implementation to restart based on which was previously in use
   cd admin-api  # or admin_api or simple-admin-api
   docker-compose up -d