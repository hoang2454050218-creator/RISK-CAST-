"""
NewsAPI Signal Source Plugin.

Fetches news events from NewsAPI.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
import hashlib

import structlog

from app.plugins.base import (
    SignalSourcePlugin,
    PluginMetadata,
    PluginType,
    PluginStatus,
)

logger = structlog.get_logger(__name__)


class NewsAPISignalPlugin(SignalSourcePlugin):
    """
    NewsAPI news signal source.
    
    Configuration:
    - api_key: NewsAPI API key (required)
    - keywords: List of keywords to track
    - sources: Preferred news sources
    """
    
    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._keywords: List[str] = []
        self._signals_fetched = 0
        self._last_fetch: Optional[datetime] = None
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="newsapi",
            version="1.0.0",
            plugin_type=PluginType.SIGNAL_SOURCE,
            author="RISKCAST",
            description="NewsAPI news event signal source",
            config_schema={
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "base_url": {"type": "string", "default": "https://newsapi.org/v2"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["api_key"],
            },
            required_permissions=["news_read"],
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self._config = config
        
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", "https://newsapi.org/v2")
        
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Api-Key": api_key},
            timeout=30.0,
        )
        
        self._keywords = config.get("keywords", [
            "shipping disruption",
            "port closure",
            "supply chain",
            "Red Sea",
            "Suez Canal",
            "Panama Canal",
        ])
        
        logger.info(
            "newsapi_plugin_initialized",
            keywords=self._keywords,
        )
    
    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch_signals(
        self,
        query: Dict[str, Any],
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch signals from NewsAPI."""
        signals = []
        
        try:
            keywords = query.get("keywords", self._keywords)
            from_date = query.get("from_date", datetime.utcnow() - timedelta(days=7))
            
            # In production, call actual API
            # For now, return structured mock data
            mock_articles = self._get_mock_articles(keywords)
            
            for article in mock_articles[:limit]:
                signal = self._article_to_signal(article)
                signals.append(signal)
            
            self._signals_fetched += len(signals)
            self._last_fetch = datetime.utcnow()
            
            logger.info(
                "newsapi_signals_fetched",
                count=len(signals),
                keywords=keywords,
            )
            
        except Exception as e:
            logger.error(
                "newsapi_fetch_failed",
                error=str(e),
            )
        
        return signals
    
    async def get_signal_by_id(
        self,
        signal_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific article by ID."""
        # NewsAPI doesn't support fetching by ID
        # Return cached signal if available
        return None
    
    async def get_source_status(self) -> Dict[str, Any]:
        """Get NewsAPI source status."""
        return {
            "source": "newsapi",
            "available": self._status == PluginStatus.ACTIVE,
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "signals_fetched": self._signals_fetched,
            "keywords": self._keywords,
        }
    
    def _article_to_signal(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Convert NewsAPI article to OMEN signal."""
        # Generate consistent ID from URL
        article_id = hashlib.sha256(
            article.get("url", "").encode()
        ).hexdigest()[:12]
        
        # Estimate probability and confidence from article
        probability = self._estimate_probability(article)
        confidence = self._estimate_confidence(article)
        
        return {
            "signal_id": f"news_{article_id}",
            "source": "newsapi",
            "event_type": "news_event",
            "title": article.get("title", ""),
            "probability": probability,
            "confidence": confidence,
            "timestamp": article.get("publishedAt", datetime.utcnow().isoformat()),
            "data": {
                "source_name": article.get("source", {}).get("name"),
                "author": article.get("author"),
                "description": article.get("description"),
                "url": article.get("url"),
                "image_url": article.get("urlToImage"),
            },
        }
    
    def _estimate_probability(self, article: Dict[str, Any]) -> float:
        """
        Estimate event probability from article content.
        
        This is a simplified heuristic - in production, use NLP.
        """
        title = (article.get("title") or "").lower()
        desc = (article.get("description") or "").lower()
        
        # Keywords that suggest high probability of disruption
        high_prob_keywords = ["confirmed", "ongoing", "declared", "attack", "blocked"]
        medium_prob_keywords = ["possible", "expected", "warning", "threat"]
        
        for kw in high_prob_keywords:
            if kw in title or kw in desc:
                return 0.8
        
        for kw in medium_prob_keywords:
            if kw in title or kw in desc:
                return 0.5
        
        return 0.3  # Default low probability
    
    def _estimate_confidence(self, article: Dict[str, Any]) -> float:
        """
        Estimate confidence based on source quality.
        """
        source_name = article.get("source", {}).get("name", "").lower()
        
        # Tier 1 sources
        tier1 = ["reuters", "bloomberg", "financial times", "wall street journal"]
        if any(s in source_name for s in tier1):
            return 0.9
        
        # Tier 2 sources
        tier2 = ["bbc", "cnn", "associated press", "guardian"]
        if any(s in source_name for s in tier2):
            return 0.75
        
        return 0.5  # Unknown source
    
    def _get_mock_articles(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Get mock articles for testing."""
        return [
            {
                "source": {"id": "reuters", "name": "Reuters"},
                "author": "Jonathan Saul",
                "title": "Red Sea shipping disruptions expected to continue into 2025",
                "description": "Major shipping companies confirm ongoing rerouting around Cape of Good Hope",
                "url": "https://reuters.com/shipping/red-sea-2025",
                "urlToImage": "https://example.com/image.jpg",
                "publishedAt": datetime.utcnow().isoformat(),
            },
            {
                "source": {"id": "bloomberg", "name": "Bloomberg"},
                "author": "Staff",
                "title": "Panama Canal restrictions ease as rainfall returns",
                "description": "El Niño effects diminishing, transit limits being relaxed",
                "url": "https://bloomberg.com/panama-canal-ease",
                "publishedAt": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
            },
            {
                "source": {"id": "ft", "name": "Financial Times"},
                "author": "Shipping Desk",
                "title": "Container rates surge amid continued supply chain volatility",
                "description": "Spot rates from Asia to Europe up 45% month-over-month",
                "url": "https://ft.com/container-rates",
                "publishedAt": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            },
        ]


# For dynamic loading
Plugin = NewsAPISignalPlugin
