"""
Built-in RISKCAST Plugins.

These are the default plugins that come with RISKCAST:

Signal Sources:
- Polymarket (prediction markets)
- NewsAPI (news events)

Action Types:
- Reroute (route cargo around disruptions)
- Delay (hold cargo until safe)
- Insure (add additional coverage)

Delivery:
- WhatsApp (via Twilio)
- Email (via SendGrid)
"""

from app.plugins.builtin.signal_sources import (
    PolymarketSignalPlugin,
    NewsAPISignalPlugin,
)
from app.plugins.builtin.action_types import (
    RerouteActionPlugin,
    DelayActionPlugin,
    InsureActionPlugin,
)

__all__ = [
    # Signal sources
    "PolymarketSignalPlugin",
    "NewsAPISignalPlugin",
    # Action types
    "RerouteActionPlugin",
    "DelayActionPlugin",
    "InsureActionPlugin",
]
