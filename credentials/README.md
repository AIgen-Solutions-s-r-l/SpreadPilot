# Credentials Directory

This directory contains sensitive credential files needed for SpreadPilot operation.

## Required Files

### `service-account.json`
Google Cloud service account key file for accessing Google Sheets and other GCP services.

**To obtain:**
1. Go to Google Cloud Console → IAM & Admin → Service Accounts
2. Create a new service account or select existing one
3. Create a new key (JSON format)
4. Download and place in this directory as `service-account.json`

**Required permissions:**
- Google Sheets API access
- Google Drive API access (if needed)

## Security Note

**NEVER commit credential files to version control!**

This directory is included in `.gitignore` to prevent accidental commits of sensitive information.

## Development Setup

For local development, you'll need to:
1. Obtain the service account JSON file from your Google Cloud project
2. Place it in this directory as `service-account.json`
3. Ensure the service account has necessary permissions for your Google Sheets
4. Update the `.env` file with correct paths and configuration

## Production Deployment

In production, credentials should be managed through:
- Google Cloud Secret Manager
- Kubernetes secrets
- Environment variables (for non-file credentials)

Do not use file-based credentials in production environments.