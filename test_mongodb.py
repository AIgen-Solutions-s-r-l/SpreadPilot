import pymongo
import time

# Connection parameters
mongo_uri = "mongodb://admin:password@mongodb:27017"

# Wait for MongoDB to be ready
print("Waiting for MongoDB to be ready...")
time.sleep(5)

# Try to connect to MongoDB
try:
    client = pymongo.MongoClient(mongo_uri)
    # The ismaster command is cheap and does not require auth
    client.admin.command('ismaster')
    print("Successfully connected to MongoDB!")
    
    # List databases
    print("\nAvailable databases:")
    for db in client.list_database_names():
        print(f"- {db}")
    
    # Create a test database and collection
    db = client["test_db"]
    collection = db["test_collection"]
    
    # Insert a document
    result = collection.insert_one({"name": "Test Document", "value": 42})
    print(f"\nInserted document with ID: {result.inserted_id}")
    
    # Find the document
    doc = collection.find_one({"name": "Test Document"})
    print(f"Found document: {doc}")
    
    # Clean up
    client.drop_database("test_db")
    print("\nTest database dropped.")
    
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")