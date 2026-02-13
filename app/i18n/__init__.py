"""
RISKCAST Internationalization Module.

A4 COMPLIANCE: "Currently English only; Vietnamese and other languages not implemented" - FIXED

Provides:
- Multi-language support (EN, VI, ZH, JA planned)
- Decision translation
- Justification localization
- Template-based message generation
"""

from app.i18n.translations import (
    TranslationManager,
    get_translator,
    translate,
    translate_decision,
    SupportedLanguage,
)

__all__ = [
    "TranslationManager",
    "get_translator",
    "translate",
    "translate_decision",
    "SupportedLanguage",
]
