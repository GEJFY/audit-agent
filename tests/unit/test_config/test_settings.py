"""Settings テスト"""

import pytest

from src.config.settings import Settings


@pytest.mark.unit
class TestSettings:
    """Settings設定テスト"""

    def test_defaults(self) -> None:
        """デフォルト値の確認"""
        s = Settings()
        assert s.app_name == "audit-agent"
        assert s.app_env == "testing"  # conftest.pyで設定済み
        assert s.default_region == "JP"

    def test_is_production_false(self) -> None:
        """テスト環境では本番ではない"""
        s = Settings()
        assert s.is_production is False

    def test_is_development_false_in_testing(self) -> None:
        """テスト環境ではdevelopmentではない"""
        s = Settings()
        assert s.is_development is False

    def test_is_production_true(self) -> None:
        """本番環境判定"""
        s = Settings(app_env="production")
        assert s.is_production is True

    def test_is_development_true(self) -> None:
        """開発環境判定"""
        s = Settings(app_env="development")
        assert s.is_development is True

    def test_supported_regions(self) -> None:
        """対応リージョン一覧"""
        s = Settings()
        assert "JP" in s.supported_regions
        assert "SG" in s.supported_regions
        assert len(s.supported_regions) >= 7

    def test_jwt_secret_key_has_default(self) -> None:
        """JWTシークレットキーのデフォルト"""
        s = Settings()
        assert s.jwt_secret_key != ""

    def test_cors_origins_default(self) -> None:
        """CORSオリジンのデフォルト"""
        s = Settings()
        assert isinstance(s.cors_origins, list)

    def test_cors_origins_from_string(self) -> None:
        """JSON文字列からのCORSオリジンパース"""
        s = Settings(cors_origins='["http://example.com"]')
        assert "http://example.com" in s.cors_origins

    def test_app_debug_default(self) -> None:
        """デバッグモードデフォルト"""
        s = Settings()
        assert isinstance(s.app_debug, bool)
