"""
AI Service API Dependencies.

Validates JWT tokens issued by the main InterviewOS API service.
The AI service uses the same JWT secret as the API — tokens are interoperable.
"""

import uuid
import logging
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.config import settings

logger = logging.getLogger("interviewos.ai.api.deps")

security = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate an InterviewOS JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_ai_caller(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Extract and validate the caller's identity from the JWT token.
    Returns a dict with user_id, workspace_id, role, is_interviewer.
    """
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return {
        "user_id": payload.get("sub"),
        "workspace_id": payload.get("workspace_id"),
        "role": payload.get("role", "member"),
        "is_interviewer": payload.get("is_interviewer", False),
    }


async def require_interviewer(
    caller: dict = Depends(get_ai_caller),
) -> dict:
    """
    Dependency that requires the caller to be an interviewer.
    Candidates must not access AI copilot endpoints.
    """
    if not caller.get("is_interviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI copilot access is restricted to interviewers",
        )
    return caller
