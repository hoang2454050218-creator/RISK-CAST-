"""
Suggestion Extractor — ORM-based for cross-database compatibility.
"""

import re
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import AiSuggestion

logger = structlog.get_logger(__name__)

SUGGESTION_PATTERN = re.compile(
    r"\[SUGGESTION:(\w+)\]\s*(.+?)\s*\[/SUGGESTION\]", re.DOTALL
)


class SuggestionExtractor:
    """Extract and persist AI suggestions from responses."""

    async def extract_and_save(
        self,
        session: AsyncSession,
        company_id: str,
        message_id: str,
        ai_response: str,
    ) -> list[dict]:
        suggestions = []

        for match in SUGGESTION_PATTERN.finditer(ai_response):
            suggestion_type = match.group(1)
            suggestion_text = match.group(2).strip()

            suggestion = AiSuggestion(
                company_id=uuid.UUID(company_id),
                message_id=uuid.UUID(message_id),
                suggestion_type=suggestion_type,
                suggestion_text=suggestion_text,
            )
            session.add(suggestion)
            await session.flush()

            suggestions.append({
                "id": str(suggestion.id),
                "type": suggestion_type,
                "text": suggestion_text,
            })

        if suggestions:
            logger.info(
                "suggestions_extracted",
                company_id=company_id,
                count=len(suggestions),
            )

        return suggestions

    def clean_response(self, text: str) -> str:
        """Remove [SUGGESTION:...][/SUGGESTION] tags, keep inner text."""
        return SUGGESTION_PATTERN.sub(r"\2", text)
