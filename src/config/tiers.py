"""テナントTier管理 — 機能マトリクス・リソース制限"""

from dataclasses import dataclass
from enum import StrEnum


class TenantTier(StrEnum):
    """テナントTier"""

    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class TierFeatures:
    """Tier別機能セット"""

    tier: TenantTier
    max_projects: int
    max_users: int
    max_agents_concurrent: int
    custom_ml_models: bool
    dedicated_tenant_db: bool
    sla_guarantee: bool
    cross_company_analytics: bool
    predictive_risk: bool
    api_rate_limit_per_min: int
    storage_gb: int
    retention_days: int
    support_level: str  # community, business, premium


# ── Tier別機能マトリクス ──────────────────────────────
TIER_FEATURES: dict[str, TierFeatures] = {
    "starter": TierFeatures(
        tier=TenantTier.STARTER,
        max_projects=5,
        max_users=10,
        max_agents_concurrent=2,
        custom_ml_models=False,
        dedicated_tenant_db=False,
        sla_guarantee=False,
        cross_company_analytics=False,
        predictive_risk=False,
        api_rate_limit_per_min=60,
        storage_gb=10,
        retention_days=90,
        support_level="community",
    ),
    "professional": TierFeatures(
        tier=TenantTier.PROFESSIONAL,
        max_projects=50,
        max_users=100,
        max_agents_concurrent=5,
        custom_ml_models=False,
        dedicated_tenant_db=False,
        sla_guarantee=True,
        cross_company_analytics=True,
        predictive_risk=True,
        api_rate_limit_per_min=300,
        storage_gb=100,
        retention_days=365,
        support_level="business",
    ),
    "enterprise": TierFeatures(
        tier=TenantTier.ENTERPRISE,
        max_projects=0,  # 無制限
        max_users=0,  # 無制限
        max_agents_concurrent=20,
        custom_ml_models=True,
        dedicated_tenant_db=True,
        sla_guarantee=True,
        cross_company_analytics=True,
        predictive_risk=True,
        api_rate_limit_per_min=1000,
        storage_gb=1000,
        retention_days=2555,  # 7年
        support_level="premium",
    ),
}


def get_tier_features(tier: str) -> TierFeatures:
    """Tier別機能セットを取得

    Args:
        tier: Tier名 (starter, professional, enterprise)

    Raises:
        ValueError: 未知のTier
    """
    features = TIER_FEATURES.get(tier.lower())
    if not features:
        supported = ", ".join(TIER_FEATURES.keys())
        raise ValueError(f"Unknown tier: {tier}. Supported: {supported}")
    return features


def check_feature_access(tier: str, feature: str) -> bool:
    """指定Tierで機能が利用可能かチェック

    Args:
        tier: Tier名
        feature: 機能名 (TierFeaturesのフィールド名)

    Returns:
        利用可能ならTrue
    """
    features = get_tier_features(tier)
    value = getattr(features, feature, None)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0 or value == 0  # 0=無制限
    return True


def list_tiers() -> list[str]:
    """利用可能なTier一覧"""
    return list(TIER_FEATURES.keys())
