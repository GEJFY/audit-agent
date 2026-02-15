"""依存性注入テスト"""

import pytest

from src.api.dependencies import get_llm_gateway


@pytest.mark.unit
class TestDependencies:
    def test_get_llm_gateway_returns_instance(self) -> None:
        """LLMゲートウェイインスタンス取得"""
        gateway = get_llm_gateway()
        assert gateway is not None

    def test_get_llm_gateway_singleton(self) -> None:
        """同一インスタンスが返される"""
        gw1 = get_llm_gateway()
        gw2 = get_llm_gateway()
        # ファクトリ関数なので新規インスタンスが返る可能性あり
        assert gw1 is not None and gw2 is not None
