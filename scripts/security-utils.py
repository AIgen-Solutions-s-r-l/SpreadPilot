#!/usr/bin/env python3
"""
Security utilities for SpreadPilot.
Provides helper functions for PIN generation, password hashing, and security checks.
"""

import argparse
import json
import os
import re
import secrets
import string
import sys
from datetime import datetime

from passlib.context import CryptContext

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_secure_pin(length: int = 6) -> str:
    """
    Generate a secure PIN that meets complexity requirements.

    Args:
        length: Length of the PIN (default: 6)

    Returns:
        str: Secure PIN
    """
    while True:
        # Generate random digits
        pin = "".join(secrets.choice(string.digits) for _ in range(length))

        # Check complexity requirements
        if validate_pin_complexity(pin):
            return pin


def validate_pin_complexity(pin: str) -> bool:
    """
    Validate PIN meets complexity requirements.

    Args:
        pin: PIN to validate

    Returns:
        bool: True if PIN is valid
    """
    # Check length
    if len(pin) < 6:
        return False

    # Check if all digits
    if not pin.isdigit():
        return False

    # Check for sequential patterns
    if is_sequential(pin):
        return False

    # Check for repeated digits
    if len(set(pin)) == 1:
        return False

    # Check for common patterns
    common_patterns = ["123456", "000000", "111111", "123123", "012345"]
    if pin in common_patterns:
        return False

    return True


def is_sequential(pin: str) -> bool:
    """Check if PIN is sequential."""
    ascending = all(int(pin[i]) == int(pin[i - 1]) + 1 for i in range(1, len(pin)))
    descending = all(int(pin[i]) == int(pin[i - 1]) - 1 for i in range(1, len(pin)))
    return ascending or descending


def hash_pin(pin: str) -> str:
    """
    Hash a PIN using bcrypt.

    Args:
        pin: PIN to hash

    Returns:
        str: Hashed PIN
    """
    return pwd_context.hash(pin)


