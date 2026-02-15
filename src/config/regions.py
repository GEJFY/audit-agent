"""APAC リージョン設定 — 地域固有の設定・規制マッピング

各リージョンの会計基準・監査基準・言語・タイムゾーンを管理。
"""

from dataclasses import dataclass, field
from enum import StrEnum


class APACRegion(StrEnum):
    """APAC対応リージョン"""

    JP = "JP"  # 日本
    SG = "SG"  # シンガポール
    HK = "HK"  # 香港
    AU = "AU"  # オーストラリア
    TW = "TW"  # 台湾
    KR = "KR"  # 韓国
    TH = "TH"  # タイ


@dataclass(frozen=True)
class RegionConfig:
    """リージョン固有設定"""

    code: str
    name_en: str
    name_local: str
    timezone: str
    accounting_standard: str
    audit_framework: str
    language: str
    currency: str
    fiscal_year_start_month: int = 4  # 4=4月始まり
    data_residency_required: bool = False
    regulatory_bodies: list[str] = field(default_factory=list)


# ── リージョン設定マスター ──────────────────────────
REGION_CONFIGS: dict[str, RegionConfig] = {
    "JP": RegionConfig(
        code="JP",
        name_en="Japan",
        name_local="日本",
        timezone="Asia/Tokyo",
        accounting_standard="J-GAAP / IFRS",
        audit_framework="J-SOX (内部統制報告制度)",
        language="ja",
        currency="JPY",
        fiscal_year_start_month=4,
        data_residency_required=True,
        regulatory_bodies=["金融庁", "東京証券取引所"],
    ),
    "SG": RegionConfig(
        code="SG",
        name_en="Singapore",
        name_local="Singapore",
        timezone="Asia/Singapore",
        accounting_standard="SFRS(I) / IFRS",
        audit_framework="SGX Listing Rules",
        language="en",
        currency="SGD",
        fiscal_year_start_month=1,
        data_residency_required=False,
        regulatory_bodies=["MAS", "ACRA", "SGX"],
    ),
    "HK": RegionConfig(
        code="HK",
        name_en="Hong Kong",
        name_local="香港",
        timezone="Asia/Hong_Kong",
        accounting_standard="HKFRS / IFRS",
        audit_framework="HKEX Listing Rules",
        language="zh-HK",
        currency="HKD",
        fiscal_year_start_month=1,
        data_residency_required=False,
        regulatory_bodies=["SFC", "HKEX"],
    ),
    "AU": RegionConfig(
        code="AU",
        name_en="Australia",
        name_local="Australia",
        timezone="Australia/Sydney",
        accounting_standard="AASB / IFRS",
        audit_framework="ASX Corporate Governance",
        language="en",
        currency="AUD",
        fiscal_year_start_month=7,
        data_residency_required=True,
        regulatory_bodies=["ASIC", "ASX", "APRA"],
    ),
    "TW": RegionConfig(
        code="TW",
        name_en="Taiwan",
        name_local="台灣",
        timezone="Asia/Taipei",
        accounting_standard="TIFRS / IFRS",
        audit_framework="Taiwan SOX",
        language="zh-TW",
        currency="TWD",
        fiscal_year_start_month=1,
        data_residency_required=False,
        regulatory_bodies=["FSC", "TWSE"],
    ),
    "KR": RegionConfig(
        code="KR",
        name_en="South Korea",
        name_local="대한민국",
        timezone="Asia/Seoul",
        accounting_standard="K-IFRS",
        audit_framework="Internal Accounting Control System",
        language="ko",
        currency="KRW",
        fiscal_year_start_month=1,
        data_residency_required=True,
        regulatory_bodies=["FSS", "KRX"],
    ),
    "TH": RegionConfig(
        code="TH",
        name_en="Thailand",
        name_local="ประเทศไทย",
        timezone="Asia/Bangkok",
        accounting_standard="TFRS / IFRS",
        audit_framework="SEC Thailand Guidelines",
        language="th",
        currency="THB",
        fiscal_year_start_month=1,
        data_residency_required=False,
        regulatory_bodies=["SEC", "SET", "BOT"],
    ),
}


def get_region_config(region_code: str) -> RegionConfig:
    """リージョン設定を取得

    Args:
        region_code: ISO 3166-1 alpha-2 コード

    Raises:
        ValueError: 未対応リージョン
    """
    config = REGION_CONFIGS.get(region_code.upper())
    if not config:
        supported = ", ".join(REGION_CONFIGS.keys())
        raise ValueError(f"Unsupported region: {region_code}. Supported: {supported}")
    return config


def list_supported_regions() -> list[str]:
    """対応リージョン一覧"""
    return list(REGION_CONFIGS.keys())


def get_fiscal_year_months(region_code: str) -> list[int]:
    """リージョンの会計年度月リスト（開始月から12ヶ月）"""
    config = get_region_config(region_code)
    start = config.fiscal_year_start_month
    return [(start + i - 1) % 12 + 1 for i in range(12)]
