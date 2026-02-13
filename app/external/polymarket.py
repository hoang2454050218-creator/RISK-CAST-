"""
Polymarket API Client.

Production-grade client for Polymarket prediction markets with:
- Async HTTP with httpx
- Circuit breaker protection
- Rate limiting
- Retry logic
- Response caching
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import httpx
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings
from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    ResilientCall,
    RetryConfig,
)
from app.core.metrics import RECORDER
from app.core.rate_limiting import rate_limit_context

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class PolymarketConfig:
    """Polymarket API configuration."""
    
    base_url: str = "https://gamma-api.polymarket.com"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    cache_ttl_seconds: int = 300  # 5 minutes
    rate_limit_per_minute: int = 30


# ============================================================================
# MODELS
# ============================================================================


class MarketStatus(str, Enum):
    """Market status values."""
    
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"


class Market(BaseModel):
    """Polymarket market."""
    
    id: str
    question: str
    description: Optional[str] = None
    slug: str
    status: MarketStatus
    volume: float = 0
    liquidity: float = 0
    created_at: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Outcome data
    outcomes: List[str] = Field(default_factory=list)
    outcome_prices: Dict[str, float] = Field(default_factory=dict)
    
    # Resolution
    resolved_outcome: Optional[str] = None
    resolved_at: Optional[datetime] = None


class MarketEvent(BaseModel):
    """Event with multiple markets."""
    
    id: str
    title: str
    slug: str
    description: Optional[str] = None
    markets: List[Market] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class PriceHistory(BaseModel):
    """Price history for a market."""
    
    market_id: str
    outcome: str
    points: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# CLIENT
# ============================================================================


class PolymarketClient:
    """
    Async client for Polymarket API.
    
    Features:
    - Circuit breaker for fault tolerance
    - Automatic retries with exponential backoff
    - Request rate limiting
    - Response caching
    """
    
    def __init__(
        self,
        config: Optional[PolymarketConfig] = None,
    ):
        self.config = config or PolymarketConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._circuit_breaker = CircuitBreakerRegistry.get_or_create("polymarket")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "RISKCAST/1.0",
                },
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, cached_at = self._cache[key]
            if datetime.utcnow() - cached_at < timedelta(seconds=self.config.cache_ttl_seconds):
                return value
            del self._cache[key]
        return None
    
    def _set_cached(self, key: str, value: Any) -> None:
        """Set cached value."""
        self._cache[key] = (value, datetime.utcnow())
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Make an API request with resilience patterns."""
        cache_key = f"{method}:{path}:{params}"
        
        # Check cache
        if use_cache and method == "GET":
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.debug("polymarket_cache_hit", path=path)
                return cached
        
        async def do_request() -> Dict[str, Any]:
            client = await self._get_client()
            
            start = datetime.utcnow()
            response = await client.request(method, path, params=params)
            response.raise_for_status()
            
            # Record metrics
            latency = (datetime.utcnow() - start).total_seconds()
            RECORDER.record_api_call(
                service="polymarket",
                endpoint=path,
                status=str(response.status_code),
                latency_seconds=latency,
            )
            
            return response.json()
        
        # Apply rate limiting
        async with rate_limit_context(
            f"polymarket:api",
            limit=self.config.rate_limit_per_minute,
            window_seconds=60,
        ):
            # Execute with resilience
            result = await (
                ResilientCall(do_request)
                .with_circuit_breaker(self._circuit_breaker)
                .with_retry(RetryConfig(
                    max_attempts=self.config.max_retries,
                    retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
                ))
                .with_timeout(self.config.timeout_seconds)
                .execute()
            )
        
        # Cache successful GET responses
        if use_cache and method == "GET":
            self._set_cached(cache_key, result)
        
        return result
    
    # ========================================================================
    # PUBLIC METHODS
    # ========================================================================
    
    async def search_markets(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        status: Optional[MarketStatus] = None,
    ) -> List[Market]:
        """
        Search for markets by keyword.
        
        Args:
            query: Search query
            limit: Max results
            offset: Pagination offset
            status: Filter by status
        
        Returns:
            List of matching markets
        """
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        if status:
            params["status"] = status.value
        
        try:
            data = await self._request("GET", "/markets", params=params)
            markets = [self._parse_market(m) for m in data.get("markets", [])]
            
            logger.info(
                "polymarket_search_complete",
                query=query,
                results=len(markets),
            )
            
            return markets
        
        except Exception as e:
            logger.error("polymarket_search_failed", query=query, error=str(e))
            raise
    
    async def get_market(self, market_id: str) -> Optional[Market]:
        """
        Get a specific market by ID.
        
        Args:
            market_id: Market identifier
        
        Returns:
            Market if found, None otherwise
        """
        try:
            data = await self._request("GET", f"/markets/{market_id}")
            return self._parse_market(data)
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def get_markets_by_tag(
        self,
        tag: str,
        limit: int = 50,
    ) -> List[Market]:
        """
        Get markets by tag/category.
        
        Useful for finding geopolitical markets related to supply chain.
        
        Args:
            tag: Tag to filter by (e.g., "geopolitics", "trade")
            limit: Max results
        
        Returns:
            List of markets with the tag
        """
        params = {
            "tag": tag,
            "limit": limit,
            "active": True,
        }
        
        data = await self._request("GET", "/markets", params=params)
        return [self._parse_market(m) for m in data.get("markets", [])]
    
    async def get_supply_chain_markets(self) -> List[Market]:
        """
        Get markets relevant to supply chain disruptions.
        
        Searches for markets related to:
        - Red Sea / Suez
        - Panama Canal
        - Trade conflicts
        - Shipping disruptions
        
        Returns:
            List of relevant markets
        """
        keywords = [
            "Red Sea",
            "Suez Canal",
            "Houthi",
            "Panama Canal",
            "shipping",
            "trade war",
            "sanctions",
            "supply chain",
        ]
        
        all_markets = []
        seen_ids = set()
        
        for keyword in keywords:
            try:
                markets = await self.search_markets(keyword, limit=20)
                for market in markets:
                    if market.id not in seen_ids:
                        all_markets.append(market)
                        seen_ids.add(market.id)
            except Exception as e:
                logger.warning(
                    "polymarket_keyword_search_failed",
                    keyword=keyword,
                    error=str(e),
                )
        
        # Sort by volume/liquidity
        all_markets.sort(key=lambda m: m.volume, reverse=True)
        
        logger.info(
            "polymarket_supply_chain_markets",
            total_markets=len(all_markets),
        )
        
        return all_markets
    
    async def get_price_history(
        self,
        market_id: str,
        outcome: str = "Yes",
        fidelity: int = 60,  # Minutes
    ) -> PriceHistory:
        """
        Get price history for a market outcome.
        
        Args:
            market_id: Market identifier
            outcome: Outcome to get prices for
            fidelity: Time interval in minutes
        
        Returns:
            Price history data
        """
        params = {
            "market": market_id,
            "outcome": outcome,
            "fidelity": fidelity,
        }
        
        data = await self._request("GET", "/prices-history", params=params)
        
        return PriceHistory(
            market_id=market_id,
            outcome=outcome,
            points=data.get("history", []),
        )
    
    def _parse_market(self, data: Dict[str, Any]) -> Market:
        """Parse market data from API response."""
        outcomes = data.get("outcomes", ["Yes", "No"])
        outcome_prices = {}
        
        # Parse outcome prices
        if "outcomePrices" in data:
            for i, price in enumerate(data["outcomePrices"]):
                if i < len(outcomes):
                    outcome_prices[outcomes[i]] = float(price)
        
        return Market(
            id=data.get("id", data.get("conditionId", "")),
            question=data.get("question", ""),
            description=data.get("description"),
            slug=data.get("slug", ""),
            status=MarketStatus(data.get("status", "open").lower()),
            volume=float(data.get("volume", 0)),
            liquidity=float(data.get("liquidity", 0)),
            outcomes=outcomes,
            outcome_prices=outcome_prices,
            created_at=self._parse_datetime(data.get("createdAt")),
            end_date=self._parse_datetime(data.get("endDate")),
            resolved_outcome=data.get("resolvedOutcome"),
            resolved_at=self._parse_datetime(data.get("resolvedAt")),
        )
    
    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse datetime from API response."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None


# ============================================================================
# FACTORY
# ============================================================================

_client: Optional[PolymarketClient] = None


def get_polymarket_client() -> PolymarketClient:
    """Get the global Polymarket client instance."""
    global _client
    if _client is None:
        _client = PolymarketClient()
    return _client


async def close_polymarket_client() -> None:
    """Close the global Polymarket client."""
    global _client
    if _client:
        await _client.close()
        _client = None
