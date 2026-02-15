"""Teams 通知プロバイダ — Webhook + Adaptive Card"""

from typing import Any

import httpx
from loguru import logger

from src.notifications.base import BaseNotificationProvider, NotificationMessage, NotificationPriority


class TeamsProvider(BaseNotificationProvider):
    """Microsoft Teams Incoming Webhook 通知プロバイダ"""

    PRIORITY_COLOR = {
        NotificationPriority.LOW: "good",
        NotificationPriority.MEDIUM: "warning",
        NotificationPriority.HIGH: "attention",
        NotificationPriority.CRITICAL: "attention",
    }

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "teams"

    async def send(self, message: NotificationMessage, channel: str = "") -> bool:
        """Teams Webhookで通知送信"""
        if not self._webhook_url:
            logger.warning("Teams: Webhook URLが未設定")
            return False

        payload = self._build_adaptive_card(message)

        try:
            if not self._client:
                self._client = httpx.AsyncClient(timeout=10.0)

            response = await self._client.post(self._webhook_url, json=payload)
            response.raise_for_status()

            logger.info("Teams通知送信成功: title={}", message.title)
            return True
        except Exception as e:
            logger.error("Teams通知送信エラー: {}", str(e))
            return False

    def _build_adaptive_card(self, message: NotificationMessage) -> dict[str, Any]:
        """Adaptive Card形式のペイロードを構築"""
        color = self.PRIORITY_COLOR.get(message.priority, "default")

        body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": message.title,
                "weight": "Bolder",
                "size": "Medium",
                "color": color,
            },
            {
                "type": "TextBlock",
                "text": message.body,
                "wrap": True,
            },
        ]

        # ファクトセット（メタデータ）
        facts: list[dict[str, str]] = []
        if message.source:
            facts.append({"title": "種別", "value": message.source})
        if message.tenant_id:
            facts.append({"title": "テナント", "value": message.tenant_id})
        if message.priority:
            facts.append({"title": "優先度", "value": message.priority.value})

        if facts:
            body.append({"type": "FactSet", "facts": facts})

        # アクション
        actions: list[dict[str, Any]] = []
        if message.action_url:
            actions.append(
                {
                    "type": "Action.OpenUrl",
                    "title": "詳細を確認",
                    "url": message.action_url,
                }
            )

        card: dict[str, Any] = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body,
                    },
                }
            ],
        }

        if actions:
            card["attachments"][0]["content"]["actions"] = actions

        return card

    async def health_check(self) -> bool:
        """Webhook URLが設定されているか確認"""
        return bool(self._webhook_url)

    async def close(self) -> None:
        """クライアント切断"""
        if self._client:
            await self._client.aclose()
            self._client = None
