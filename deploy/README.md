# SpreadPilot Deployment Guide (GCP Cloud Build & Cloud Run)

This directory contains the configuration and scripts for automating the deployment of SpreadPilot microservices to Google Cloud Platform using Cloud Build and Cloud Run.

## Files

*   **`../cloudbuild.yaml`**: Defines the CI/CD pipeline executed by Google Cloud Build. It includes steps for:
    *   Installing dependencies.
    *   Running unit and integration tests.
    *   Building Docker images for each microservice.
    *   Pushing images to Google Container Registry (GCR).
    *   Deploying services to the **development** environment on Cloud Run (triggered automatically on merge to `main`).
*   **`deploy.sh`**: A bash script used by Cloud Build (and potentially manually) to deploy a specific service image to a specified environment (`dev` or `prod`) on Cloud Run. It handles environment-specific configurations and secrets.
*   **`promote_to_prod.sh`**: A bash script designed for manually triggering a production deployment. It takes a service name and a specific image tag (usually a commit SHA verified in the dev environment) and uses `deploy.sh` to deploy it to the **production** environment.
*   **`.env.dev.template`**: A template file outlining the necessary environment variables for the **development** environment. Variables marked with `(Secret Manager)` should be stored securely in GCP Secret Manager.
*   **`.env.prod.template`**: A template file outlining the necessary environment variables for the **production** environment. Note the `-prod` suffix convention for secret names in Secret Manager for production.

## Setup Instructions

### 1. Prerequisites

*   **GCP Project:** You need separate GCP projects for `dev` and `prod` environments (or use a single project with clear naming conventions).
*   **Enable APIs:** Ensure the following APIs are enabled in your GCP project(s):
    *   Cloud Build API
    *   Cloud Run API
    *   Container Registry API
    *   Secret Manager API
    *   IAM API
*   **Permissions:** The Cloud Build service account (`[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com`) needs appropriate IAM roles:
    *   `Cloud Run Admin`: To deploy and manage Cloud Run services.
    *   `Storage Admin`: To push images to GCR (or `Storage Object Admin` on the GCR bucket).
    *   `Secret Manager Secret Accessor`: To access secrets during deployment.
    *   `Service Account User`: To act as the Cloud Run runtime service account (if different from default).
    *   Any secrets or network access needed to run integration tests against the database (e.g., MongoDB connection string, firewall rules).
*   **Dockerfiles:** Ensure each microservice (including `frontend`) has a valid `Dockerfile`. The `cloudbuild.yaml` assumes standard locations (`<service-name>/Dockerfile`).

### 2. Configure Secret Manager

For each variable marked with `(Secret Manager)` in the `.env.*.template` files:

1.  Go to the GCP Secret Manager console for your `dev` project.
2.  Create a new secret.
    *   Use the secret name specified in the template (e.g., `firebase-sa`, `ibkr-password`).
    *   Add the secret value.
3.  Repeat for all secrets in the `.env.dev.template`.
4.  Go to the GCP Secret Manager console for your `prod` project.
5.  Create secrets using the **production names** (e.g., `firebase-sa-prod`, `ibkr-password-prod`).
    *   Add the corresponding production secret values.
6.  Ensure the Cloud Build service account has the `Secret Manager Secret Accessor` role in *both* projects.

### 3. Configure Cloud Build Triggers

1.  Go to the Cloud Build console -> Triggers.
2.  Connect your source code repository (e.g., GitHub, Cloud Source Repositories).
3.  **Create Trigger for Dev Deployment:**
    *   **Name:** `Deploy to Dev`
    *   **Event:** Push to branch
    *   **Repository:** Your connected repository
    *   **Branch:** `^main$` (or your primary development branch)
    *   **Configuration:** Cloud Build configuration file (repository)
    *   **Cloud Build file location:** `cloudbuild.yaml`
    *   **Substitution Variables (Optional but Recommended):**
        *   `_GCP_REGION`: `us-central1` (or your preferred region)
        *   You can add others if needed. The `PROJECT_ID` and `COMMIT_SHA` are provided automatically by Cloud Build.
    *   **Service Account:** Ensure the Cloud Build service account is selected.
4.  **Create Trigger for Production Promotion (Manual):**
    *   **Name:** `Promote to Production`
    *   **Event:** Manual invocation
    *   **Repository:** Your connected repository
    *   **Branch/Tag:** Leave flexible or set a default like `main`. You will specify the commit when running manually.
    *   **Configuration:** Cloud Build configuration file (repository)
    *   **Cloud Build file location:** `deploy/cloudbuild-promote.yaml` (You'll need to create this - see below)
    *   **Substitution Variables:**
        *   `_SERVICE_NAME`: (Leave blank - required at invocation)
        *   `_IMAGE_TAG`: (Leave blank - required at invocation, usually a commit SHA)
        *   `_GCP_PROJECT_ID_PROD`: `your-gcp-project-id-prod`
        *   `_GCP_REGION`: `us-central1` (or your preferred region)
    *   **Service Account:** Ensure the Cloud Build service account is selected.

### 4. Create `deploy/cloudbuild-promote.yaml`

Create a separate, simpler Cloud Build file specifically for the manual promotion trigger:

```yaml
# deploy/cloudbuild-promote.yaml
# Used for manually promoting a specific service version to production.

steps:
- name: 'bash'
  id: 'Run Promotion Script'
  script: |
    #!/usr/bin/env bash
    set -e # Exit on error
    chmod +x deploy/promote_to_prod.sh
    ./deploy/promote_to_prod.sh "$_SERVICE_NAME" "$_IMAGE_TAG" "$_GCP_PROJECT_ID_PROD"
  waitFor: ['-'] # Start immediately

timeout: 600s # 10 minutes
```

### 5. Review and Customize

*   **Testing:** The `cloudbuild.yaml` includes basic test steps. You *must* adapt these to your project's specific testing setup (e.g., test directories, commands, required environment setup for integration tests). Add steps for each service that has tests.
*   **Deployment Strategy:** This setup uses basic Cloud Run deployment. Review Cloud Run options (min/max instances, CPU allocation, concurrency, VPC connectors, etc.) and add corresponding flags to the `gcloud run deploy` commands in `deploy.sh` as needed.
*   **Frontend Build:** The frontend build step assumes a simple Docker build. If your frontend requires a multi-stage build or specific environment variables during the build process, update the `frontend/Dockerfile` and potentially the corresponding build step in `cloudbuild.yaml`.
*   **Error Handling:** The scripts use `set -e`. Consider adding more specific error handling or notifications if needed.
*   **Security:** Review `--allow-unauthenticated` flags. Only use them for services intended for public access (like the frontend or potentially a public API). Other services should likely rely on authenticated invocation (e.g., using IAM service accounts).

## Usage

*   **Development:** Merging code into the `main` branch will automatically trigger the `Deploy to Dev` build, running tests and deploying successful builds to the dev environment.
*   **Production:**
    1.  Identify the `COMMIT_SHA` of the version you want to promote (usually one that has been successfully deployed and tested in dev).
    2.  Go to Cloud Build -> Triggers.
    3.  Find the `Promote to Production` trigger and click "Run".
    4.  Enter the required substitution variables:
        *   `_SERVICE_NAME`: The name of the service (e.g., `admin-api`).
        *   `_IMAGE_TAG`: The `COMMIT_SHA` to deploy.
    5.  Click "Run trigger". This will execute `deploy/promote_to_prod.sh` using the specified image tag and deploy to the production Cloud Run service.