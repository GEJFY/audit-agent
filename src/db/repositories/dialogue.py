"""対話メッセージRepository"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.dialogue import DialogueMessage
from src.db.repositories.base import BaseRepository


class DialogueRepository(BaseRepository[DialogueMessage]):
    """対話メッセージ固有のクエリ"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DialogueMessage, session)

    async def get_thread(self, thread_id: str | UUID) -> list[DialogueMessage]:
        """スレッド内の全メッセージを時系列で取得"""
        query = (
            select(DialogueMessage)
            .where(DialogueMessage.thread_id == str(thread_id))
            .order_by(DialogueMessage.created_at.asc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_project(self, project_id: str | UUID, limit: int = 100) -> list[DialogueMessage]:
        """プロジェクト別対話メッセージ"""
        query = (
            select(DialogueMessage)
            .where(DialogueMessage.project_id == str(project_id))
            .order_by(DialogueMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_pending_approvals(self, tenant_id: str | UUID) -> list[DialogueMessage]:
        """承認待ちメッセージ一覧"""
        query = (
            select(DialogueMessage)
            .where(
                DialogueMessage.from_tenant_id == str(tenant_id),
                DialogueMessage.human_approved.is_(None),
            )
            .order_by(DialogueMessage.created_at.asc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_escalated(self, tenant_id: str | UUID) -> list[DialogueMessage]:
        """エスカレーション済みメッセージ"""
        query = (
            select(DialogueMessage)
            .where(
                DialogueMessage.to_tenant_id == str(tenant_id),
                DialogueMessage.is_escalated.is_(True),
            )
            .order_by(DialogueMessage.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
