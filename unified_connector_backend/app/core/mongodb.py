from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

mongo_client: AsyncIOMotorClient | None = None
db = None

async def connect_to_mongo():
    global mongo_client, db
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = mongo_client[settings.MONGODB_DB_NAME]

async def close_mongo_connection():
    global mongo_client
    if mongo_client:
        mongo_client.close()
        mongo_client = None
