"""
sitecustomize for the backend 'src' directory to ensure parent paths and backend src are on sys.path.

This helps execution of:
    uvicorn app.server:app
from within this directory by making parent 'unified_connector_backend' and repo root importable.
"""
from __future__ import annotations

import os
import sys

def _add_path(p: str) -> None:
    if p and p not in sys.path:
        sys.path.insert(0, p)

_here = os.path.dirname(__file__)
cur = _here
for _ in range(6):
    _add_path(cur)
    parent = os.path.dirname(cur)
    if not parent or parent == cur:
        break
    cur = parent
