import os
from motor.motor_asyncio import AsyncIOMotorClient

# Get MongoDB connection details from environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@mongodb:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "spreadpilot_admin")

print(f"Connecting to MongoDB with URI: {MONGO_URI}")
print(f"Using database: {MONGO_DB_NAME}")

# Create a MongoDB client
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]

# Define collections
followers_collection = db.followers

# Function to check database connection
async def check_connection():
    try:
        # The ismaster command is cheap and does not require auth
        await client.admin.command('ismaster')
        print("Successfully connected to MongoDB!")
        return True
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return False