def generate_jwt_secret(length: int = 32) -> str:
    """
    Generate a secure JWT secret.

    Args:
        length: Length in bytes (default: 32)

    Returns:
        str: Hex-encoded secret
    """
    return secrets.token_hex(length)


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a secure password meeting policy requirements.

    Args:
        length: Password length (default: 16)

    Returns:
        str: Secure password
    """
    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Ensure at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]

    # Fill the rest randomly
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))

    # Shuffle the password
    secrets.SystemRandom().shuffle(password)

    return "".join(password)


def check_password_policy(password: str) -> tuple[bool, list[str]]:
    """
    Check if password meets policy requirements.

    Args:
        password: Password to check

    Returns:
        tuple: (is_valid, list_of_issues)
    """
    issues = []

    # Length check
    if len(password) < 12:
        issues.append("Password must be at least 12 characters long")

    # Uppercase check
    if not re.search(r"[A-Z]", password):
        issues.append("Password must contain at least one uppercase letter")

    # Lowercase check
    if not re.search(r"[a-z]", password):
        issues.append("Password must contain at least one lowercase letter")

    # Digit check
    if not re.search(r"\d", password):
        issues.append("Password must contain at least one number")

    # Special character check
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        issues.append("Password must contain at least one special character")

    # Common password check
    common_passwords = [
        "password123",
        "admin123",
        "letmein",
        "welcome123",
        "password",
        "admin",
        "root",
        "toor",
        "pass",
    ]
    if password.lower() in common_passwords:
        issues.append("Password is too common")

    return len(issues) == 0, issues


def generate_api_key() -> str:
    """
    Generate a secure API key.

    Returns:
        str: API key in format: sp_live_xxxxx
    """
    prefix = "sp_live_"
    key = secrets.token_urlsafe(32)
    return f"{prefix}{key}"


def security_audit_report() -> dict:
    """
    Generate a security audit report.

    Returns:
        dict: Security audit results
    """
    report = {"timestamp": datetime.utcnow().isoformat(), "checks": []}

    # Check environment variables
    security_vars = ["JWT_SECRET", "SECURITY_PIN_HASH", "MONGO_URI", "POSTGRES_URI"]

    for var in security_vars:
        value = os.environ.get(var)
        if not value:
            report["checks"].append(
                {
                    "check": f"Environment variable {var}",
                    "status": "FAIL",
                    "message": f"{var} is not set",
                }
            )
        else:
            # Basic validation
            if var == "MONGO_URI" and "tls=true" not in value:
                report["checks"].append(
                    {
                        "check": "MongoDB TLS",
                        "status": "WARNING",
                        "message": "MongoDB connection may not be using TLS",
                    }
                )
            elif var == "POSTGRES_URI" and "sslmode=" not in value:
                report["checks"].append(
                    {
                        "check": "PostgreSQL SSL",
                        "status": "WARNING",
                        "message": "PostgreSQL connection may not be using SSL",
                    }
                )
            else:
                report["checks"].append(
                    {
                        "check": f"Environment variable {var}",
                        "status": "PASS",
                        "message": f"{var} is configured",
                    }
                )

    return report


def main():
    parser = argparse.ArgumentParser(description="SpreadPilot Security Utilities")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate PIN command
    pin_parser = subparsers.add_parser("generate-pin", help="Generate a secure PIN")
    pin_parser.add_argument(
        "--length", type=int, default=6, help="PIN length (default: 6)"
    )

    # Hash PIN command
    hash_parser = subparsers.add_parser("hash-pin", help="Hash a PIN")
    hash_parser.add_argument("pin", help="PIN to hash")

    # Generate JWT secret command
    jwt_parser = subparsers.add_parser("generate-jwt", help="Generate JWT secret")
    jwt_parser.add_argument(
        "--length", type=int, default=32, help="Secret length in bytes"
    )

    # Generate password command
    pass_parser = subparsers.add_parser(
        "generate-password", help="Generate secure password"
    )
    pass_parser.add_argument("--length", type=int, default=16, help="Password length")

    # Check password command
    check_parser = subparsers.add_parser("check-password", help="Check password policy")
    check_parser.add_argument("password", help="Password to check")

    # Generate API key command
    api_parser = subparsers.add_parser("generate-api-key", help="Generate API key")

    # Security audit command
    audit_parser = subparsers.add_parser("audit", help="Run security audit")

    args = parser.parse_args()

    if args.command == "generate-pin":
        pin = generate_secure_pin(args.length)
        print(f"Generated PIN: {pin}")
        print(f"PIN Hash: {hash_pin(pin)}")
        print("\nAdd this hash to your security.env file:")
        print(f"SECURITY_PIN_HASH={hash_pin(pin)}")

    elif args.command == "hash-pin":
        if not validate_pin_complexity(args.pin):
            print("ERROR: PIN does not meet complexity requirements")
            sys.exit(1)
        print(f"PIN Hash: {hash_pin(args.pin)}")

    elif args.command == "generate-jwt":
        secret = generate_jwt_secret(args.length)
        print(f"JWT Secret: {secret}")
        print("\nAdd this to your .env file:")
        print(f"JWT_SECRET={secret}")

    elif args.command == "generate-password":
        password = generate_secure_password(args.length)
        print(f"Generated Password: {password}")

    elif args.command == "check-password":
        valid, issues = check_password_policy(args.password)
        if valid:
            print("✅ Password meets all policy requirements")
        else:
            print("❌ Password does not meet policy requirements:")
            for issue in issues:
                print(f"  - {issue}")

    elif args.command == "generate-api-key":
        key = generate_api_key()
        print(f"API Key: {key}")

    elif args.command == "audit":
        report = security_audit_report()
        print(json.dumps(report, indent=2))

        # Exit with error if any checks failed
        failed = [c for c in report["checks"] if c["status"] == "FAIL"]
        if failed:
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
