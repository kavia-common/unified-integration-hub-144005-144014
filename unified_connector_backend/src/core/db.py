from __future__ import annotations

from typing import Any, Dict

from pymongo import MongoClient

from src.core.settings import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_client: MongoClient | None = None


# PUBLIC_INTERFACE
def get_mongo_client() -> MongoClient:
    """Return a singleton MongoClient using settings from environment variables."""
    global _client
    if _client is None:
        settings = get_settings()
        logger.info("Connecting to MongoDB...")
        _client = MongoClient(settings.mongo.MONGODB_URL)
    return _client


# PUBLIC_INTERFACE
def get_db():
    """Get the configured MongoDB database handle."""
    settings = get_settings()
    return get_mongo_client()[settings.mongo.MONGODB_DB]


# PUBLIC_INTERFACE
def tenant_collection(tenant_id: str, name: str):
    """Get a tenant-scoped collection by name.

    Using naming convention: <tenantId>__<collection>
    """
    col_name = f"{tenant_id}__{name}"
    return get_db()[col_name]


# PUBLIC_INTERFACE
def upsert_by_id(collection, _id: str, payload: Dict[str, Any]):
    """Upsert a document by id."""
    collection.update_one({"_id": _id}, {"$set": payload}, upsert=True)
