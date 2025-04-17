#!/bin/bash

# deploy/promote_to_prod.sh
# Promotes a specific image tag (commit SHA) of a service to the production environment.

set -e
set -u
set -o pipefail

# --- Configuration ---
SERVICE_NAME="$1"   # e.g., admin-api, trading-bot
IMAGE_TAG="$2"      # The specific commit SHA or tag verified in dev
GCP_PROJECT_ID="$3"

# --- Input Validation ---
if [ -z "$SERVICE_NAME" ] || [ -z "$IMAGE_TAG" ] || [ -z "$GCP_PROJECT_ID" ]; then
  echo "Usage: $0 <service-name> <image-tag> <gcp-project-id>"
  echo "Example: $0 admin-api abc1234 my-gcp-project"
  exit 1
fi

echo "Promoting ${SERVICE_NAME} version ${IMAGE_TAG} to Production..."

# --- Call the main deployment script ---
# Assuming deploy.sh is in the same directory
SCRIPT_DIR=$(dirname "$0")
"${SCRIPT_DIR}/deploy.sh" "$SERVICE_NAME" "prod" "$IMAGE_TAG" "$GCP_PROJECT_ID"

echo "Promotion of ${SERVICE_NAME} version ${IMAGE_TAG} to Production completed."