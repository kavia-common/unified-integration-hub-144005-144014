from fastapi import HTTPException

def http_error(code: str, message: str, status_code: int = 400, retry_after: int | None = None):
    payload = {"status": "error", "code": code, "message": message}
    if retry_after is not None:
        payload["retry_after"] = retry_after
    raise HTTPException(status_code=status_code, detail=payload)
