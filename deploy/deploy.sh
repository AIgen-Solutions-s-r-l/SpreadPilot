#!/bin/bash

# deploy/deploy.sh
# Deploys a specific service to a specified environment (dev/prod) on Cloud Run.

set -e # Exit immediately if a command exits with a non-zero status.
set -u # Treat unset variables as an error when substituting.
set -o pipefail # Return value of a pipeline is the value of the last command to exit with a non-zero status

# --- Configuration ---
SERVICE_NAME="$1" # e.g., admin-api, trading-bot
ENVIRONMENT="$2"  # 'dev' or 'prod'
IMAGE_TAG="$3"    # Commit SHA or 'latest' for prod promotion
GCP_PROJECT_ID="$4"
GCP_REGION="us-central1" # Or make this an argument/config

# --- Input Validation ---
if [ -z "$SERVICE_NAME" ] || [ -z "$ENVIRONMENT" ] || [ -z "$IMAGE_TAG" ] || [ -z "$GCP_PROJECT_ID" ]; then
  echo "Usage: $0 <service-name> <environment> <image-tag> <gcp-project-id>"
  echo "Example: $0 admin-api dev abc1234 my-gcp-project"
  exit 1
fi

if [ "$ENVIRONMENT" != "dev" ] && [ "$ENVIRONMENT" != "prod" ]; then
  echo "Error: Environment must be 'dev' or 'prod'."
  exit 1
fi

# --- Determine Cloud Run Service Name and Configuration ---
CLOUD_RUN_SERVICE_NAME="${SERVICE_NAME}-${ENVIRONMENT}"
IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "Deploying ${SERVICE_NAME} to ${ENVIRONMENT} environment..."
echo "Cloud Run Service: ${CLOUD_RUN_SERVICE_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "Project: ${GCP_PROJECT_ID}"
echo "Region: ${GCP_REGION}"

# --- Base gcloud command ---
GCLOUD_CMD=(
  gcloud run deploy "${CLOUD_RUN_SERVICE_NAME}"
  --image="${IMAGE_NAME}"
  --region="${GCP_REGION}"
  --platform=managed
  --project="${GCP_PROJECT_ID}"
)

# --- Environment-Specific Configuration ---
# Common env vars (can be expanded)
COMMON_ENV_VARS="ENV=${ENVIRONMENT},GCP_PROJECT=${GCP_PROJECT_ID}"

# Service-specific env vars and secrets (add more as needed)
SERVICE_ENV_VARS=""
SECRET_REFS="" # Format: SECRET_NAME=SECRET_NAME:latest,...

case $SERVICE_NAME in
  admin-api)
    SERVICE_ENV_VARS="API_BASE_URL=..." # Example - Set actual URL based on env
    SECRET_REFS="FIREBASE_SERVICE_ACCOUNT=firebase-sa:latest" # Example secret - use -prod suffix for prod
    GCLOUD_CMD+=( --allow-unauthenticated ) # If public access needed
    ;;
  trading-bot)
    SECRET_REFS="IBKR_ACCOUNT=ibkr-account:latest,IBKR_PASSWORD=ibkr-password:latest,TELEGRAM_BOT_TOKEN=telegram-token:latest" # Use -prod suffix for prod
    ;;
  report-worker)
    SECRET_REFS="SENDGRID_API_KEY=sendgrid-key:latest,TELEGRAM_BOT_TOKEN=telegram-token:latest" # Use -prod suffix for prod
    ;;
  alert-router)
    SECRET_REFS="TELEGRAM_BOT_TOKEN=telegram-token:latest" # Use -prod suffix for prod
    ;;
  watchdog)
    SECRET_REFS="TELEGRAM_BOT_TOKEN=telegram-token:latest" # Use -prod suffix for prod
    ;;
  frontend)
    SERVICE_ENV_VARS="REACT_APP_API_URL=..." # Example - Set actual URL based on env
    GCLOUD_CMD+=( --allow-unauthenticated )
    ;;
  *)
    echo "Warning: No specific configuration found for service ${SERVICE_NAME}. Using defaults."
    ;;
esac

# Adjust secret names for production
if [ "$ENVIRONMENT" == "prod" ]; then
    SECRET_REFS=${SECRET_REFS//:latest/-prod:latest} # Append -prod to secret names
    # Update URLs for prod if needed in SERVICE_ENV_VARS
    case $SERVICE_NAME in
      admin-api) SERVICE_ENV_VARS="API_BASE_URL=..." ;; # Set prod URL
      frontend) SERVICE_ENV_VARS="REACT_APP_API_URL=..." ;; # Set prod URL
    esac
fi


# --- Combine Env Vars and Secrets ---
ALL_ENV_VARS="${COMMON_ENV_VARS}"
if [ -n "$SERVICE_ENV_VARS" ]; then
  ALL_ENV_VARS="${ALL_ENV_VARS},${SERVICE_ENV_VARS}"
fi

# Add env vars to command
if [ -n "$ALL_ENV_VARS" ]; then
  # Use ^--^ delimiter for Cloud Build compatibility if running there
  # Locally, just use comma separation
  if [ -n "${CLOUD_BUILD:-}" ]; then # Check if CLOUD_BUILD is set and non-empty
      GCLOUD_CMD+=( "--set-env-vars=^--^${ALL_ENV_VARS//,/--}" )
  else
      GCLOUD_CMD+=( "--set-env-vars=${ALL_ENV_VARS}" )
  fi
fi

# Add secrets to command
if [ -n "$SECRET_REFS" ]; then
  GCLOUD_CMD+=( --set-secrets="${SECRET_REFS}" )
fi

# --- Execute Deployment ---
echo "Running command: ${GCLOUD_CMD[@]}"
"${GCLOUD_CMD[@]}"

echo "Deployment of ${SERVICE_NAME} to ${ENVIRONMENT} completed successfully."