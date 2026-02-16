"""通知Repository"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.notification import Notification, NotificationSetting
from src.db.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """通知履歴固有のクエリ"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Notification, session)

    async def get_by_project(
        self,
        tenant_id: str | UUID,
        project_id: str | UUID,
        limit: int = 50,
    ) -> list[Notification]:
        """プロジェクト別通知取得"""
        query = (
            select(Notification)
            .where(
                Notification.tenant_id == str(tenant_id),
                Notification.project_id == str(project_id),
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_failed(
        self,
        tenant_id: str | UUID,
        limit: int = 100,
    ) -> list[Notification]:
        """送信失敗の通知取得"""
        query = (
            select(Notification)
            .where(
                Notification.tenant_id == str(tenant_id),
                Notification.status == "failed",
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())


class NotificationSettingRepository(BaseRepository[NotificationSetting]):
    """通知設定固有のクエリ"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NotificationSetting, session)

    async def get_enabled(
        self,
        tenant_id: str | UUID,
    ) -> list[NotificationSetting]:
        """有効な通知設定取得"""
        query = (
            select(NotificationSetting)
            .where(
                NotificationSetting.tenant_id == str(tenant_id),
                NotificationSetting.is_enabled.is_(True),
            )
            .order_by(NotificationSetting.provider)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
