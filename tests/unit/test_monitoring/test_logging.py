"""ロギング設定テスト"""

import pytest

from src.monitoring.logging import (
    correlation_id_var,
    get_logger,
    setup_logging,
    tenant_id_var,
)


@pytest.mark.unit
class TestContextVars:
    """コンテキスト変数テスト"""

    def test_correlation_id_default(self) -> None:
        """相関IDのデフォルト値"""
        assert correlation_id_var.get("") == ""

    def test_tenant_id_default(self) -> None:
        """テナントIDのデフォルト値"""
        assert tenant_id_var.get("") == ""

    def test_correlation_id_set_get(self) -> None:
        """相関IDの設定・取得"""
        token = correlation_id_var.set("req-001")
        try:
            assert correlation_id_var.get() == "req-001"
        finally:
            correlation_id_var.reset(token)

    def test_tenant_id_set_get(self) -> None:
        """テナントIDの設定・取得"""
        token = tenant_id_var.set("t-001")
        try:
            assert tenant_id_var.get() == "t-001"
        finally:
            tenant_id_var.reset(token)


@pytest.mark.unit
class TestSetupLogging:
    """setup_logging関数テスト"""

    def test_setup_json_output(self) -> None:
        """JSON出力モードの設定"""
        setup_logging(level="WARNING", json_output=True)
        # エラーなく完了すればOK

    def test_setup_dev_output(self) -> None:
        """開発モードの設定"""
        setup_logging(level="DEBUG", json_output=False)
        # エラーなく完了すればOK


@pytest.mark.unit
class TestGetLogger:
    """get_logger関数テスト"""

    def test_returns_logger(self) -> None:
        """ロガーを返す"""
        logger = get_logger("test_module")
        assert logger is not None

    def test_different_names(self) -> None:
        """異なるモジュール名で呼び出し可能"""
        l1 = get_logger("module_a")
        l2 = get_logger("module_b")
        assert l1 is not None
        assert l2 is not None
