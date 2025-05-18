#!/usr/bin/env python3
"""
Script to generate bcrypt password hashes for the Admin API.
"""

import sys
from passlib.context import CryptContext

# Create password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_hash(password: str) -> str:
    """Generate a bcrypt hash for the given password."""
    return pwd_context.hash(password)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_hash.py <password>")
        sys.exit(1)
    
    password = sys.argv[1]
    hashed_password = generate_hash(password)
    
    print(f"\nPassword Hash: {hashed_password}")
    print("\nAdd this to your .env file as:")
    print(f"ADMIN_PASSWORD_HASH={hashed_password}")