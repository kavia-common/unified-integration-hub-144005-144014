from typing import Optional
from ..core.mongodb import db
from ..models.connection import Connection
from ..core.security import encrypt_secret, decrypt_secret

COLL = "connector_connections"

async def upsert_connection(conn: Connection):
    # encrypt secrets before storing
    doc = conn.model_dump()
    creds = doc.get("credentials", {})
    for key in ("access_token", "refresh_token"):
        if creds.get(key):
            creds[key] = encrypt_secret(creds[key])
    doc["credentials"] = creds
    await db[COLL].update_one(
        {"tenant_id": conn.tenant_id, "connector_id": conn.connector_id},
        {"$set": doc},
        upsert=True,
    )

async def get_connection(tenant_id: str, connector_id: str) -> Optional[Connection]:
    doc = await db[COLL].find_one({"tenant_id": tenant_id, "connector_id": connector_id})
    if not doc:
        return None
    # decrypt
    creds = doc.get("credentials", {})
    for key in ("access_token", "refresh_token"):
        if creds.get(key):
            creds[key] = decrypt_secret(creds[key])
    doc["credentials"] = creds
    return Connection(**doc)

async def delete_connection(tenant_id: str, connector_id: str) -> int:
    res = await db[COLL].delete_one({"tenant_id": tenant_id, "connector_id": connector_id})
    return res.deleted_count
