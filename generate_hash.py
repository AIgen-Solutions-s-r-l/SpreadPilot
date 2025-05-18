import bcrypt

def generate_password_hash(password):
    """Generate a bcrypt hash for the given password."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

if __name__ == "__main__":
    password = input("Enter password to hash: ")
    hashed_password = generate_password_hash(password)
    print("\nBcrypt hash for your password:")
    print(hashed_password)
    print("\nAdd this to your .env file as ADMIN_PASSWORD_HASH")