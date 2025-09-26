"""
sitecustomize for 'src/unified_connector_backend' to ensure parent paths are added to sys.path.
This makes 'app.server' and 'unified_connector_backend' imports work when CWD is this directory.
"""
from __future__ import annotations

import os
import sys

def _add_path(p: str) -> None:
    if p and p not in sys.path:
        sys.path.insert(0, p)

_here = os.path.dirname(__file__)
cur = _here
for _ in range(8):
    _add_path(cur)
    parent = os.path.dirname(cur)
    if not parent or parent == cur:
        break
    cur = parent
