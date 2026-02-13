"""
JWT Token Management.

HS256 signing for access tokens.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from riskcast.config import settings


class TokenError(Exception):
    """Raised when token creation or validation fails."""

    pass


def create_access_token(
    user_id: str,
    company_id: str,
    email: str,
    role: str = "member",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    now = datetime.utcnow()
    payload = {
        "user_id": str(user_id),
        "company_id": str(company_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Returns the payload dict with user_id, company_id, email, role.
    Raises TokenError on any failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        # Validate required fields
        if "user_id" not in payload or "company_id" not in payload:
            raise TokenError("Token missing required claims")
        return payload
    except JWTError as e:
        raise TokenError(f"Invalid token: {e}") from e
