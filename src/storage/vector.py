"""ベクトルDB — pgvector ベースのRAG検索"""

import uuid as uuid_mod
from typing import Any

from loguru import logger
from sqlalchemy import Column, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.db.base import Base, TimestampMixin
from src.db.session import get_session


class VectorDocument(Base, TimestampMixin):
    """ベクトル文書テーブル — pgvector HNSW索引付き"""

    __tablename__ = "vector_documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict)
    doc_type = Column(String(100), nullable=False)  # audit_standard, regulation, past_response, evidence
    source_id = Column(String(255), nullable=True)  # 元文書ID
    # pgvector: embedding カラムはマイグレーションで追加
    # embedding = Column(Vector(1536))  # text-embedding-3-small次元数


class VectorStore:
    """pgvectorベースのベクトルストア

    監査基準・社内規程・過去回答のセマンティック検索を提供。
    Anthropic Embedding API or OpenAI text-embedding-3-small でベクトル化。
    HNSW索引による高速近傍検索。
    """

    EMBEDDING_DIM = 1536  # text-embedding-3-small

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._settings = get_settings()

    async def _get_session(self) -> AsyncSession:
        """セッション取得"""
        if self._session:
            return self._session
        async for session in get_session():
            return session
        raise RuntimeError("DBセッション取得失敗")

    async def _generate_embedding(self, text_content: str) -> list[float]:
        """テキストをベクトル化

        Anthropicの場合、LLMで擬似的にEmbeddingを生成するか、
        OpenAI Embedding APIを使用。ここではOpenAI互換APIを使用。
        """
        try:
            import httpx

            # OpenAI Embedding API互換エンドポイント
            api_key = self._settings.azure_openai_api_key or self._settings.anthropic_api_key
            if not api_key:
                # フォールバック: 簡易ハッシュベースの疑似ベクトル
                return self._fallback_embedding(text_content)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "text-embedding-3-small",
                        "input": text_content[:8000],  # トークン制限
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]  # type: ignore[no-any-return]

            return self._fallback_embedding(text_content)
        except Exception as e:
            logger.warning("Embedding API エラー、フォールバック使用: {}", str(e))
            return self._fallback_embedding(text_content)

    def _fallback_embedding(self, text_content: str) -> list[float]:
        """フォールバック: ハッシュベースの疑似ベクトル生成

        本番ではEmbedding APIを使用すべき。開発/テスト環境用。
        """
        import hashlib

        hash_bytes = hashlib.sha512(text_content.encode()).digest()
        # SHA-512 = 64 bytes → 必要な次元数に拡張
        values: list[float] = []
        for i in range(self.EMBEDDING_DIM):
            byte_val = hash_bytes[i % len(hash_bytes)]
            values.append((byte_val / 255.0) * 2 - 1)  # [-1, 1]に正規化
        return values

    async def ensure_extension(self) -> None:
        """pgvector拡張が有効であることを確認"""
        session = await self._get_session()
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await session.commit()

    async def add_documents(
        self,
        documents: list[dict[str, Any]],
        tenant_id: str,
    ) -> int:
        """文書をベクトル化して保存

        Args:
            documents: [{"content": str, "doc_type": str, "metadata": dict, "source_id": str}]
            tenant_id: テナントID
        """
        session = await self._get_session()
        count = 0

        for doc in documents:
            content = doc.get("content", "")
            if not content:
                continue

            embedding = await self._generate_embedding(content)
            doc_id = str(uuid_mod.uuid4())

            # pgvectorのベクトル型にINSERT
            await session.execute(
                text(
                    "INSERT INTO vector_documents "
                    "(id, tenant_id, content, metadata, doc_type, source_id, embedding) "
                    "VALUES (:id, :tenant_id, :content, :metadata, :doc_type, :source_id, :embedding)"
                ),
                {
                    "id": doc_id,
                    "tenant_id": tenant_id,
                    "content": content,
                    "metadata": doc.get("metadata", {}),
                    "doc_type": doc.get("doc_type", "general"),
                    "source_id": doc.get("source_id"),
                    "embedding": str(embedding),
                },
            )
            count += 1

        await session.commit()
        logger.info("文書追加完了: {}件 (tenant: {})", count, tenant_id)
        return count

    async def search(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
        doc_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """セマンティック検索 — pgvector cosine distance

        HNSWインデックスによる高速近傍検索。
        """
        session = await self._get_session()
        query_embedding = await self._generate_embedding(query)

        # pgvector cosine distance: <=> 演算子
        filter_clauses = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "query_embedding": str(query_embedding),
            "top_k": top_k,
        }

        if doc_type:
            filter_clauses.append("doc_type = :doc_type")
            params["doc_type"] = doc_type

        where_clause = " AND ".join(filter_clauses)

        result = await session.execute(
            text(
                f"SELECT id, content, metadata, doc_type, source_id, "  # noqa: S608
                f"1 - (embedding <=> :query_embedding::vector) AS similarity "
                f"FROM vector_documents "
                f"WHERE {where_clause} "
                f"ORDER BY embedding <=> :query_embedding::vector "
                f"LIMIT :top_k"
            ),
            params,
        )

        rows = result.fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "content": row[1],
                    "metadata": row[2],
                    "doc_type": row[3],
                    "source_id": row[4],
                    "similarity": float(row[5]),
                }
            )

        logger.debug(
            "ベクトル検索完了: query='{}', results={}, top_similarity={}",
            query[:50],
            len(results),
            f"{results[0]['similarity']:.3f}" if results else "N/A",
        )
        return results

    async def delete_by_tenant(self, tenant_id: str) -> int:
        """テナント単位で文書削除"""
        session = await self._get_session()
        result = await session.execute(
            text("DELETE FROM vector_documents WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        await session.commit()
        count = result.rowcount or 0
        logger.info("テナント文書削除: {}件 (tenant: {})", count, tenant_id)
        return count

    async def delete_by_source(self, tenant_id: str, source_id: str) -> int:
        """ソースID単位で文書削除"""
        session = await self._get_session()
        result = await session.execute(
            text("DELETE FROM vector_documents WHERE tenant_id = :tenant_id AND source_id = :source_id"),
            {"tenant_id": tenant_id, "source_id": source_id},
        )
        await session.commit()
        return result.rowcount or 0

    async def count(self, tenant_id: str, doc_type: str | None = None) -> int:
        """文書数をカウント"""
        session = await self._get_session()
        query_str = "SELECT COUNT(*) FROM vector_documents WHERE tenant_id = :tenant_id"
        params: dict[str, str] = {"tenant_id": tenant_id}
        if doc_type:
            query_str += " AND doc_type = :doc_type"
            params["doc_type"] = doc_type
        result = await session.execute(text(query_str), params)
        return result.scalar_one()  # type: ignore[no-any-return]
