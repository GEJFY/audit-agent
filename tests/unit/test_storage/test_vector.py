"""ベクトルストアテスト"""

import pytest

from src.storage.vector import VectorStore


@pytest.mark.unit
class TestVectorStoreFallbackEmbedding:
    """フォールバックエンベディングテスト"""

    def test_fallback_embedding_length(self) -> None:
        """フォールバックベクトルの次元数"""
        store = VectorStore.__new__(VectorStore)
        embedding = store._fallback_embedding("テストテキスト")
        assert len(embedding) == VectorStore.EMBEDDING_DIM

    def test_fallback_embedding_range(self) -> None:
        """フォールバックベクトルの値範囲 [-1, 1]"""
        store = VectorStore.__new__(VectorStore)
        embedding = store._fallback_embedding("テストテキスト")
        for val in embedding:
            assert -1.0 <= val <= 1.0

    def test_fallback_embedding_deterministic(self) -> None:
        """同じ入力で同じベクトルが返る"""
        store = VectorStore.__new__(VectorStore)
        e1 = store._fallback_embedding("テスト")
        e2 = store._fallback_embedding("テスト")
        assert e1 == e2

    def test_fallback_embedding_different_input(self) -> None:
        """異なる入力で異なるベクトル"""
        store = VectorStore.__new__(VectorStore)
        e1 = store._fallback_embedding("テキストA")
        e2 = store._fallback_embedding("テキストB")
        assert e1 != e2

    def test_fallback_embedding_empty_string(self) -> None:
        """空文字列でも正常にベクトル生成"""
        store = VectorStore.__new__(VectorStore)
        embedding = store._fallback_embedding("")
        assert len(embedding) == VectorStore.EMBEDDING_DIM


@pytest.mark.unit
class TestVectorStoreConstants:
    """定数テスト"""

    def test_embedding_dim(self) -> None:
        """エンベディング次元数"""
        assert VectorStore.EMBEDDING_DIM == 1536
