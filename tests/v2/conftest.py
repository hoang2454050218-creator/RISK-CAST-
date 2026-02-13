"""
Test fixtures for RiskCast V2 tests.

Provides:
- Async DB session fixture (SQLite in-memory for speed)
- Company/User fixtures with multiple roles
- API key fixtures for service-to-service testing
- Authenticated FastAPI test client
- Sample data factories
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from riskcast.auth.api_keys import generate_api_key, hash_api_key
from riskcast.auth.jwt import create_access_token
from riskcast.db.engine import Base
from riskcast.db.models import (  # noqa: F401 — register all models
    Alert,
    AlertRuleModel,
    APIKey,
    AiSuggestion,
    ChatMessage,
    ChatSession,
    Company,
    Customer,
    Incident,
    MorningBrief,
    OmenIngestSignal,
    Order,
    Outcome,
    Payment,
    ReconcileLog,
    RiskAppetiteProfile,
    Route,
    SecurityAuditLog,
    Signal,
    SignalLedger,
    SuggestionFeedback,
    User,
)

# In-memory SQLite for fast, isolated tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine with all tables."""
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(engine):
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean DB session per test."""
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── Company Fixtures ─────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def company_a(session_factory) -> Company:
    """Create test Company A."""
    async with session_factory() as session:
        company = Company(
            id=uuid.uuid4(),
            name="Company Alpha",
            slug=f"alpha-{uuid.uuid4().hex[:8]}",
            industry="logistics",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)
        return company


@pytest_asyncio.fixture
async def company_b(session_factory) -> Company:
    """Create test Company B."""
    async with session_factory() as session:
        company = Company(
            id=uuid.uuid4(),
            name="Company Beta",
            slug=f"beta-{uuid.uuid4().hex[:8]}",
            industry="shipping",
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)
        return company


# ── User Fixtures (one per role) ─────────────────────────────────────────


async def _create_user(session_factory, company: Company, role: str) -> User:
    """Helper: create a user with a specific role."""
    async with session_factory() as session:
        user = User(
            id=uuid.uuid4(),
            company_id=company.id,
            email=f"{role}-{uuid.uuid4().hex[:8]}@test.com",
            password_hash="$2b$12$fakehashfortest",
            name=f"Test {role.capitalize()}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def viewer_user(session_factory, company_a) -> User:
    return await _create_user(session_factory, company_a, "viewer")


@pytest_asyncio.fixture
async def analyst_user(session_factory, company_a) -> User:
    return await _create_user(session_factory, company_a, "analyst")


@pytest_asyncio.fixture
async def manager_user(session_factory, company_a) -> User:
    return await _create_user(session_factory, company_a, "manager")


@pytest_asyncio.fixture
async def admin_user(session_factory, company_a) -> User:
    return await _create_user(session_factory, company_a, "admin")


@pytest_asyncio.fixture
async def owner_user(session_factory, company_a) -> User:
    return await _create_user(session_factory, company_a, "owner")


# ── JWT Token Fixtures ──────────────────────────────────────────────────


def _make_token(user: User) -> str:
    return create_access_token(
        user_id=str(user.id),
        company_id=str(user.company_id),
        email=user.email,
        role=user.role,
    )


@pytest.fixture
def viewer_token(viewer_user) -> str:
    return _make_token(viewer_user)


@pytest.fixture
def analyst_token(analyst_user) -> str:
    return _make_token(analyst_user)


@pytest.fixture
def manager_token(manager_user) -> str:
    return _make_token(manager_user)


@pytest.fixture
def admin_token(admin_user) -> str:
    return _make_token(admin_user)


@pytest.fixture
def owner_token(owner_user) -> str:
    return _make_token(owner_user)


# ── API Key Fixtures ───────────────────────────────────────────────────


@pytest_asyncio.fixture
async def valid_api_key(session_factory, company_a) -> tuple[str, APIKey]:
    """Create a valid API key for company_a with full scopes."""
    full_key, key_hash, key_prefix = generate_api_key()
    async with session_factory() as session:
        api_key = APIKey(
            id=uuid.uuid4(),
            company_id=company_a.id,
            key_name="test-omen-key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=["signals:ingest", "reconcile:run"],
            is_active=True,
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return full_key, api_key


@pytest_asyncio.fixture
async def expired_api_key(session_factory, company_a) -> tuple[str, APIKey]:
    """Create an expired API key."""
    full_key, key_hash, key_prefix = generate_api_key()
    async with session_factory() as session:
        api_key = APIKey(
            id=uuid.uuid4(),
            company_id=company_a.id,
            key_name="expired-key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=["signals:ingest"],
            is_active=True,
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),  # expired
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return full_key, api_key


@pytest_asyncio.fixture
async def revoked_api_key(session_factory, company_a) -> tuple[str, APIKey]:
    """Create a revoked (inactive) API key."""
    full_key, key_hash, key_prefix = generate_api_key()
    async with session_factory() as session:
        api_key = APIKey(
            id=uuid.uuid4(),
            company_id=company_a.id,
            key_name="revoked-key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=["signals:ingest"],
            is_active=False,
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return full_key, api_key


# ── Sample Data Helpers ──────────────────────────────────────────────────


async def create_customer(
    session: AsyncSession, company_id: uuid.UUID, name: str, **kwargs
) -> Customer:
    """Helper: create a customer in a given company."""
    customer = Customer(
        company_id=company_id,
        name=name,
        code=kwargs.get("code", f"C-{uuid.uuid4().hex[:6]}"),
        tier=kwargs.get("tier", "standard"),
    )
    session.add(customer)
    await session.flush()
    return customer


async def create_order(
    session: AsyncSession,
    company_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
    **kwargs,
) -> Order:
    """Helper: create an order in a given company."""
    order = Order(
        company_id=company_id,
        customer_id=customer_id,
        order_number=kwargs.get("order_number", f"ORD-{uuid.uuid4().hex[:8]}"),
        status=kwargs.get("status", "pending"),
        total_value=kwargs.get("total_value", 1000000),
    )
    session.add(order)
    await session.flush()
    return order


async def create_chat_session(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    **kwargs,
) -> "ChatSession":
    """Helper: create a chat session in a given company."""
    from riskcast.db.models import ChatSession
    chat_session = ChatSession(
        company_id=company_id,
        user_id=user_id or uuid.uuid4(),
        title=kwargs.get("title", "Test Session"),
    )
    session.add(chat_session)
    await session.flush()
    return chat_session


async def create_chat_message(
    session: AsyncSession,
    session_id: uuid.UUID,
    company_id: uuid.UUID,
    content: str = "Test message",
    **kwargs,
) -> "ChatMessage":
    """Helper: create a chat message."""
    from riskcast.db.models import ChatMessage
    msg = ChatMessage(
        session_id=session_id,
        company_id=company_id,
        role=kwargs.get("role", "user"),
        content=content,
    )
    session.add(msg)
    await session.flush()
    return msg
