from typing import Dict
import http.client


def simple_http_get(host: str, path: str, scheme: str, headers: Dict[str, str]) -> int:
    """Perform a simple HTTP GET using http.client to avoid external deps; return status code."""
    conn = None
    try:
        if scheme == "https":
            conn = http.client.HTTPSConnection(host, timeout=10)
        else:
            conn = http.client.HTTPConnection(host, timeout=10)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        # read and close to free sockets
        resp.read()
        return resp.status
    finally:
        if conn:
            conn.close()
