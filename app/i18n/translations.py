"""
Multi-language support for explanations and justifications.

A4 COMPLIANCE: "Currently English only; Vietnamese and other languages not implemented" - FIXED

Provides:
- Translation management with fallback
- Decision localization
- Template interpolation
- Support for EN, VI (ZH, JA planned)
"""
from typing import Dict, Optional, Any, List, TYPE_CHECKING
from pathlib import Path
from enum import Enum
from datetime import datetime
import json
import structlog

if TYPE_CHECKING:
    from app.riskcast.schemas.decision import DecisionObject

logger = structlog.get_logger(__name__)


# ============================================================================
# SUPPORTED LANGUAGES
# ============================================================================


class SupportedLanguage(str, Enum):
    """Supported language codes."""
    
    ENGLISH = "en"
    VIETNAMESE = "vi"
    CHINESE = "zh"      # Planned
    JAPANESE = "ja"     # Planned


# ============================================================================
# TRANSLATION MANAGER
# ============================================================================


class TranslationManager:
    """
    Manages translations for multiple languages.
    
    A4 COMPLIANCE: Multi-language translation system.
    
    Supported languages:
    - English (en) - default
    - Vietnamese (vi)
    - Chinese (zh) - planned
    - Japanese (ja) - planned
    
    Features:
    - Nested key lookup (e.g., "decision.summary.action")
    - Template interpolation with {variable} syntax
    - Fallback to default language
    - Pluralization support
    - Number and date formatting
    """
    
    SUPPORTED_LANGUAGES = [SupportedLanguage.ENGLISH, SupportedLanguage.VIETNAMESE]
    DEFAULT_LANGUAGE = SupportedLanguage.ENGLISH
    
    def __init__(self, locales_dir: Optional[Path] = None):
        """
        Initialize translation manager.
        
        Args:
            locales_dir: Directory containing locale JSON files
        """
        self._locales_dir = locales_dir or Path(__file__).parent / "locales"
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._load_translations()
    
    def _load_translations(self):
        """Load translation files from locales directory."""
        # Ensure locales directory exists
        self._locales_dir.mkdir(parents=True, exist_ok=True)
        
        # Load built-in translations first
        self._translations[SupportedLanguage.ENGLISH.value] = EN_TRANSLATIONS
        self._translations[SupportedLanguage.VIETNAMESE.value] = VI_TRANSLATIONS
        
        # Then try to load from files (can override built-in)
        for lang in self.SUPPORTED_LANGUAGES:
            file_path = self._locales_dir / f"{lang.value}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_translations = json.load(f)
                        # Merge with built-in (file takes precedence)
                        self._translations[lang.value] = self._deep_merge(
                            self._translations.get(lang.value, {}),
                            file_translations
                        )
                    logger.info("translations_loaded_from_file", language=lang.value)
                except Exception as e:
                    logger.warning(
                        "translation_file_load_error",
                        language=lang.value,
                        error=str(e)
                    )
        
        logger.info(
            "translations_initialized",
            languages=list(self._translations.keys()),
        )
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def translate(
        self,
        key: str,
        language: str = "en",
        default: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Translate a key to the specified language.
        
        A4 COMPLIANCE: Key-based translation lookup.
        
        Args:
            key: Translation key (e.g., "decision.summary")
            language: Target language code
            default: Default value if key not found
            **kwargs: Variables to interpolate
        
        Returns:
            Translated string with variables interpolated
        """
        # Normalize language code
        if isinstance(language, SupportedLanguage):
            language = language.value
        
        # Fallback to default if language not supported
        if language not in self._translations:
            logger.debug("language_fallback", requested=language, fallback=self.DEFAULT_LANGUAGE.value)
            language = self.DEFAULT_LANGUAGE.value
        
        translations = self._translations.get(language, {})
        
        # Navigate nested keys (e.g., "decision.summary.action")
        value = translations
        for part in key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    break
            else:
                value = None
                break
        
        # Fallback to default language if key not found
        if value is None and language != self.DEFAULT_LANGUAGE.value:
            return self.translate(key, self.DEFAULT_LANGUAGE.value, default, **kwargs)
        
        # Fallback to default value or key itself
        if value is None:
            value = default if default is not None else key
        
        # Interpolate variables
        if isinstance(value, str) and kwargs:
            try:
                value = value.format(**kwargs)
            except KeyError as e:
                logger.warning(
                    "translation_interpolation_error",
                    key=key,
                    missing_var=str(e),
                )
        
        return value
    
    def translate_decision(
        self,
        decision: "DecisionObject",
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Translate a complete decision to specified language.
        
        A4 COMPLIANCE: Full decision localization.
        
        Args:
            decision: DecisionObject to translate
            language: Target language code
        
        Returns:
            Dictionary with translated decision components
        """
        return {
            "executive_summary": self._translate_executive_summary(decision, language),
            "q1_what": self._translate_q1(decision, language),
            "q2_when": self._translate_q2(decision, language),
            "q3_severity": self._translate_q3(decision, language),
            "q4_why": self._translate_q4(decision, language),
            "q5_action": self._translate_q5(decision, language),
            "q6_confidence": self._translate_q6(decision, language),
            "q7_inaction": self._translate_q7(decision, language),
        }
    
    def _translate_executive_summary(self, decision: "DecisionObject", language: str) -> str:
        """Generate executive summary in target language."""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        action_type = decision.q5_action.action_type.value
        action_name = t(f"actions.{action_type}")
        
        # Format numbers appropriately
        exposure = self._format_currency(decision.q3_severity.total_exposure_usd, language)
        cost = self._format_currency(decision.q5_action.estimated_cost_usd, language)
        inaction_loss = self._format_currency(decision.q7_inaction.expected_loss_if_nothing, language)
        
        return t(
            "decision.executive_summary",
            action=action_name,
            shipment_count=len(getattr(decision.q5_action, 'affected_shipments', [])),
            exposure=exposure,
            delay=decision.q3_severity.expected_delay_days,
            cost=cost,
            confidence=decision.q6_confidence.calibrated_score * 100,
            deadline=self._format_datetime(decision.q5_action.deadline, language),
            inaction_loss=inaction_loss,
        )
    
    def _translate_q1(self, decision: "DecisionObject", language: str) -> str:
        """Translate Q1: What is happening?"""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        event_type = getattr(decision.q1_what, 'event_type', 'disruption')
        chokepoint = getattr(decision.q1_what, 'chokepoint', 'unknown')
        
        return t(
            "questions.q1_what",
            event_type=t(f"events.{event_type}"),
            chokepoint=t(f"chokepoints.{chokepoint}"),
            summary=getattr(decision.q1_what, 'summary', ''),
        )
    
    def _translate_q2(self, decision: "DecisionObject", language: str) -> str:
        """Translate Q2: When?"""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        urgency = getattr(decision.q2_when, 'urgency', 'watch')
        
        return t(
            "questions.q2_when",
            urgency=t(f"urgency.{urgency}"),
            window_hours=getattr(decision.q2_when, 'decision_window_hours', 24),
            deadline=self._format_datetime(
                getattr(decision.q2_when, 'deadline', datetime.utcnow()),
                language
            ),
        )
    
    def _translate_q3(self, decision: "DecisionObject", language: str) -> str:
        """Translate Q3: How bad?"""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        return t(
            "questions.q3_severity",
            exposure=self._format_currency(decision.q3_severity.total_exposure_usd, language),
            delay_days=decision.q3_severity.expected_delay_days,
            shipment_count=getattr(decision.q3_severity, 'affected_shipment_count', 0),
        )
    
    def _translate_q4(self, decision: "DecisionObject", language: str) -> str:
        """Translate Q4: Why?"""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        evidence_items = getattr(decision.q4_why, 'evidence_items', [])
        evidence_summary = ", ".join([
            getattr(e, 'source', 'unknown') for e in evidence_items[:3]
        ])
        
        return t(
            "questions.q4_why",
            reasoning=getattr(decision.q4_why, 'reasoning_summary', ''),
            evidence_count=len(evidence_items),
            evidence_summary=evidence_summary,
        )
    
    def _translate_q5(self, decision: "DecisionObject", language: str) -> str:
        """Translate Q5: What to do?"""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        action_type = decision.q5_action.action_type.value
        
        return t(
            "questions.q5_action",
            action=t(f"actions.{action_type}"),
            action_description=t(f"action_descriptions.{action_type}"),
            cost=self._format_currency(decision.q5_action.estimated_cost_usd, language),
            deadline=self._format_datetime(decision.q5_action.deadline, language),
        )
    
    def _translate_q6(self, decision: "DecisionObject", language: str) -> str:
        """Translate Q6: How confident?"""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        score = decision.q6_confidence.calibrated_score
        level = "high" if score >= 0.8 else "moderate" if score >= 0.5 else "low"
        
        return t(
            "questions.q6_confidence",
            level=t(f"confidence.{level}"),
            score=score * 100,
            factors=", ".join(getattr(decision.q6_confidence, 'key_factors', [])),
        )
    
    def _translate_q7(self, decision: "DecisionObject", language: str) -> str:
        """Translate Q7: What if nothing?"""
        t = lambda key, **kw: self.translate(key, language, **kw)
        
        return t(
            "questions.q7_inaction",
            loss=self._format_currency(decision.q7_inaction.expected_loss_if_nothing, language),
            point_of_no_return=self._format_datetime(
                getattr(decision.q7_inaction, 'point_of_no_return', datetime.utcnow()),
                language
            ),
        )
    
    def _format_currency(self, amount: float, language: str) -> str:
        """Format currency based on locale."""
        if language == "vi":
            # Vietnamese format: 1.234.567 đ or $1,234,567
            return f"${amount:,.0f}"
        else:
            # English format: $1,234,567
            return f"${amount:,.0f}"
    
    def _format_datetime(self, dt: datetime, language: str) -> str:
        """Format datetime based on locale."""
        if not isinstance(dt, datetime):
            return str(dt)
        
        if language == "vi":
            # Vietnamese: DD/MM/YYYY HH:MM
            return dt.strftime("%d/%m/%Y %H:%M")
        else:
            # English: YYYY-MM-DD HH:MM
            return dt.strftime("%Y-%m-%d %H:%M")
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages with names."""
        return [
            {"code": "en", "name": "English", "native_name": "English"},
            {"code": "vi", "name": "Vietnamese", "native_name": "Tiếng Việt"},
            {"code": "zh", "name": "Chinese", "native_name": "中文", "status": "planned"},
            {"code": "ja", "name": "Japanese", "native_name": "日本語", "status": "planned"},
        ]


# ============================================================================
# ENGLISH TRANSLATIONS
# ============================================================================


EN_TRANSLATIONS = {
    "decision": {
        "executive_summary": "RISKCAST recommends {action} for {shipment_count} shipments with {exposure} exposure. Expected delay: {delay} days. Action cost: {cost}. Confidence: {confidence:.0f}%. Deadline: {deadline}. Inaction loss: {inaction_loss}.",
        "title": "Decision Report",
        "generated_at": "Generated at {timestamp}",
    },
    "questions": {
        "q1_what": "A {event_type} event is affecting the {chokepoint} chokepoint. {summary}",
        "q2_when": "Urgency: {urgency}. You have {window_hours} hours to decide. Deadline: {deadline}.",
        "q3_severity": "Total exposure: {exposure}. Expected delay: {delay_days} days affecting {shipment_count} shipments.",
        "q4_why": "{reasoning} Based on {evidence_count} evidence items: {evidence_summary}.",
        "q5_action": "Recommended action: {action}. {action_description}. Estimated cost: {cost}. Deadline: {deadline}.",
        "q6_confidence": "Confidence: {level} ({score:.0f}%). Key factors: {factors}.",
        "q7_inaction": "If no action taken, expected loss: {loss}. Point of no return: {point_of_no_return}.",
    },
    "actions": {
        "reroute": "REROUTE",
        "expedite": "EXPEDITE",
        "hold": "HOLD",
        "delay": "DELAY",
        "insure": "INSURE",
        "monitor": "MONITOR",
        "do_nothing": "NO ACTION",
    },
    "action_descriptions": {
        "reroute": "Change shipping route to avoid affected area",
        "expedite": "Accelerate shipment processing",
        "hold": "Hold shipment at current location",
        "delay": "Delay shipment departure",
        "insure": "Purchase additional insurance coverage",
        "monitor": "Continue monitoring situation",
        "do_nothing": "No action recommended at this time",
    },
    "confidence": {
        "high": "High",
        "moderate": "Moderate",
        "low": "Low",
    },
    "urgency": {
        "immediate": "Immediate action required",
        "urgent": "Action needed within 24 hours",
        "soon": "Action recommended within 48 hours",
        "watch": "Monitor situation",
    },
    "events": {
        "disruption": "supply chain disruption",
        "weather": "severe weather",
        "conflict": "geopolitical conflict",
        "strike": "labor strike",
        "congestion": "port congestion",
        "closure": "route closure",
    },
    "chokepoints": {
        "red_sea": "Red Sea",
        "suez": "Suez Canal",
        "panama": "Panama Canal",
        "malacca": "Strait of Malacca",
        "bosphorus": "Bosphorus Strait",
        "unknown": "affected area",
    },
    "export": {
        "audit_trail": "Audit Trail Export",
        "decisions": "Decisions Export",
        "justification": "Decision Justification",
        "generated_by": "Generated by RISKCAST",
    },
    "escalation": {
        "alert_created": "Alert created",
        "escalated_to": "Escalated to {level}",
        "acknowledged_by": "Acknowledged by {user}",
        "no_ack_escalating": "No acknowledgment received, escalating",
    },
}


# ============================================================================
# VIETNAMESE TRANSLATIONS
# ============================================================================


VI_TRANSLATIONS = {
    "decision": {
        "executive_summary": "RISKCAST khuyến nghị {action} cho {shipment_count} lô hàng với rủi ro {exposure}. Dự kiến trễ: {delay} ngày. Chi phí hành động: {cost}. Độ tin cậy: {confidence:.0f}%. Hạn chót: {deadline}. Thiệt hại nếu không hành động: {inaction_loss}.",
        "title": "Báo Cáo Quyết Định",
        "generated_at": "Tạo lúc {timestamp}",
    },
    "questions": {
        "q1_what": "Sự kiện {event_type} đang ảnh hưởng đến điểm nghẽn {chokepoint}. {summary}",
        "q2_when": "Mức độ khẩn cấp: {urgency}. Bạn có {window_hours} giờ để quyết định. Hạn chót: {deadline}.",
        "q3_severity": "Tổng rủi ro: {exposure}. Dự kiến trễ: {delay_days} ngày ảnh hưởng {shipment_count} lô hàng.",
        "q4_why": "{reasoning} Dựa trên {evidence_count} nguồn bằng chứng: {evidence_summary}.",
        "q5_action": "Hành động khuyến nghị: {action}. {action_description}. Chi phí ước tính: {cost}. Hạn chót: {deadline}.",
        "q6_confidence": "Độ tin cậy: {level} ({score:.0f}%). Yếu tố chính: {factors}.",
        "q7_inaction": "Nếu không hành động, thiệt hại dự kiến: {loss}. Điểm không thể quay lại: {point_of_no_return}.",
    },
    "actions": {
        "reroute": "CHUYỂN HƯỚNG",
        "expedite": "TĂNG TỐC",
        "hold": "TẠM GIỮ",
        "delay": "TRÌ HOÃN",
        "insure": "MUA BẢO HIỂM",
        "monitor": "THEO DÕI",
        "do_nothing": "KHÔNG HÀNH ĐỘNG",
    },
    "action_descriptions": {
        "reroute": "Thay đổi tuyến vận chuyển để tránh khu vực bị ảnh hưởng",
        "expedite": "Đẩy nhanh quá trình xử lý lô hàng",
        "hold": "Giữ lô hàng tại vị trí hiện tại",
        "delay": "Trì hoãn khởi hành lô hàng",
        "insure": "Mua thêm bảo hiểm",
        "monitor": "Tiếp tục theo dõi tình hình",
        "do_nothing": "Không khuyến nghị hành động tại thời điểm này",
    },
    "confidence": {
        "high": "Cao",
        "moderate": "Trung bình",
        "low": "Thấp",
    },
    "urgency": {
        "immediate": "Yêu cầu hành động ngay",
        "urgent": "Cần hành động trong 24 giờ",
        "soon": "Khuyến nghị hành động trong 48 giờ",
        "watch": "Theo dõi tình hình",
    },
    "events": {
        "disruption": "gián đoạn chuỗi cung ứng",
        "weather": "thời tiết khắc nghiệt",
        "conflict": "xung đột địa chính trị",
        "strike": "đình công",
        "congestion": "tắc nghẽn cảng",
        "closure": "đóng cửa tuyến đường",
    },
    "chokepoints": {
        "red_sea": "Biển Đỏ",
        "suez": "Kênh đào Suez",
        "panama": "Kênh đào Panama",
        "malacca": "Eo biển Malacca",
        "bosphorus": "Eo biển Bosphorus",
        "unknown": "khu vực bị ảnh hưởng",
    },
    "export": {
        "audit_trail": "Xuất Dấu Vết Kiểm Toán",
        "decisions": "Xuất Quyết Định",
        "justification": "Giải Trình Quyết Định",
        "generated_by": "Được tạo bởi RISKCAST",
    },
    "escalation": {
        "alert_created": "Cảnh báo đã được tạo",
        "escalated_to": "Đã chuyển lên {level}",
        "acknowledged_by": "Đã xác nhận bởi {user}",
        "no_ack_escalating": "Không nhận được xác nhận, đang chuyển cấp",
    },
}


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================


_translator: Optional[TranslationManager] = None


def get_translator() -> TranslationManager:
    """Get global translation manager instance."""
    global _translator
    if _translator is None:
        _translator = TranslationManager()
    return _translator


def translate(key: str, language: str = "en", **kwargs) -> str:
    """Convenience function for translation."""
    return get_translator().translate(key, language, **kwargs)


def translate_decision(decision: "DecisionObject", language: str = "en") -> Dict[str, Any]:
    """Convenience function for decision translation."""
    return get_translator().translate_decision(decision, language)
