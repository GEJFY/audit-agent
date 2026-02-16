"""通知エンドポイント — 通知送信・プロバイダ管理"""

from typing import Any

from fastapi import APIRouter

from src.notifications.base import NotificationMessage, NotificationPriority
from src.notifications.dispatcher import NotificationDispatcher

router = APIRouter()

# アプリケーションスコープのディスパッチャー
_dispatcher = NotificationDispatcher()


@router.get("/providers")
async def list_providers() -> dict[str, Any]:
    """登録済み通知プロバイダ一覧"""
    providers = _dispatcher.list_providers()
    return {
        "providers": providers,
        "count": len(providers),
    }


@router.post("/send")
async def send_notification(
    body: dict[str, Any],
) -> dict[str, Any]:
    """通知送信

    Body:
        title: 通知タイトル
        body: 通知本文
        priority: 優先度 (low, medium, high, critical)
        tenant_id: テナントID
        source: 通知種別 (escalation, approval_request, risk_alert)
        provider_names: 送信先プロバイダ名リスト (省略時は全プロバイダ)
        action_url: アクションリンク (省略可)
    """
    priority_str = body.get("priority", "medium")
    try:
        priority = NotificationPriority(priority_str)
    except ValueError:
        priority = NotificationPriority.MEDIUM

    message = NotificationMessage(
        title=body.get("title", ""),
        body=body.get("body", ""),
        priority=priority,
        tenant_id=body.get("tenant_id", ""),
        source=body.get("source", ""),
        action_url=body.get("action_url"),
    )

    provider_names = body.get("provider_names")
    results = await _dispatcher.dispatch(message, provider_names=provider_names)

    return {
        "sent": results,
        "success_count": sum(1 for v in results.values() if v),
        "failure_count": sum(1 for v in results.values() if not v),
    }


@router.post("/escalation")
async def send_escalation(
    body: dict[str, Any],
) -> dict[str, Any]:
    """エスカレーション通知送信

    Body:
        tenant_id: テナントID
        title: 通知タイトル
        body: 通知本文
        action_url: アクションリンク (省略可)
    """
    results = await _dispatcher.dispatch_escalation(
        tenant_id=body.get("tenant_id", ""),
        title=body.get("title", ""),
        body=body.get("body", ""),
        action_url=body.get("action_url"),
    )
    return {"sent": results}


@router.post("/risk-alert")
async def send_risk_alert(
    body: dict[str, Any],
) -> dict[str, Any]:
    """リスクアラート通知送信

    Body:
        tenant_id: テナントID
        title: 通知タイトル
        body: 通知本文
        priority: 優先度 (省略時はhigh)
    """
    priority_str = body.get("priority", "high")
    try:
        priority = NotificationPriority(priority_str)
    except ValueError:
        priority = NotificationPriority.HIGH

    results = await _dispatcher.dispatch_risk_alert(
        tenant_id=body.get("tenant_id", ""),
        title=body.get("title", ""),
        body=body.get("body", ""),
        priority=priority,
    )
    return {"sent": results}


@router.get("/health")
async def check_providers_health() -> dict[str, Any]:
    """全通知プロバイダのヘルスチェック"""
    results = await _dispatcher.health_check_all()
    all_healthy = all(results.values()) if results else True
    return {
        "status": "healthy" if all_healthy else "degraded",
        "providers": results,
    }
