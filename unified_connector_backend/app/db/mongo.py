import os
from datetime import datetime
from typing import Optional, Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient

_client: Optional[AsyncIOMotorClient] = None

def get_mongo_url() -> str:
    # Expect environment variable MONGODB_URL to be set by orchestrator
    return os.getenv("MONGODB_URL", "mongodb://localhost:27017/unified_connector")

def get_db_name() -> str:
    return os.getenv("MONGODB_DB", "unified_connector")

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_mongo_url())
    return _client

def get_db():
    return get_client()[get_db_name()]

def connections_collection():
    return get_db()["connector_connections"]

async def upsert_connection(tenant_id: str, connector_id: str, credentials: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
    doc = {
        "tenant_id": tenant_id,
        "connector_id": connector_id,
        "credentials": credentials,
        "metadata": {
            "created_at": datetime.utcnow(),
            "refreshed_at": datetime.utcnow(),
            **(metadata or {})
        }
    }
    await connections_collection().update_one(
        {"tenant_id": tenant_id, "connector_id": connector_id},
        {"$set": doc},
        upsert=True
    )

async def get_connection(tenant_id: str, connector_id: str) -> Optional[Dict[str, Any]]:
    return await connections_collection().find_one({"tenant_id": tenant_id, "connector_id": connector_id})

async def delete_connection(tenant_id: str, connector_id: str):
    await connections_collection().delete_one({"tenant_id": tenant_id, "connector_id": connector_id})
