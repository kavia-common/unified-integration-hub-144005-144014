from typing import Dict, Tuple
import base64
from urllib.parse import urlparse
from .http_client import simple_http_get


def _basic_auth_header(username: str, token: str) -> str:
    """Build a Basic authorization header value for Atlassian APIs."""
    raw = f"{username}:{token}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"Basic {encoded}"


# PUBLIC_INTERFACE
def test_atlassian_basic(base_url: str, username: str, api_token: str, service: str) -> Tuple[bool, str]:
    """
    Perform a minimal Basic Auth test against Atlassian Jira/Confluence Cloud.
    Jira test endpoint: /rest/api/3/myself
    Confluence test endpoint: /wiki/rest/api/space?limit=1 (common on cloud is /wiki prefix)
    """
    parsed = urlparse(base_url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc
    prefix = parsed.path.rstrip("/")
    auth = _basic_auth_header(username, api_token)

    if service == "jira":
        path = f"{prefix}/rest/api/3/myself"
    else:
        # Try common Confluence cloud path; users may provide either https://site.atlassian.net or https://site.atlassian.net/wiki
        # We'll attempt with provided prefix first, then fallback to '/wiki'
        path = f"{prefix}/rest/api/space?limit=1" if prefix.endswith("/wiki") else f"{prefix}/wiki/rest/api/space?limit=1"

    headers: Dict[str, str] = {
        "Authorization": auth,
        "Accept": "application/json",
        "User-Agent": "UnifiedConnector/0.1",
    }

    try:
        status = simple_http_get(host, path, scheme, headers)
        if status in (200, 201):
            return True, "Connection successful."
        elif status == 401:
            return False, "Authentication failed (401). Check email/username and API token."
        elif status == 403:
            return False, "Access forbidden (403). The token may lack required scopes."
        elif status == 404:
            return False, "Endpoint not found (404). Verify the baseUrl (ensure correct site and product path)."
        else:
            return False, f"Unexpected response status: {status}"
    except Exception as e:
        return False, f"Connection error: {e}"
