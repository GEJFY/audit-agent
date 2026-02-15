"""APAC リージョン設定 テスト"""

import pytest

from src.config.regions import (
    REGION_CONFIGS,
    APACRegion,
    get_fiscal_year_months,
    get_region_config,
    list_supported_regions,
)


@pytest.mark.unit
class TestAPACRegionEnum:
    """APACRegion 列挙型テスト"""

    def test_jp(self) -> None:
        assert APACRegion.JP == "JP"

    def test_sg(self) -> None:
        assert APACRegion.SG == "SG"

    def test_all_regions(self) -> None:
        assert len(APACRegion) == 7


@pytest.mark.unit
class TestRegionConfig:
    """RegionConfig テスト"""

    def test_jp_config(self) -> None:
        """日本リージョン設定"""
        config = get_region_config("JP")
        assert config.name_en == "Japan"
        assert config.timezone == "Asia/Tokyo"
        assert config.accounting_standard == "J-GAAP / IFRS"
        assert config.language == "ja"
        assert config.currency == "JPY"
        assert config.fiscal_year_start_month == 4
        assert config.data_residency_required is True
        assert "金融庁" in config.regulatory_bodies

    def test_sg_config(self) -> None:
        """シンガポールリージョン設定"""
        config = get_region_config("SG")
        assert config.name_en == "Singapore"
        assert config.timezone == "Asia/Singapore"
        assert config.language == "en"
        assert config.fiscal_year_start_month == 1

    def test_hk_config(self) -> None:
        """香港リージョン設定"""
        config = get_region_config("HK")
        assert config.name_en == "Hong Kong"
        assert config.currency == "HKD"

    def test_au_config(self) -> None:
        """オーストラリアリージョン設定"""
        config = get_region_config("AU")
        assert config.fiscal_year_start_month == 7
        assert config.data_residency_required is True

    def test_kr_config(self) -> None:
        """韓国リージョン設定"""
        config = get_region_config("KR")
        assert config.accounting_standard == "K-IFRS"
        assert config.data_residency_required is True

    def test_case_insensitive(self) -> None:
        """大文字小文字を区別しない"""
        config = get_region_config("jp")
        assert config.code == "JP"

    def test_unsupported_region(self) -> None:
        """未対応リージョンでValueError"""
        with pytest.raises(ValueError, match="Unsupported region"):
            get_region_config("XX")

    def test_frozen_dataclass(self) -> None:
        """frozen=Trueで変更不可"""
        config = get_region_config("JP")
        with pytest.raises(AttributeError):
            config.code = "US"  # type: ignore[misc]


@pytest.mark.unit
class TestListSupportedRegions:
    """対応リージョン一覧テスト"""

    def test_returns_list(self) -> None:
        regions = list_supported_regions()
        assert isinstance(regions, list)

    def test_contains_all_regions(self) -> None:
        regions = list_supported_regions()
        assert "JP" in regions
        assert "SG" in regions
        assert "HK" in regions
        assert "AU" in regions
        assert "TW" in regions
        assert "KR" in regions
        assert "TH" in regions

    def test_count(self) -> None:
        regions = list_supported_regions()
        assert len(regions) == 7


@pytest.mark.unit
class TestFiscalYearMonths:
    """会計年度月リストテスト"""

    def test_jp_fiscal_year(self) -> None:
        """日本: 4月始まり"""
        months = get_fiscal_year_months("JP")
        assert months[0] == 4
        assert months[-1] == 3
        assert len(months) == 12

    def test_sg_fiscal_year(self) -> None:
        """シンガポール: 1月始まり"""
        months = get_fiscal_year_months("SG")
        assert months[0] == 1
        assert months[-1] == 12

    def test_au_fiscal_year(self) -> None:
        """オーストラリア: 7月始まり"""
        months = get_fiscal_year_months("AU")
        assert months[0] == 7
        assert months[-1] == 6


@pytest.mark.unit
class TestRegionConfigsMaster:
    """REGION_CONFIGSマスターデータテスト"""

    def test_all_have_timezone(self) -> None:
        """全リージョンにタイムゾーン設定"""
        for code, config in REGION_CONFIGS.items():
            assert config.timezone, f"{code} has no timezone"

    def test_all_have_accounting_standard(self) -> None:
        """全リージョンに会計基準"""
        for code, config in REGION_CONFIGS.items():
            assert config.accounting_standard, f"{code} has no accounting standard"

    def test_all_have_regulatory_bodies(self) -> None:
        """全リージョンに規制当局"""
        for code, config in REGION_CONFIGS.items():
            assert len(config.regulatory_bodies) > 0, (
                f"{code} has no regulatory bodies"
            )

    def test_all_have_currency(self) -> None:
        """全リージョンに通貨"""
        for code, config in REGION_CONFIGS.items():
            assert len(config.currency) == 3, f"{code} currency is not 3-letter"
