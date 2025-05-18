# Alert Router Migration Plan

This document outlines the steps to migrate from the existing multiple Alert Router implementations to the new consolidated version.

## Current Implementations

1. `alert_router/` (with underscore)
   - More complete implementation with main.py, config.py, and service/router.py
   - Uses AsyncIOMotorClient for MongoDB
   - Has secret loading functionality
   - Handles PubSub messages for alerts
   - Routes alerts to Telegram and Email

2. `alert-router/` (with hyphen)
   - Simpler implementation
   - Uses Python 3.11 instead of 3.10
   - Has different requirements (includes sendgrid and python-telegram-bot)

## New Implementation

The new implementation in `new-alert-router/` combines the best aspects of both:
- Structured project layout from `alert_router/`
- Modern Python 3.11 from `alert-router/`
- Secret loading functionality from `alert_router/`
- PubSub message handling from `alert_router/`
- Alert routing to Telegram and Email from `alert_router/`
- Comprehensive documentation and configuration

## Migration Steps

1. **Backup Existing Implementations**
   ```bash
   mkdir -p backup
   cp -r alert_router backup/
   cp -r alert-router backup/
   ```

2. **Move New Implementation to Target Location**
   ```bash
   # Remove existing implementations
   rm -rf alert_router alert-router
   
   # Move new implementation to alert-router (using hyphen convention)
   mv new-alert-router alert-router
   ```

3. **Update Docker Compose References**
   - Update any references in docker-compose files to point to the new implementation
   - Ensure the Dockerfile paths are updated to use the new implementation

4. **Update Documentation**
   - Update any references in documentation to point to the new implementation

5. **Test the New Implementation**
   ```bash
   cd alert-router
   # Run tests or start the service locally
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

## Rollback Plan

If issues are encountered with the new implementation:

1. **Stop the New Implementation**
   ```bash
   # If running locally
   # Press Ctrl+C to stop the service
   ```

2. **Restore from Backup**
   ```bash
   rm -rf alert-router
   cp -r backup/alert_router .
   cp -r backup/alert-router .
   ```

3. **Restart the Previous Implementation**
   ```bash
   # Choose which implementation to restart based on which was previously in use
   cd alert-router  # or alert_router
   # Start the service