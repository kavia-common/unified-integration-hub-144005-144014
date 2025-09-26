# PUBLIC_INTERFACE
"""
Connector registry: register and access available connectors.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .base import BaseConnector


class _Registry:
    def __init__(self) -> None:
        self._by_id: Dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        if connector.id in self._by_id:
            raise ValueError(f"Connector already registered: {connector.id}")
        self._by_id[connector.id] = connector

    def get(self, connector_id: str) -> Optional[BaseConnector]:
        return self._by_id.get(connector_id)

    def list(self) -> List[dict]:
        return [
            {
                "id": c.id,
                "display_name": c.display_name,
                "supports_oauth": c.supports_oauth,
                "required_scopes": c.required_scopes,
            }
            for c in self._by_id.values()
        ]


_registry = _Registry()


# PUBLIC_INTERFACE
def connectors_registry() -> _Registry:
    """Return the connectors registry singleton."""
    return _registry
