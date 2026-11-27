"""Authentication dependency for API Key verification."""
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key_validator(expected_key: str):
    """Factory for API key dependency using current settings."""
    def validate_api_key(api_key: str = Security(api_key_header)) -> str:
        if not api_key or not secrets.compare_digest(api_key.strip(), expected_key.strip()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API Key",
            )
        return api_key
    return validate_api_key
