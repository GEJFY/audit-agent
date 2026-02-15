"""Slack 通知プロバイダ — Webhook + Block Kit"""

from typing import Any

import httpx
from loguru import logger

from src.notifications.base import BaseNotificationProvider, NotificationMessage, NotificationPriority


class SlackProvider(BaseNotificationProvider):
    """Slack Incoming Webhook 通知プロバイダ"""

    PRIORITY_EMOJI = {
        NotificationPriority.LOW: ":information_source:",
        NotificationPriority.MEDIUM: ":warning:",
        NotificationPriority.HIGH: ":exclamation:",
        NotificationPriority.CRITICAL: ":rotating_light:",
    }

    PRIORITY_COLOR = {
        NotificationPriority.LOW: "#36a64f",
        NotificationPriority.MEDIUM: "#daa520",
        NotificationPriority.HIGH: "#ff6600",
        NotificationPriority.CRITICAL: "#ff0000",
    }

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "slack"

    async def send(self, message: NotificationMessage, channel: str = "") -> bool:
        """Slack Webhookで通知送信"""
        if not self._webhook_url:
            logger.warning("Slack: Webhook URLが未設定")
            return False

        payload = self._build_payload(message)

        try:
            if not self._client:
                self._client = httpx.AsyncClient(timeout=10.0)

            response = await self._client.post(self._webhook_url, json=payload)
            response.raise_for_status()

            logger.info("Slack通知送信成功: title={}", message.title)
            return True
        except Exception as e:
            logger.error("Slack通知送信エラー: {}", str(e))
            return False

    def _build_payload(self, message: NotificationMessage) -> dict[str, Any]:
        """Block Kit形式のペイロードを構築"""
        emoji = self.PRIORITY_EMOJI.get(message.priority, ":bell:")
        color = self.PRIORITY_COLOR.get(message.priority, "#cccccc")

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {message.title}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message.body,
                },
            },
        ]

        # メタデータ情報
        fields: list[dict[str, str]] = []
        if message.source:
            fields.append({"type": "mrkdwn", "text": f"*種別:* {message.source}"})
        if message.tenant_id:
            fields.append({"type": "mrkdwn", "text": f"*テナント:* {message.tenant_id}"})
        if message.priority:
            fields.append({"type": "mrkdwn", "text": f"*優先度:* {message.priority.value}"})

        if fields:
            blocks.append({"type": "section", "fields": fields})

        # アクションリンク
        if message.action_url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "詳細を確認"},
                            "url": message.action_url,
                            "style": "primary",
                        }
                    ],
                }
            )

        return {
            "blocks": blocks,
            "attachments": [{"color": color, "blocks": []}],
        }

    async def health_check(self) -> bool:
        """Webhook URLが設定されているか確認"""
        return bool(self._webhook_url)

    async def close(self) -> None:
        """クライアント切断"""
        if self._client:
            await self._client.aclose()
            self._client = None
