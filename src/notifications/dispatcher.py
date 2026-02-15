"""通知ディスパッチャー — 通知の振り分けと送信"""

from loguru import logger

from src.notifications.base import BaseNotificationProvider, NotificationMessage, NotificationPriority


class NotificationDispatcher:
    """通知振り分けエンジン

    複数プロバイダへの同時送信、優先度に基づくルーティング、
    テナント単位の通知設定を管理する。
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseNotificationProvider] = {}
        self._tenant_channels: dict[str, dict[str, str]] = {}
        # テナント → {プロバイダ名 → チャンネル}

    def register_provider(self, provider: BaseNotificationProvider) -> None:
        """通知プロバイダを登録"""
        self._providers[provider.provider_name] = provider
        logger.info("通知プロバイダ登録: {}", provider.provider_name)

    def set_tenant_channel(
        self,
        tenant_id: str,
        provider_name: str,
        channel: str,
    ) -> None:
        """テナントの通知チャンネルを設定"""
        if tenant_id not in self._tenant_channels:
            self._tenant_channels[tenant_id] = {}
        self._tenant_channels[tenant_id][provider_name] = channel

    async def dispatch(
        self,
        message: NotificationMessage,
        provider_names: list[str] | None = None,
    ) -> dict[str, bool]:
        """通知を振り分けて送信

        Args:
            message: 通知メッセージ
            provider_names: 送信先プロバイダ名（Noneなら全プロバイダ）

        Returns:
            {プロバイダ名: 送信成功/失敗} の辞書
        """
        targets = provider_names or list(self._providers.keys())
        results: dict[str, bool] = {}

        for name in targets:
            provider = self._providers.get(name)
            if not provider:
                logger.warning("通知プロバイダ未登録: {}", name)
                results[name] = False
                continue

            # テナント別チャンネル
            channel = ""
            if message.tenant_id and message.tenant_id in self._tenant_channels:
                channel = self._tenant_channels[message.tenant_id].get(name, "")

            try:
                success = await provider.send(message, channel)
                results[name] = success
            except Exception as e:
                logger.error("通知送信エラー: provider={}, error={}", name, str(e))
                results[name] = False

        return results

    async def dispatch_escalation(
        self,
        tenant_id: str,
        title: str,
        body: str,
        action_url: str | None = None,
    ) -> dict[str, bool]:
        """エスカレーション通知を送信"""
        message = NotificationMessage(
            title=title,
            body=body,
            priority=NotificationPriority.HIGH,
            tenant_id=tenant_id,
            source="escalation",
            action_url=action_url,
        )
        return await self.dispatch(message)

    async def dispatch_approval_request(
        self,
        tenant_id: str,
        title: str,
        body: str,
        action_url: str | None = None,
    ) -> dict[str, bool]:
        """承認依頼通知を送信"""
        message = NotificationMessage(
            title=title,
            body=body,
            priority=NotificationPriority.MEDIUM,
            tenant_id=tenant_id,
            source="approval_request",
            action_url=action_url,
        )
        return await self.dispatch(message)

    async def dispatch_risk_alert(
        self,
        tenant_id: str,
        title: str,
        body: str,
        priority: NotificationPriority = NotificationPriority.HIGH,
    ) -> dict[str, bool]:
        """リスクアラート通知を送信"""
        message = NotificationMessage(
            title=title,
            body=body,
            priority=priority,
            tenant_id=tenant_id,
            source="risk_alert",
        )
        return await self.dispatch(message)

    def list_providers(self) -> list[str]:
        """登録済みプロバイダ一覧"""
        return list(self._providers.keys())

    async def health_check_all(self) -> dict[str, bool]:
        """全プロバイダのヘルスチェック"""
        results: dict[str, bool] = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results
