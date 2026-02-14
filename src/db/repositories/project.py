"""監査プロジェクトRepository"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.auditor import AuditProject
from src.db.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[AuditProject]):
    """監査プロジェクト固有のクエリ"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditProject, session)

    async def get_active_projects(self, tenant_id: str | UUID) -> list[AuditProject]:
        """アクティブな監査プロジェクト一覧"""
        query = (
            select(AuditProject)
            .where(
                AuditProject.tenant_id == str(tenant_id),
                AuditProject.status.notin_(["closed", "draft"]),
            )
            .order_by(AuditProject.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_fiscal_year(
        self, tenant_id: str | UUID, fiscal_year: int
    ) -> list[AuditProject]:
        """年度別プロジェクト取得"""
        query = (
            select(AuditProject)
            .where(
                AuditProject.tenant_id == str(tenant_id),
                AuditProject.fiscal_year == fiscal_year,
            )
            .order_by(AuditProject.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
