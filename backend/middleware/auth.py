from fastapi import Header, HTTPException
from backend.config import settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Enforce API key auth when API_KEY is configured; no-op when it is empty."""
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
