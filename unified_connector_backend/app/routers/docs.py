from fastapi import APIRouter

router = APIRouter()

# PUBLIC_INTERFACE
@router.get("/websocket-usage", summary="WebSocket usage help", description="This MVP does not provide WebSocket endpoints. Use REST endpoints under /api/connectors/* for search/create operations.")
def ws_help():
    """Docs endpoint to clarify WebSocket usage."""
    return {
        "websocket": "not_implemented_in_mvp",
        "note": "Use REST endpoints under /api/connectors/*."
    }
