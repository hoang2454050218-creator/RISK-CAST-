"""
Pytest Configuration and Fixtures.

Provides reusable fixtures for testing RISKCAST components.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

# Set testing mode before importing app
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/riskcast_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"


# ============================================================================
# EVENT LOOP FIXTURE
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for session scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    from app.core.config import settings
    
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope="session")
async def test_session_factory(test_engine):
    """Create test session factory."""
    factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return factory


@pytest.fixture
async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with rollback."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


# ============================================================================
# HTTP CLIENT FIXTURES
# ============================================================================


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def authenticated_client(test_client, test_api_key) -> AsyncClient:
    """Create authenticated test client."""
    test_client.headers["Authorization"] = f"Bearer {test_api_key}"
    return test_client


# ============================================================================
# API KEY FIXTURES
# ============================================================================


@pytest.fixture
async def api_key_repo():
    """Create in-memory API key repository."""
    from app.db.repositories.api_keys import InMemoryAPIKeyRepository
    return InMemoryAPIKeyRepository()


@pytest.fixture
async def test_api_key(api_key_repo):
    """Create a test API key."""
    from app.db.repositories.api_keys import CreateAPIKeyRequest
    
    request = CreateAPIKeyRequest(
        owner_id="test_customer_001",
        owner_type="customer",
        name="Test API Key",
        scopes=["decisions:read", "decisions:write", "alerts:read"],
        rate_limit_per_minute=1000,
    )
    response = await api_key_repo.create(request)
    return response.raw_key


@pytest.fixture
async def admin_api_key(api_key_repo):
    """Create an admin API key."""
    from app.db.repositories.api_keys import CreateAPIKeyRequest
    
    request = CreateAPIKeyRequest(
        owner_id="admin",
        owner_type="admin",
        name="Admin API Key",
        scopes=["admin"],
        rate_limit_per_minute=10000,
    )
    response = await api_key_repo.create(request)
    return response.raw_key


# ============================================================================
# RATE LIMITER FIXTURES
# ============================================================================


@pytest.fixture
async def rate_limiter():
    """Create in-memory rate limiter."""
    from app.core.rate_limiting import InMemoryRateLimiter
    return InMemoryRateLimiter()


# ============================================================================
# CIRCUIT BREAKER FIXTURES
# ============================================================================


@pytest.fixture
def circuit_breaker():
    """Create test circuit breaker."""
    from app.core.resilience import CircuitBreaker, CircuitBreakerConfig
    
    config = CircuitBreakerConfig(
        failure_threshold=3,
        timeout_seconds=0.1,  # Short timeout for testing
        success_threshold=2,
    )
    return CircuitBreaker("test_service", config)


# ============================================================================
# ENCRYPTION FIXTURES
# ============================================================================


@pytest.fixture
def encryptor():
    """Create test encryptor."""
    from app.core.encryption import FieldEncryptor, KeyManager
    
    key_manager = KeyManager(master_key=b"test_master_key_32bytes_long!!")
    return FieldEncryptor(key_manager)


# ============================================================================
# CUSTOMER FIXTURES
# ============================================================================


@pytest.fixture
def sample_customer():
    """Create sample customer data."""
    return {
        "customer_id": "cust_001",
        "company_name": "Acme Imports",
        "email": "contact@acme.com",
        "phone": "+1234567890",
        "tier": "premium",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_shipments():
    """Create sample shipments."""
    return [
        {
            "shipment_id": "PO-4521",
            "customer_id": "cust_001",
            "cargo_value_usd": 125000,
            "route_chokepoints": ["red_sea", "suez"],
            "container_count": 2,
            "current_status": "in_transit",
            "eta": (datetime.utcnow() + timedelta(days=5)).isoformat(),
        },
        {
            "shipment_id": "PO-4522",
            "customer_id": "cust_001",
            "cargo_value_usd": 110000,
            "route_chokepoints": ["red_sea", "suez"],
            "container_count": 2,
            "current_status": "in_transit",
            "eta": (datetime.utcnow() + timedelta(days=8)).isoformat(),
        },
    ]


# ============================================================================
# SIGNAL FIXTURES
# ============================================================================


@pytest.fixture
def sample_omen_signal():
    """Create sample OMEN signal."""
    return {
        "signal_id": "sig_001",
        "category": "geopolitical",
        "source": "polymarket",
        "headline": "Houthi attacks on Red Sea shipping",
        "description": "Increased Houthi drone and missile attacks on commercial vessels",
        "probability": 0.85,
        "confidence_score": 0.90,
        "chokepoints": ["red_sea"],
        "evidence": [
            {"type": "prediction_market", "source": "Polymarket", "value": "85%"},
            {"type": "news", "source": "Reuters", "value": "3 attacks this week"},
        ],
        "created_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# DECISION FIXTURES
# ============================================================================


@pytest.fixture
def sample_decision():
    """Create sample decision."""
    from app.riskcast.schemas.decision import (
        DecisionObject,
        Action,
        ActionType,
        Urgency,
    )
    
    return DecisionObject(
        decision_id="dec_001",
        customer_id="cust_001",
        q1_what="Houthi attacks impacting your Red Sea shipments",
        q2_when=Urgency.URGENT,
        q2_timeline="Next 48-72 hours",
        q3_severity_level="HIGH",
        q3_exposure_usd=235000.0,
        q3_delay_days=14.0,
        q4_why="Increased Houthi activity with 85% probability of continued attacks",
        q4_evidence=["Polymarket 85%", "3 attacks this week", "Maersk rerouting"],
        q5_action=Action(
            action_type=ActionType.REROUTE,
            action_text="REROUTE via Cape of Good Hope with MSC",
            estimated_cost_usd=8500.0,
            deadline=datetime.utcnow() + timedelta(hours=6),
        ),
        q6_confidence=0.82,
        q6_factors=["High signal correlation", "Historical accuracy 87%"],
        q6_caveats=["Dependent on carrier availability"],
        q7_inaction_cost=15000.0,
        q7_point_of_no_return=datetime.utcnow() + timedelta(hours=12),
    )


# ============================================================================
# MOCK EXTERNAL SERVICE FIXTURES
# ============================================================================


@pytest.fixture
def mock_polymarket_response():
    """Mock Polymarket API response."""
    return {
        "markets": [
            {
                "id": "market_001",
                "question": "Will Houthi attacks disrupt Red Sea shipping in February?",
                "outcomes": ["Yes", "No"],
                "outcomePrices": ["0.85", "0.15"],
                "volume": 1500000,
                "liquidity": 500000,
                "status": "open",
            },
        ],
    }


@pytest.fixture
def mock_ais_response():
    """Mock AIS API response."""
    return {
        "DATA": [
            {
                "MMSI": "123456789",
                "IMO": "9876543",
                "SHIPNAME": "EVER GIVEN",
                "LAT": 27.5,
                "LON": 33.8,
                "SPEED": 12.5,
                "COURSE": 180,
                "SHIP_TYPE": "Container",
                "FLAG": "Panama",
                "DESTINATION": "Rotterdam",
            },
        ],
    }


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
async def cleanup():
    """Clean up after each test."""
    yield
    # Add any cleanup logic here


# ============================================================================
# MARKERS CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "external: Tests requiring external services")
