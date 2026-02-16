"""監査イベントRepository"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.audit_event import AuditEvent
from src.db.repositories.base import BaseRepository


class AuditEventRepository(BaseRepository[AuditEvent]):
    """監査イベント固有のクエリ"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditEvent, session)

    async def get_by_resource(
        self,
        tenant_id: str | UUID,
        resource_type: str,
        resource_id: str | UUID,
    ) -> list[AuditEvent]:
        """リソース別イベント取得"""
        query = (
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == str(tenant_id),
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == str(resource_id),
            )
            .order_by(AuditEvent.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_actor(
        self,
        tenant_id: str | UUID,
        actor_id: str | UUID,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """操作者別イベント取得"""
        query = (
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == str(tenant_id),
                AuditEvent.actor_id == str(actor_id),
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_project(
        self,
        tenant_id: str | UUID,
        project_id: str | UUID,
    ) -> list[AuditEvent]:
        """プロジェクト別イベント取得"""
        query = (
            select(AuditEvent)
            .where(
                AuditEvent.tenant_id == str(tenant_id),
                AuditEvent.project_id == str(project_id),
            )
            .order_by(AuditEvent.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
