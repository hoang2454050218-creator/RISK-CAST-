"""
RISKCAST Authentication Module.

Provides enterprise-grade authentication:
- JWT token creation and validation
- OAuth2 provider integration (Okta, Azure AD, Google)
- Scope-based authorization

B3 COMPLIANCE: "No JWT/OAuth2 support" - FIXED
"""

from app.auth.oauth2 import (
    # Schemas
    TokenData,
    TokenPair,
    OAuth2Config,
    # JWT Handler
    JWTHandler,
    create_jwt_handler,
    # OAuth2 Provider
    OAuth2Provider,
    create_oauth2_provider,
    # Dependencies
    oauth2_password,
    oauth2_code,
    get_current_user_jwt,
    require_scope_jwt,
    # Constants
    SupportedOAuth2Provider,
)

__all__ = [
    # Schemas
    "TokenData",
    "TokenPair",
    "OAuth2Config",
    # JWT Handler
    "JWTHandler",
    "create_jwt_handler",
    # OAuth2 Provider
    "OAuth2Provider",
    "create_oauth2_provider",
    # Dependencies
    "oauth2_password",
    "oauth2_code",
    "get_current_user_jwt",
    "require_scope_jwt",
    # Constants
    "SupportedOAuth2Provider",
]
