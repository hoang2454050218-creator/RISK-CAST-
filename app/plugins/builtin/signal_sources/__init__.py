"""
Built-in Signal Source Plugins.
"""

from app.plugins.builtin.signal_sources.polymarket import PolymarketSignalPlugin
from app.plugins.builtin.signal_sources.newsapi import NewsAPISignalPlugin

__all__ = [
    "PolymarketSignalPlugin",
    "NewsAPISignalPlugin",
]
