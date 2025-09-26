"""
Auto-loaded sitecustomize to make backend imports robust when running from deep subdirectories.

This adjusts sys.path at interpreter startup (Python auto-imports sitecustomize if present on sys.path)
so that parent directories and backend src are importable, enabling:
    uvicorn app.server:app
even when CWD is 'src/unified_connector_backend/utils'.
"""
from __future__ import annotations

import os
import sys

def _add_path(p: str) -> None:
    if p and p not in sys.path:
        sys.path.insert(0, p)

def _maybe_add_backend_src(start_dir: str) -> None:
    cur = start_dir
    for _ in range(8):
        if not cur or cur == os.path.dirname(cur):
            break
        backend_dir = os.path.join(cur, "unified_connector_backend")
        src_dir = os.path.join(backend_dir, "src")
        if os.path.isdir(backend_dir) and os.path.isdir(src_dir):
            _add_path(src_dir)
            return
        cur = os.path.dirname(cur)

_here = os.path.dirname(__file__)
cur = _here
for _ in range(8):
    _add_path(cur)
    parent = os.path.dirname(cur)
    if not parent or parent == cur:
        break
    cur = parent

_maybe_add_backend_src(_here)
