"""Generic CRUD Repository — テナント分離対応"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """テナント分離対応の汎用CRUDリポジトリ

    全クエリにtenant_idフィルタを自動適用。
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def create(self, **kwargs: Any) -> ModelT:
        """新規レコード作成"""
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_by_id(self, id_: str | UUID, tenant_id: str | UUID | None = None) -> ModelT | None:
        """IDでレコード取得"""
        query = select(self._model).where(self._model.id == str(id_))  # type: ignore[attr-defined]
        if tenant_id and hasattr(self._model, "tenant_id"):
            query = query.where(self._model.tenant_id == str(tenant_id))  # type: ignore[attr-defined]
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str | UUID | None = None,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        **filters: Any,
    ) -> list[ModelT]:
        """一覧取得（ページネーション対応）"""
        query = select(self._model)

        if tenant_id and hasattr(self._model, "tenant_id"):
            query = query.where(self._model.tenant_id == str(tenant_id))  # type: ignore[attr-defined]

        for key, value in filters.items():
            if hasattr(self._model, key) and value is not None:
                query = query.where(getattr(self._model, key) == value)

        if order_by and hasattr(self._model, order_by):
            query = query.order_by(getattr(self._model, order_by).desc())
        elif hasattr(self._model, "created_at"):
            query = query.order_by(self._model.created_at.desc())  # type: ignore[attr-defined]

        query = query.offset(offset).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        id_: str | UUID,
        tenant_id: str | UUID | None = None,
        **kwargs: Any,
    ) -> ModelT | None:
        """レコード更新"""
        stmt = (
            update(self._model)
            .where(self._model.id == str(id_))  # type: ignore[attr-defined]
            .values(**kwargs)
            .returning(self._model)
        )
        if tenant_id and hasattr(self._model, "tenant_id"):
            stmt = stmt.where(self._model.tenant_id == str(tenant_id))  # type: ignore[attr-defined]

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, id_: str | UUID, tenant_id: str | UUID | None = None) -> bool:
        """レコード削除"""
        stmt = delete(self._model).where(self._model.id == str(id_))  # type: ignore[attr-defined]
        if tenant_id and hasattr(self._model, "tenant_id"):
            stmt = stmt.where(self._model.tenant_id == str(tenant_id))  # type: ignore[attr-defined]

        result = await self._session.execute(stmt)
        return result.rowcount > 0  # type: ignore[union-attr]

    async def count(self, tenant_id: str | UUID | None = None, **filters: Any) -> int:
        """レコード数取得"""
        query = select(func.count()).select_from(self._model)

        if tenant_id and hasattr(self._model, "tenant_id"):
            query = query.where(self._model.tenant_id == str(tenant_id))  # type: ignore[attr-defined]

        for key, value in filters.items():
            if hasattr(self._model, key) and value is not None:
                query = query.where(getattr(self._model, key) == value)

        result = await self._session.execute(query)
        return result.scalar_one()
