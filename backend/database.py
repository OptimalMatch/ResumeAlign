from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
import os
from dotenv import load_dotenv

load_dotenv()

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

db = MongoDB()

async def connect_to_mongo():
    """Create database connection."""
    try:
        db.client = AsyncIOMotorClient(
            os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=5000
        )
        # Force connection to verify it works
        await db.client.server_info()
        db.database = db.client[os.getenv("MONGODB_DB_NAME", "resume_optimizer")]
        print("Connected to MongoDB")
    except ServerSelectionTimeoutError:
        print("Unable to connect to MongoDB")
        raise

async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        print("Disconnected from MongoDB")

def get_database():
    """Get database instance."""
    return db.database

# Collections
def get_users_collection():
    return db.database.users

def get_optimizations_collection():
    return db.database.optimizations