"""
Tests for OAuth2/JWT Authentication.

B3 COMPLIANCE: Validates JWT/OAuth2 support implementation.

Tests:
- JWT token creation and validation
- Token refresh flow
- Token revocation
- Scope-based authorization
- OAuth2 provider integration
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json
import base64

from fastapi import HTTPException
from fastapi.testclient import TestClient


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def jwt_handler():
    """Create a JWT handler for testing."""
    from app.auth.oauth2 import JWTHandler
    return JWTHandler(secret_key="test-secret-key-for-testing")


@pytest.fixture
def sample_user_data():
    """Sample user data for token creation."""
    return {
        "user_id": "user_123",
        "email": "test@example.com",
        "scopes": ["decisions:read", "decisions:write"],
        "customer_id": "cust_456",
    }


@pytest.fixture
def oauth2_config():
    """Sample OAuth2 configuration."""
    from app.auth.oauth2 import OAuth2Config, SupportedOAuth2Provider
    
    return OAuth2Config(
        provider=SupportedOAuth2Provider.GOOGLE,
        client_id="test-client-id",
        client_secret="test-client-secret",
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
        scopes=["openid", "email", "profile"],
    )


# ============================================================================
# JWT HANDLER TESTS
# ============================================================================


class TestJWTHandler:
    """Test JWT token operations."""
    
    def test_create_access_token(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: JWT token creation.
        
        Token should be created with correct claims.
        """
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            scopes=sample_user_data["scopes"],
            customer_id=sample_user_data["customer_id"],
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Token should have 3 parts (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3
    
    def test_create_refresh_token(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: Refresh token creation.
        
        Refresh token should be created for token rotation.
        """
        token = jwt_handler.create_refresh_token(
            user_id=sample_user_data["user_id"],
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_token_pair(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: Token pair creation.
        
        Should create both access and refresh tokens.
        """
        from app.auth.oauth2 import TokenPair
        
        token_pair = jwt_handler.create_token_pair(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            scopes=sample_user_data["scopes"],
            customer_id=sample_user_data["customer_id"],
        )
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in > 0
        assert "decisions:read" in token_pair.scope
    
    def test_decode_token(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: JWT token validation.
        
        Token should be decoded and validated correctly.
        """
        # Create token
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            scopes=sample_user_data["scopes"],
            customer_id=sample_user_data["customer_id"],
        )
        
        # Decode token
        token_data = jwt_handler.decode_token(token)
        
        assert token_data.sub == sample_user_data["user_id"]
        assert token_data.email == sample_user_data["email"]
        assert set(token_data.scopes) == set(sample_user_data["scopes"])
        assert token_data.customer_id == sample_user_data["customer_id"]
    
    def test_decode_token_expired(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: Expired token rejection.
        
        Expired tokens should be rejected.
        """
        # Create token with negative expiry (already expired)
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            expires_delta=timedelta(seconds=-10),  # Already expired
        )
        
        # Try to decode - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.decode_token(token)
        
        assert exc_info.value.status_code == 401
    
    def test_decode_invalid_token(self, jwt_handler):
        """Invalid tokens should be rejected."""
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.decode_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
    
    def test_revoke_token(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: Token revocation.
        
        Revoked tokens should be rejected.
        """
        # Create token
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
        )
        
        # Decode to get JTI
        token_data = jwt_handler.decode_token(token)
        jti = token_data.jti
        
        # Revoke token
        if jti:
            jwt_handler.revoke_token(jti)
            
            # Try to decode again - should fail
            with pytest.raises(HTTPException) as exc_info:
                jwt_handler.decode_token(token)
            
            assert exc_info.value.status_code == 401
            assert "revoked" in exc_info.value.detail.lower()
    
    def test_refresh_access_token(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: Token refresh flow.
        
        Refresh token should generate new token pair.
        """
        # Create initial token pair
        initial_pair = jwt_handler.create_token_pair(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            scopes=sample_user_data["scopes"],
        )
        
        # Refresh using refresh token
        new_pair = jwt_handler.refresh_access_token(
            refresh_token=initial_pair.refresh_token,
        )
        
        # New tokens should be different
        assert new_pair.access_token != initial_pair.access_token
        assert new_pair.refresh_token != initial_pair.refresh_token
        
        # New access token should be valid
        token_data = jwt_handler.decode_token(new_pair.access_token)
        assert token_data.sub == sample_user_data["user_id"]


class TestJWTAlgorithms:
    """Test different JWT algorithms."""
    
    def test_hs256_default(self):
        """Default algorithm should be HS256."""
        from app.auth.oauth2 import JWTHandler
        
        handler = JWTHandler(secret_key="test-key")
        assert handler._algorithm == "HS256"
    
    def test_custom_algorithm(self):
        """Should support custom algorithms."""
        from app.auth.oauth2 import JWTHandler
        
        handler = JWTHandler(secret_key="test-key", algorithm="HS256")
        assert handler._algorithm == "HS256"


# ============================================================================
# TOKEN DATA TESTS
# ============================================================================


class TestTokenData:
    """Test TokenData schema."""
    
    def test_token_data_creation(self):
        """TokenData should validate correctly."""
        from app.auth.oauth2 import TokenData
        
        now = datetime.utcnow()
        token_data = TokenData(
            sub="user_123",
            email="test@example.com",
            scopes=["read", "write"],
            customer_id="cust_456",
            exp=now + timedelta(hours=1),
            iat=now,
        )
        
        assert token_data.sub == "user_123"
        assert token_data.email == "test@example.com"
        assert token_data.scopes == ["read", "write"]
        assert token_data.customer_id == "cust_456"
        assert token_data.iss == "riskcast"
        assert token_data.aud == "riskcast-api"
    
    def test_token_data_defaults(self):
        """TokenData should have sensible defaults."""
        from app.auth.oauth2 import TokenData
        
        now = datetime.utcnow()
        token_data = TokenData(
            sub="user_123",
            exp=now + timedelta(hours=1),
            iat=now,
        )
        
        assert token_data.scopes == []
        assert token_data.email is None
        assert token_data.customer_id is None


# ============================================================================
# OAUTH2 PROVIDER TESTS
# ============================================================================


class TestOAuth2Provider:
    """Test OAuth2 provider integration."""
    
    @pytest.mark.asyncio
    async def test_get_authorization_url(self, oauth2_config):
        """
        B3 COMPLIANCE: Authorization URL generation.
        
        Should generate valid OAuth2 authorization URL.
        """
        from app.auth.oauth2 import OAuth2Provider
        
        provider = OAuth2Provider(config=oauth2_config)
        
        url = await provider.get_authorization_url(
            state="random-state-value",
            redirect_uri="https://app.example.com/callback",
        )
        
        assert "client_id=test-client-id" in url
        assert "response_type=code" in url
        assert "state=random-state-value" in url
        assert "redirect_uri=" in url
        assert oauth2_config.authorization_url in url
    
    @pytest.mark.asyncio
    async def test_exchange_code(self, oauth2_config):
        """
        B3 COMPLIANCE: Authorization code exchange.
        
        Should exchange code for tokens.
        """
        from app.auth.oauth2 import OAuth2Provider
        
        provider = OAuth2Provider(config=oauth2_config)
        
        # Mock the httpx client
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "provider-access-token",
                "refresh_token": "provider-refresh-token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
            
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            tokens = await provider.exchange_code(
                code="authorization-code",
                redirect_uri="https://app.example.com/callback",
            )
            
            assert tokens["access_token"] == "provider-access-token"
            assert tokens["refresh_token"] == "provider-refresh-token"
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, oauth2_config):
        """
        B3 COMPLIANCE: User info retrieval.
        
        Should retrieve user info from provider.
        """
        from app.auth.oauth2 import OAuth2Provider
        
        provider = OAuth2Provider(config=oauth2_config)
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "sub": "google-user-id",
                "email": "user@gmail.com",
                "name": "Test User",
                "given_name": "Test",
                "family_name": "User",
            }
            
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            user_info = await provider.get_user_info("access-token")
            
            assert user_info.sub == "google-user-id"
            assert user_info.email == "user@gmail.com"
            assert user_info.name == "Test User"


class TestOAuth2ProviderFactory:
    """Test OAuth2 provider factory functions."""
    
    def test_create_google_provider(self):
        """Should create Google OAuth2 provider."""
        from app.auth.oauth2 import create_oauth2_provider, SupportedOAuth2Provider
        
        provider = create_oauth2_provider(
            provider=SupportedOAuth2Provider.GOOGLE,
            client_id="test-client-id",
            client_secret="test-client-secret",
        )
        
        assert provider.config.provider == SupportedOAuth2Provider.GOOGLE
        assert "accounts.google.com" in provider.config.authorization_url
    
    def test_create_azure_provider(self):
        """Should create Azure AD OAuth2 provider."""
        from app.auth.oauth2 import create_oauth2_provider, SupportedOAuth2Provider
        
        provider = create_oauth2_provider(
            provider=SupportedOAuth2Provider.AZURE_AD,
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="test-tenant-id",
        )
        
        assert provider.config.provider == SupportedOAuth2Provider.AZURE_AD
        assert "login.microsoftonline.com" in provider.config.authorization_url
        assert "test-tenant-id" in provider.config.authorization_url
    
    def test_create_okta_provider(self):
        """Should create Okta OAuth2 provider."""
        from app.auth.oauth2 import create_oauth2_provider, SupportedOAuth2Provider
        
        provider = create_oauth2_provider(
            provider=SupportedOAuth2Provider.OKTA,
            client_id="test-client-id",
            client_secret="test-client-secret",
            domain="test.okta.com",
        )
        
        assert provider.config.provider == SupportedOAuth2Provider.OKTA
        assert "test.okta.com" in provider.config.authorization_url


# ============================================================================
# FASTAPI DEPENDENCY TESTS
# ============================================================================


class TestFastAPIDependencies:
    """Test FastAPI authentication dependencies."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_jwt_valid(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: JWT authentication dependency.
        
        Should authenticate valid JWT tokens.
        """
        from app.auth.oauth2 import get_current_user_jwt, get_jwt_handler
        from unittest.mock import MagicMock
        
        # Create valid token
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            scopes=sample_user_data["scopes"],
            customer_id=sample_user_data["customer_id"],
        )
        
        # Mock request
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.state = MagicMock()
        
        # Patch JWT handler
        with patch("app.auth.oauth2.get_jwt_handler", return_value=jwt_handler):
            user = await get_current_user_jwt(mock_request, token)
        
        assert user.sub == sample_user_data["user_id"]
        assert user.email == sample_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_jwt_missing(self):
        """Missing token should raise 401."""
        from app.auth.oauth2 import get_current_user_jwt
        from unittest.mock import MagicMock
        
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_jwt(mock_request, None)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_require_scope_jwt_has_scope(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: Scope-based authorization.
        
        Should allow access when user has required scope.
        """
        from app.auth.oauth2 import require_scope_jwt, get_current_user_jwt
        from unittest.mock import MagicMock
        
        # Create token with scope
        token = jwt_handler.create_access_token(
            user_id=sample_user_data["user_id"],
            scopes=["admin", "decisions:read"],
        )
        
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.state = MagicMock()
        
        with patch("app.auth.oauth2.get_jwt_handler", return_value=jwt_handler):
            # Get user
            user = await get_current_user_jwt(mock_request, token)
            
            # Check scope
            check_scope = require_scope_jwt("admin")
            result = await check_scope(user)
            
            assert result.sub == sample_user_data["user_id"]
            assert "admin" in result.scopes
    
    @pytest.mark.asyncio
    async def test_require_scope_jwt_missing_scope(self, jwt_handler, sample_user_data):
        """
        B3 COMPLIANCE: Scope-based authorization.
        
        Should deny access when user lacks required scope.
        """
        from app.auth.oauth2 import require_scope_jwt
        from app.auth.oauth2 import TokenData
        
        # User without admin scope
        user = TokenData(
            sub=sample_user_data["user_id"],
            scopes=["decisions:read"],  # No admin
            exp=datetime.utcnow() + timedelta(hours=1),
            iat=datetime.utcnow(),
        )
        
        check_scope = require_scope_jwt("admin")
        
        with pytest.raises(HTTPException) as exc_info:
            await check_scope(user)
        
        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestOAuth2Flow:
    """Integration tests for complete OAuth2 flow."""
    
    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, oauth2_config, jwt_handler):
        """
        B3 COMPLIANCE: Full OAuth2 authentication flow.
        
        Test complete flow: authorize → callback → tokens.
        """
        from app.auth.oauth2 import OAuth2Provider
        
        provider = OAuth2Provider(config=oauth2_config, jwt_handler=jwt_handler)
        
        # Step 1: Generate authorization URL
        auth_url = await provider.get_authorization_url(
            state="test-state",
            redirect_uri="https://app.example.com/callback",
        )
        
        assert "client_id" in auth_url
        assert "state=test-state" in auth_url
        
        # Step 2: Mock code exchange and user info
        with patch.object(provider, "exchange_code") as mock_exchange:
            with patch.object(provider, "get_user_info") as mock_userinfo:
                from app.auth.oauth2 import UserInfo
                
                mock_exchange.return_value = {
                    "access_token": "provider-access-token",
                    "refresh_token": "provider-refresh-token",
                }
                
                mock_userinfo.return_value = UserInfo(
                    sub="provider-user-id",
                    email="user@example.com",
                    name="Test User",
                    groups=["riskcast-users"],
                )
                
                # Step 3: Complete authentication
                token_pair = await provider.authenticate(
                    code="authorization-code",
                    redirect_uri="https://app.example.com/callback",
                )
        
        # Verify RISKCAST tokens were created
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        
        # Verify token contains user info
        token_data = jwt_handler.decode_token(token_pair.access_token)
        assert token_data.sub == "provider-user-id"
        assert token_data.email == "user@example.com"
        assert "decisions:read" in token_data.scopes  # From riskcast-users group
