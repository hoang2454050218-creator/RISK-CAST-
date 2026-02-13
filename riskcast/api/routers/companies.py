"""Company CRUD endpoints + per-company notification settings."""

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.db.repositories.company import company_repo
from riskcast.schemas.company import CompanyResponse, CompanyUpdate

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


# ── Notification Settings schemas ─────────────────────────────────────


class NotificationSettingsResponse(BaseModel):
    """Per-company notification configuration."""
    discord_webhook_url: str = ""
    discord_enabled: bool = False
    email_enabled: bool = False
    email_recipients: list[str] = Field(default_factory=list)
    in_app_enabled: bool = True
    # Which alert severities to send
    notify_critical: bool = True
    notify_high: bool = True
    notify_warning: bool = False
    notify_info: bool = False


class NotificationSettingsUpdate(BaseModel):
    """Update notification settings — all fields optional."""
    discord_webhook_url: Optional[str] = None
    discord_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    email_recipients: Optional[list[str]] = None
    in_app_enabled: Optional[bool] = None
    notify_critical: Optional[bool] = None
    notify_high: Optional[bool] = None
    notify_warning: Optional[bool] = None
    notify_info: Optional[bool] = None


# ── Company CRUD ──────────────────────────────────────────────────────


@router.get("/me", response_model=CompanyResponse)
async def get_my_company(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get the current tenant's company info."""
    company = await company_repo.get_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch("/me", response_model=CompanyResponse)
async def update_my_company(
    body: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Update the current tenant's company info."""
    updates = body.model_dump(exclude_unset=True)
    company = await company_repo.update(db, company_id, **updates)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


# ── Notification Settings endpoints ───────────────────────────────────


@router.get("/me/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Get notification settings for current company.

    Returns Discord webhook config, email settings, and severity filters.
    """
    company = await company_repo.get_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    notif = (company.settings or {}).get("notifications", {})
    return NotificationSettingsResponse(
        discord_webhook_url=notif.get("discord_webhook_url", ""),
        discord_enabled=notif.get("discord_enabled", False),
        email_enabled=notif.get("email_enabled", False),
        email_recipients=notif.get("email_recipients", []),
        in_app_enabled=notif.get("in_app_enabled", True),
        notify_critical=notif.get("notify_critical", True),
        notify_high=notif.get("notify_high", True),
        notify_warning=notif.get("notify_warning", False),
        notify_info=notif.get("notify_info", False),
    )


@router.put("/me/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    body: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Update notification settings for current company.

    Stores Discord webhook URL, email config, and severity filters.
    Only provided fields are updated; others keep their current values.
    """
    company = await company_repo.get_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Validate Discord webhook URL if provided
    webhook_url = body.discord_webhook_url
    if webhook_url is not None and webhook_url != "":
        if not webhook_url.startswith("https://discord.com/api/webhooks/"):
            raise HTTPException(
                status_code=400,
                detail="Discord webhook URL phải bắt đầu bằng https://discord.com/api/webhooks/",
            )

    # Merge with existing notification settings
    current_settings = dict(company.settings or {})
    current_notif = current_settings.get("notifications", {})

    updates = body.model_dump(exclude_unset=True)
    current_notif.update(updates)

    # Auto-enable Discord when URL is provided
    if "discord_webhook_url" in updates and updates["discord_webhook_url"]:
        current_notif.setdefault("discord_enabled", True)

    current_settings["notifications"] = current_notif

    # Save
    company = await company_repo.update(db, company_id, settings=current_settings)

    logger.info(
        "notification_settings_updated",
        company_id=str(company_id),
        discord_enabled=current_notif.get("discord_enabled"),
        has_webhook=bool(current_notif.get("discord_webhook_url")),
    )

    return NotificationSettingsResponse(**current_notif)


@router.post("/me/notifications/test")
async def test_notification(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Send a test notification to verify Discord webhook configuration.

    Returns success/failure with details.
    """
    company = await company_repo.get_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    notif = (company.settings or {}).get("notifications", {})
    webhook_url = notif.get("discord_webhook_url", "")

    if not webhook_url:
        raise HTTPException(
            status_code=400,
            detail="Chưa cấu hình Discord webhook URL. Vào Settings → Thông báo để thiết lập.",
        )

    # Send test message
    from riskcast.alerting.channels import WebhookDispatcher
    from riskcast.alerting.schemas import (
        AlertChannel, AlertRecord, AlertSeverity, AlertStatus,
    )
    from datetime import datetime

    test_alert = AlertRecord(
        alert_id="test_notification",
        rule_id="test",
        rule_name="Test",
        company_id=str(company_id),
        severity=AlertSeverity.INFO,
        status=AlertStatus.PENDING,
        metric="test",
        metric_value=0,
        threshold=0,
        title="✅ Kết nối Discord thành công!",
        message=(
            "Đây là tin nhắn test từ **RiskCast**.\n\n"
            "Hệ thống sẽ gửi thông báo vào kênh này khi:\n"
            "• Phát hiện rủi ro cao cho lô hàng của bạn\n"
            "• Có khuyến nghị hành động cần xử lý\n"
            "• Quyết định cần được phê duyệt\n\n"
            "📌 Bạn có thể tùy chỉnh loại thông báo trong Settings."
        ),
        channels=[AlertChannel.WEBHOOK],
        triggered_at=datetime.utcnow().isoformat(),
    )

    payload = WebhookDispatcher._build_discord_payload(test_alert)

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code < 400:
                return {
                    "success": True,
                    "message": "Đã gửi tin nhắn test lên Discord. Kiểm tra kênh Discord của bạn!",
                }
            else:
                return {
                    "success": False,
                    "message": f"Discord trả về lỗi {response.status_code}. Kiểm tra lại webhook URL.",
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"Không thể kết nối: {str(e)}",
        }
