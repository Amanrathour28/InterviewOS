import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

# Initialize Argon2id password hasher
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash password using Argon2id algorithm."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2 hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def generate_secure_token() -> str:
    """Generate cryptographically secure random urlsafe string for refresh/reset tokens."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Compute SHA-256 hash of a token for secure server-side persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(8),
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT access token signature, expiration, and token type."""
    try:
        decoded = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        if decoded.get("type") != "access":
            return None
        return decoded
    except jwt.PyJWTError:
        return None
