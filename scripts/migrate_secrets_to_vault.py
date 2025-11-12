#!/usr/bin/env python3
"""
Script to migrate SpreadPilot secrets from environment variables to HashiCorp Vault.

This script helps migrate existing secrets stored in environment variables or .env files
to HashiCorp Vault for improved security and centralized secret management.

Usage:
    python migrate_secrets_to_vault.py [--dry-run] [--env-file .env]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from spreadpilot_core.logging import get_logger
from spreadpilot_core.utils.secret_manager import (
    SECRET_CONFIGS,
    SecretManager,
    SecretType,
    get_secret_manager,
)
from spreadpilot_core.utils.vault import VaultClient

logger = get_logger(__name__)


def load_env_file(env_file: str) -> dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars = {}

    if not os.path.exists(env_file):
        logger.error(f"Environment file not found: {env_file}")
        return env_vars

    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes if present
                value = value.strip('"').strip("'")
                env_vars[key] = value

    return env_vars


def migrate_secrets(dry_run: bool = False, env_file: Optional[str] = None) -> bool:
    """
    Migrate secrets from environment variables to Vault.

    Args:
        dry_run: If True, only show what would be migrated without actually doing it
        env_file: Optional .env file to load secrets from

    Returns:
        True if migration successful, False otherwise
    """
    # Load environment variables from file if provided
    if env_file:
        env_vars = load_env_file(env_file)
        logger.info(f"Loaded {len(env_vars)} variables from {env_file}")
    else:
        env_vars = os.environ.copy()

    # Initialize Vault client
    vault_url = env_vars.get("VAULT_ADDR", "http://localhost:8200")
    vault_token = env_vars.get("VAULT_TOKEN")

    if not vault_token:
        logger.error(
            "VAULT_TOKEN not found in environment. Please set it to authenticate with Vault."
        )
        return False

    try:
        vault_client = VaultClient(vault_url=vault_url, vault_token=vault_token)

        # Test Vault connectivity
        if not vault_client.health_check():
            logger.error("Failed to connect to Vault. Please check VAULT_ADDR and VAULT_TOKEN.")
            return False

        logger.info(f"Connected to Vault at {vault_url}")

    except Exception as e:
        logger.error(f"Failed to initialize Vault client: {e}")
        return False

    # Initialize secret manager with Vault
    secret_manager = SecretManager(vault_client=vault_client)

    # Track migration status
    migrated = []
    skipped = []
    failed = []

    # Group secrets by Vault path
    secrets_by_path: dict[str, dict[str, str]] = {}

    for secret_type, config in SECRET_CONFIGS.items():
        env_var = config.env_var
        vault_path = config.vault_path

        # Check if secret exists in environment
        if env_var in env_vars:
            value = env_vars[env_var]

            # Skip empty values
            if not value:
                logger.debug(f"Skipping {env_var} (empty value)")
                skipped.append(env_var)
                continue

            # Group by Vault path
            if vault_path not in secrets_by_path:
                secrets_by_path[vault_path] = {}

            secrets_by_path[vault_path][secret_type.value] = value
            logger.info(f"Found {env_var} -> {vault_path}/{secret_type.value}")
        else:
            logger.debug(f"Secret {env_var} not found in environment")
            skipped.append(env_var)

    # Migrate secrets grouped by path
    for vault_path, secrets in secrets_by_path.items():
        if dry_run:
            logger.info(f"[DRY RUN] Would store {len(secrets)} secrets at {vault_path}")
            for key, value in secrets.items():
                # Mask sensitive values in dry run
                masked_value = value[:3] + "***" if len(value) > 3 else "***"
                logger.info(f"  - {key}: {masked_value}")
            migrated.extend(secrets.keys())
        else:
            try:
                # Get existing secrets at this path
                existing = vault_client.get_secret(vault_path.replace("secret/", "")) or {}

                # Merge with new secrets
                existing.update(secrets)

                # Store to Vault
                success = vault_client.put_secret(vault_path.replace("secret/", ""), existing)

                if success:
                    logger.info(f"Successfully stored {len(secrets)} secrets at {vault_path}")
                    migrated.extend(secrets.keys())
                else:
                    logger.error(f"Failed to store secrets at {vault_path}")
                    failed.extend(secrets.keys())

            except Exception as e:
                logger.error(f"Error storing secrets at {vault_path}: {e}")
                failed.extend(secrets.keys())

    # Print summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total secrets found: {len(migrated) + len(failed)}")
    print(f"Successfully migrated: {len(migrated)}")
    print(f"Failed: {len(failed)}")
    print(f"Skipped (not found/empty): {len(skipped)}")

    if migrated:
        print("\nMigrated secrets:")
        for secret in sorted(migrated):
            print(f"  ✓ {secret}")

    if failed:
        print("\nFailed to migrate:")
        for secret in sorted(failed):
            print(f"  ✗ {secret}")

    if dry_run:
        print("\n[DRY RUN] No changes were made. Remove --dry-run to perform actual migration.")
    else:
        print("\nMigration complete!")
        print("\nNext steps:")
        print("1. Update your services to use Vault for secret retrieval")
        print("2. Remove sensitive values from environment variables")
        print("3. Restart services to pick up the changes")

    return len(failed) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate SpreadPilot secrets to HashiCorp Vault")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually doing it",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file containing secrets (default: use current environment)",
    )
    parser.add_argument(
        "--vault-addr",
        type=str,
        help="Vault server address (default: VAULT_ADDR env var or http://localhost:8200)",
    )
    parser.add_argument(
        "--vault-token", type=str, help="Vault authentication token (default: VAULT_TOKEN env var)"
    )

    args = parser.parse_args()

    # Set Vault environment variables if provided
    if args.vault_addr:
        os.environ["VAULT_ADDR"] = args.vault_addr
    if args.vault_token:
        os.environ["VAULT_TOKEN"] = args.vault_token

    # Run migration
    success = migrate_secrets(dry_run=args.dry_run, env_file=args.env_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
