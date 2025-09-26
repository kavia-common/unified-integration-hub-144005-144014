from typing import Dict, List
from fastapi import FastAPI
from .base import BaseConnector

_registry: Dict[str, BaseConnector] = {}
_routers: Dict[str, any] = {}

def register(connector: BaseConnector, router):
    _registry[connector.id] = connector
    _routers[connector.id] = router

# PUBLIC_INTERFACE
def list_connectors() -> List[dict]:
    """List registered connectors with basic metadata."""
    return [
        {
            "id": c.id,
            "display_name": c.display_name,
            "supports_oauth": c.supports_oauth,
            "required_scopes": c.required_scopes,
        }
        for c in _registry.values()
    ]

# PUBLIC_INTERFACE
def get_connector(connector_id: str) -> BaseConnector | None:
    """Get a connector instance by id."""
    return _registry.get(connector_id)

def mount_all_connectors(app: FastAPI):
    for cid, router in _routers.items():
        app.include_router(router, prefix=f"/connectors/{cid}", tags=[cid])
