"""検出事項Repository"""

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.auditor import Finding
from src.db.repositories.base import BaseRepository


class FindingRepository(BaseRepository[Finding]):
    """検出事項固有のクエリ"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Finding, session)

    async def get_by_project(
        self, tenant_id: str | UUID, project_id: str | UUID
    ) -> list[Finding]:
        """プロジェクト別検出事項一覧"""
        query = (
            select(Finding)
            .where(
                Finding.tenant_id == str(tenant_id),
                Finding.project_id == str(project_id),
            )
            .order_by(Finding.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_risk_summary(
        self, tenant_id: str | UUID, project_id: str | UUID
    ) -> dict[str, int]:
        """リスクレベル別集計"""
        query = (
            select(Finding.risk_level, func.count())
            .where(
                Finding.tenant_id == str(tenant_id),
                Finding.project_id == str(project_id),
            )
            .group_by(Finding.risk_level)
        )
        result = await self._session.execute(query)
        return dict(result.all())
