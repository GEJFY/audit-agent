"""通知プロバイダ基底クラス"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class NotificationPriority(StrEnum):
    """通知優先度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationMessage(BaseModel):
    """通知メッセージ"""

    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    tenant_id: str = ""
    source: str = ""  # エスカレーション、承認依頼、アラート等
    metadata: dict[str, Any] = {}
    action_url: str | None = None  # 承認画面等へのリンク


class BaseNotificationProvider(ABC):
    """通知プロバイダの基底クラス"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """プロバイダ名"""
        ...

    @abstractmethod
    async def send(self, message: NotificationMessage, channel: str) -> bool:
        """通知を送信

        Args:
            message: 通知メッセージ
            channel: 送信先チャンネル/アドレス

        Returns:
            送信成功ならTrue
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """接続チェック"""
        ...
