"""テナントTier管理テスト"""

import pytest

from src.config.tiers import (
    TIER_FEATURES,
    TenantTier,
    check_feature_access,
    get_tier_features,
    list_tiers,
)


@pytest.mark.unit
class TestTenantTier:
    """TenantTier enumテスト"""

    def test_values(self) -> None:
        assert TenantTier.STARTER == "starter"
        assert TenantTier.PROFESSIONAL == "professional"
        assert TenantTier.ENTERPRISE == "enterprise"


@pytest.mark.unit
class TestTierFeatures:
    """TierFeaturesテスト"""

    def test_starter_features(self) -> None:
        """Starter Tier"""
        f = TIER_FEATURES["starter"]
        assert f.tier == TenantTier.STARTER
        assert f.max_projects == 5
        assert f.max_users == 10
        assert f.custom_ml_models is False
        assert f.dedicated_tenant_db is False
        assert f.sla_guarantee is False
        assert f.support_level == "community"

    def test_professional_features(self) -> None:
        """Professional Tier"""
        f = TIER_FEATURES["professional"]
        assert f.tier == TenantTier.PROFESSIONAL
        assert f.max_projects == 50
        assert f.sla_guarantee is True
        assert f.cross_company_analytics is True
        assert f.predictive_risk is True
        assert f.support_level == "business"

    def test_enterprise_features(self) -> None:
        """Enterprise Tier"""
        f = TIER_FEATURES["enterprise"]
        assert f.tier == TenantTier.ENTERPRISE
        assert f.max_projects == 0  # 無制限
        assert f.custom_ml_models is True
        assert f.dedicated_tenant_db is True
        assert f.sla_guarantee is True
        assert f.storage_gb == 1000
        assert f.retention_days == 2555
        assert f.support_level == "premium"

    def test_frozen_dataclass(self) -> None:
        """frozen=Trueで変更不可"""
        f = TIER_FEATURES["starter"]
        with pytest.raises(AttributeError):
            f.max_projects = 999  # type: ignore[misc]


@pytest.mark.unit
class TestGetTierFeatures:
    """get_tier_features関数テスト"""

    def test_valid_tier(self) -> None:
        f = get_tier_features("enterprise")
        assert f.tier == TenantTier.ENTERPRISE

    def test_case_insensitive(self) -> None:
        f = get_tier_features("ENTERPRISE")
        assert f.tier == TenantTier.ENTERPRISE

    def test_unknown_tier(self) -> None:
        with pytest.raises(ValueError, match="Unknown tier"):
            get_tier_features("unknown")


@pytest.mark.unit
class TestCheckFeatureAccess:
    """check_feature_access関数テスト"""

    def test_starter_no_custom_ml(self) -> None:
        assert check_feature_access("starter", "custom_ml_models") is False

    def test_enterprise_custom_ml(self) -> None:
        assert check_feature_access("enterprise", "custom_ml_models") is True

    def test_starter_cross_company(self) -> None:
        assert check_feature_access("starter", "cross_company_analytics") is False

    def test_professional_cross_company(self) -> None:
        assert check_feature_access("professional", "cross_company_analytics") is True

    def test_unknown_feature(self) -> None:
        assert check_feature_access("enterprise", "nonexistent_feature") is False

    def test_int_feature(self) -> None:
        """整数フィールドのチェック"""
        assert check_feature_access("starter", "max_projects") is True


@pytest.mark.unit
class TestListTiers:
    """list_tiers関数テスト"""

    def test_returns_all_tiers(self) -> None:
        tiers = list_tiers()
        assert "starter" in tiers
        assert "professional" in tiers
        assert "enterprise" in tiers
        assert len(tiers) == 3
