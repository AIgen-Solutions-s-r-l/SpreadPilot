# Report Worker Migration Plan

This document outlines the steps to migrate from the existing multiple Report Worker implementations to the new consolidated version.

## Current Implementations

1. `report_worker/` (with underscore)
   - More complete implementation with main.py, config.py, and service modules
   - Uses Flask for the web server
   - Uses MongoDB for data storage
   - Has secret loading functionality
   - Handles PubSub messages for report generation
   - Has more dependencies in requirements.in

2. `report-worker/` (with hyphen)
   - Simpler implementation
   - Uses Python 3.11
   - Has fewer dependencies in requirements.in

## New Implementation

The new implementation in `new-report-worker/` combines the best aspects of both:
- Structured project layout from `report_worker/`
- Modern Python 3.11 from `report-worker/`
- Secret loading functionality from `report_worker/`
- PubSub message handling from `report_worker/`
- MongoDB integration for data storage
- Comprehensive documentation and configuration

## Migration Steps

1. **Backup Existing Implementations**
   ```bash
   mkdir -p backup
   cp -r report_worker backup/
   cp -r report-worker backup/
   ```

2. **Move New Implementation to Target Location**
   ```bash
   # Remove existing implementations
   rm -rf report_worker report-worker
   
   # Move new implementation to report-worker (using hyphen convention)
   mv new-report-worker report-worker
   ```

3. **Update Docker Compose References**
   - Update any references in docker-compose files to point to the new implementation
   - Ensure the Dockerfile paths are updated to use the new implementation

4. **Update Documentation**
   - Update any references in documentation to point to the new implementation

5. **Test the New Implementation**
   ```bash
   cd report-worker
   # Run tests or start the service locally
   python app/main.py
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
   rm -rf report-worker
   cp -r backup/report_worker .
   cp -r backup/report-worker .
   ```

3. **Restart the Previous Implementation**
   ```bash
   # Choose which implementation to restart based on which was previously in use
   cd report-worker  # or report_worker
   # Start the service