"""
Tests for Multi-language Support.

A4 COMPLIANCE: Validates multi-language implementation.

Tests:
- English translations
- Vietnamese translations
- Translation fallback
- Template interpolation
"""
import pytest
from datetime import datetime

from app.i18n.translations import (
    TranslationManager,
    SupportedLanguage,
    get_translator,
    translate,
    EN_TRANSLATIONS,
    VI_TRANSLATIONS,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def translator():
    """Create fresh translation manager."""
    return TranslationManager()


# ============================================================================
# BASIC TRANSLATION TESTS
# ============================================================================


class TestBasicTranslation:
    """Test basic translation functionality."""
    
    def test_translate_simple_key_english(self, translator):
        """
        A4 COMPLIANCE: English translation works.
        
        Simple key lookup should return correct translation.
        """
        result = translator.translate("actions.reroute", "en")
        assert result == "REROUTE"
    
    def test_translate_simple_key_vietnamese(self, translator):
        """
        A4 COMPLIANCE: Vietnamese translation works.
        
        Simple key lookup should return Vietnamese text.
        """
        result = translator.translate("actions.reroute", "vi")
        assert result == "CHUYỂN HƯỚNG"
    
    def test_translate_nested_key(self, translator):
        """Nested key lookup should work."""
        result = translator.translate("confidence.high", "en")
        assert result == "High"
        
        result_vi = translator.translate("confidence.high", "vi")
        assert result_vi == "Cao"
    
    def test_translate_urgency_levels(self, translator):
        """All urgency levels should translate."""
        urgencies = ["immediate", "urgent", "soon", "watch"]
        
        for urgency in urgencies:
            en = translator.translate(f"urgency.{urgency}", "en")
            vi = translator.translate(f"urgency.{urgency}", "vi")
            
            assert en != f"urgency.{urgency}", f"Missing EN translation for {urgency}"
            assert vi != f"urgency.{urgency}", f"Missing VI translation for {urgency}"
            assert en != vi, f"EN and VI should differ for {urgency}"


class TestTranslationFallback:
    """Test fallback behavior."""
    
    def test_fallback_to_default_language(self, translator):
        """Unknown language should fall back to English."""
        result = translator.translate("actions.reroute", "xx")  # Unknown language
        assert result == "REROUTE"  # Falls back to English
    
    def test_fallback_to_key_if_not_found(self, translator):
        """Missing key should return the key itself."""
        result = translator.translate("nonexistent.key", "en")
        assert result == "nonexistent.key"
    
    def test_fallback_with_default_value(self, translator):
        """Should use provided default if key not found."""
        result = translator.translate(
            "nonexistent.key",
            "en",
            default="Default Value"
        )
        assert result == "Default Value"


class TestTemplateInterpolation:
    """Test variable interpolation in translations."""
    
    def test_interpolate_single_variable(self, translator):
        """Single variable interpolation should work."""
        result = translator.translate(
            "decision.generated_at",
            "en",
            timestamp="2024-01-15 10:30:00"
        )
        assert "2024-01-15 10:30:00" in result
    
    def test_interpolate_multiple_variables(self, translator):
        """Multiple variables should be interpolated."""
        result = translator.translate(
            "export.page",
            "en",
            page=1,
            total=10
        )
        assert "1" in result
        assert "10" in result
    
    def test_interpolate_currency_values(self, translator):
        """Currency values should be interpolated."""
        # The executive summary uses currency formatting
        result = translator.translate(
            "questions.q3_severity",
            "en",
            exposure="$100,000",
            delay_days=5,
            shipment_count=10
        )
        assert "$100,000" in result
        assert "5" in result
        assert "10" in result
    
    def test_interpolate_missing_variable(self, translator):
        """Missing variable should not crash."""
        # Should handle gracefully (not raise exception)
        result = translator.translate(
            "export.page",
            "en",
            page=1
            # Missing 'total' variable
        )
        # Should return something (may have placeholder still)
        assert result is not None


# ============================================================================
# ACTION TRANSLATION TESTS
# ============================================================================


class TestActionTranslations:
    """Test action type translations."""
    
    @pytest.mark.parametrize("action,expected_en,expected_vi", [
        ("reroute", "REROUTE", "CHUYỂN HƯỚNG"),
        ("expedite", "EXPEDITE", "TĂNG TỐC"),
        ("hold", "HOLD", "TẠM GIỮ"),
        ("delay", "DELAY", "TRÌ HOÃN"),
        ("insure", "INSURE", "MUA BẢO HIỂM"),
        ("monitor", "MONITOR", "THEO DÕI"),
        ("do_nothing", "NO ACTION", "KHÔNG HÀNH ĐỘNG"),
    ])
    def test_action_translations(self, translator, action, expected_en, expected_vi):
        """
        A4 COMPLIANCE: All action types translate correctly.
        """
        assert translator.translate(f"actions.{action}", "en") == expected_en
        assert translator.translate(f"actions.{action}", "vi") == expected_vi


# ============================================================================
# CHOKEPOINT TRANSLATION TESTS
# ============================================================================


class TestChokepointTranslations:
    """Test chokepoint translations."""
    
    @pytest.mark.parametrize("chokepoint,expected_en,expected_vi", [
        ("red_sea", "Red Sea", "Biển Đỏ"),
        ("suez", "Suez Canal", "Kênh đào Suez"),
        ("panama", "Panama Canal", "Kênh đào Panama"),
        ("malacca", "Strait of Malacca", "Eo biển Malacca"),
    ])
    def test_chokepoint_translations(self, translator, chokepoint, expected_en, expected_vi):
        """
        A4 COMPLIANCE: Chokepoint names translate correctly.
        """
        assert translator.translate(f"chokepoints.{chokepoint}", "en") == expected_en
        assert translator.translate(f"chokepoints.{chokepoint}", "vi") == expected_vi


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_get_translator_singleton(self):
        """get_translator should return same instance."""
        t1 = get_translator()
        t2 = get_translator()
        assert t1 is t2
    
    def test_translate_function(self):
        """translate function should work."""
        result = translate("actions.reroute", "en")
        assert result == "REROUTE"
        
        result_vi = translate("actions.reroute", "vi")
        assert result_vi == "CHUYỂN HƯỚNG"


# ============================================================================
# SUPPORTED LANGUAGES TESTS
# ============================================================================


class TestSupportedLanguages:
    """Test language support information."""
    
    def test_supported_languages_list(self, translator):
        """Should return list of supported languages."""
        languages = translator.get_supported_languages()
        
        assert len(languages) >= 2
        
        codes = [lang["code"] for lang in languages]
        assert "en" in codes
        assert "vi" in codes
    
    def test_language_info_contains_names(self, translator):
        """Language info should include names."""
        languages = translator.get_supported_languages()
        
        for lang in languages:
            assert "code" in lang
            assert "name" in lang
            assert "native_name" in lang


# ============================================================================
# BUILT-IN TRANSLATIONS TESTS
# ============================================================================


class TestBuiltInTranslations:
    """Test that built-in translations are complete."""
    
    def test_en_translations_has_required_sections(self):
        """English translations should have all required sections."""
        required_sections = [
            "decision",
            "questions",
            "actions",
            "confidence",
            "urgency",
            "events",
            "chokepoints",
            "export",
            "escalation",
        ]
        
        for section in required_sections:
            assert section in EN_TRANSLATIONS, f"Missing section: {section}"
    
    def test_vi_translations_has_required_sections(self):
        """Vietnamese translations should have all required sections."""
        required_sections = [
            "decision",
            "questions",
            "actions",
            "confidence",
            "urgency",
            "events",
            "chokepoints",
            "export",
            "escalation",
        ]
        
        for section in required_sections:
            assert section in VI_TRANSLATIONS, f"Missing VI section: {section}"
    
    def test_translations_parity(self):
        """EN and VI should have same keys."""
        def get_all_keys(d, prefix=""):
            keys = []
            for k, v in d.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys.extend(get_all_keys(v, full_key))
                else:
                    keys.append(full_key)
            return keys
        
        en_keys = set(get_all_keys(EN_TRANSLATIONS))
        vi_keys = set(get_all_keys(VI_TRANSLATIONS))
        
        missing_in_vi = en_keys - vi_keys
        missing_in_en = vi_keys - en_keys
        
        # Allow some difference but flag major gaps
        assert len(missing_in_vi) < 5, f"VI missing keys: {missing_in_vi}"
        assert len(missing_in_en) < 5, f"EN missing keys: {missing_in_en}"
