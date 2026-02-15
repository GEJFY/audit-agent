"""コンプライアンスフレームワークチェッカー

各リージョンの規制要件（SOC2, ISO27001, GDPR, PDPA, PIPL）への
準拠状況を評価するチェッカー。リージョン設定に基づき適用フレームワークを選定。
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from loguru import logger

from src.config.regions import REGION_CONFIGS


class ComplianceFramework(StrEnum):
    """対応コンプライアンスフレームワーク"""

    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    GDPR = "GDPR"
    PDPA = "PDPA"
    PIPL = "PIPL"
    JSOX = "J-SOX"


class ComplianceStatus(StrEnum):
    """準拠ステータス"""

    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_ASSESSED = "not_assessed"


@dataclass
class ComplianceFinding:
    """コンプライアンス所見"""

    control_id: str
    description: str
    severity: str  # high, medium, low
    recommendation: str = ""


@dataclass
class ComplianceCheckResult:
    """コンプライアンスチェック結果"""

    framework: str
    status: ComplianceStatus
    score: float  # 0.0-100.0
    findings: list[ComplianceFinding] = field(default_factory=list)
    checked_at: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def high_severity_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")


# ── リージョン→フレームワーク マッピング ──────────────
REGION_FRAMEWORKS: dict[str, list[ComplianceFramework]] = {
    "JP": [ComplianceFramework.JSOX, ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
    "SG": [ComplianceFramework.PDPA, ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
    "HK": [ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
    "AU": [ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
    "TW": [ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
    "KR": [ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
    "TH": [ComplianceFramework.PDPA, ComplianceFramework.SOC2],
    "EU": [ComplianceFramework.GDPR, ComplianceFramework.SOC2, ComplianceFramework.ISO27001],
    "CN": [ComplianceFramework.PIPL, ComplianceFramework.ISO27001],
}


class ComplianceChecker:
    """コンプライアンスチェッカー

    監査データ・セキュリティ設定に基づき、各フレームワークへの準拠状況を評価。
    """

    def get_applicable_frameworks(self, region: str) -> list[ComplianceFramework]:
        """リージョンに適用されるフレームワーク一覧"""
        return REGION_FRAMEWORKS.get(region.upper(), [ComplianceFramework.SOC2])

    def check_soc2(self, audit_data: dict[str, Any] | None = None) -> ComplianceCheckResult:
        """SOC2 (Trust Service Criteria) チェック"""
        data = audit_data or {}
        findings: list[ComplianceFinding] = []
        score = 100.0

        # CC6.1: 論理・物理アクセス制御
        if not data.get("access_control_enabled"):
            findings.append(
                ComplianceFinding(
                    control_id="CC6.1",
                    description="論理的アクセス制御が未設定です",
                    severity="high",
                    recommendation="RBACの有効化と定期的な権限レビューを実施してください",
                )
            )
            score -= 20.0

        # CC7.2: システム監視
        if not data.get("monitoring_enabled"):
            findings.append(
                ComplianceFinding(
                    control_id="CC7.2",
                    description="システム監視が未有効化です",
                    severity="medium",
                    recommendation="監視ダッシュボードとアラートの設定を推奨します",
                )
            )
            score -= 10.0

        # CC8.1: 変更管理
        if not data.get("change_management_enabled"):
            findings.append(
                ComplianceFinding(
                    control_id="CC8.1",
                    description="変更管理プロセスが未文書化です",
                    severity="medium",
                    recommendation="変更管理手順書の作成と承認フローの導入を推奨します",
                )
            )
            score -= 10.0

        # CC6.3: 暗号化
        if not data.get("encryption_at_rest"):
            findings.append(
                ComplianceFinding(
                    control_id="CC6.3",
                    description="保存データの暗号化が未実施です",
                    severity="high",
                    recommendation="AES-256による保存データ暗号化を実施してください",
                )
            )
            score -= 15.0

        # CC7.3: 監査ログ
        if not data.get("audit_trail_enabled"):
            findings.append(
                ComplianceFinding(
                    control_id="CC7.3",
                    description="監査証跡が未有効化です",
                    severity="high",
                    recommendation="全操作の監査ログ記録を有効化してください",
                )
            )
            score -= 20.0

        status = self._score_to_status(score)
        return ComplianceCheckResult(
            framework="SOC2",
            status=status,
            score=max(0.0, score),
            findings=findings,
            checked_at=datetime.now(tz=UTC).isoformat(),
        )

    def check_iso27001(self, audit_data: dict[str, Any] | None = None) -> ComplianceCheckResult:
        """ISO 27001 (ISMS) チェック"""
        data = audit_data or {}
        findings: list[ComplianceFinding] = []
        score = 100.0

        # A.9: アクセス制御
        if not data.get("access_control_enabled"):
            findings.append(
                ComplianceFinding(
                    control_id="A.9.1",
                    description="アクセス制御ポリシーが未策定です",
                    severity="high",
                    recommendation="アクセス制御ポリシーの策定と実装を推奨します",
                )
            )
            score -= 15.0

        # A.10: 暗号化
        if not data.get("encryption_at_rest") or not data.get("encryption_in_transit"):
            findings.append(
                ComplianceFinding(
                    control_id="A.10.1",
                    description="暗号化対策が不完全です",
                    severity="high",
                    recommendation="保存時・転送時両方の暗号化を実施してください",
                )
            )
            score -= 15.0

        # A.12: 運用セキュリティ
        if not data.get("monitoring_enabled"):
            findings.append(
                ComplianceFinding(
                    control_id="A.12.4",
                    description="イベントログ・監視が不十分です",
                    severity="medium",
                    recommendation="ログ管理と監視体制の強化を推奨します",
                )
            )
            score -= 10.0

        # A.18: コンプライアンス
        if not data.get("data_residency_compliance"):
            region_config = REGION_CONFIGS.get(data.get("region", "JP"))
            if region_config and region_config.data_residency_required:
                findings.append(
                    ComplianceFinding(
                        control_id="A.18.1",
                        description="データ居住地要件を満たしていない可能性があります",
                        severity="high",
                        recommendation="データ保管場所がリージョン要件を満たしているか確認してください",
                    )
                )
                score -= 15.0

        status = self._score_to_status(score)
        return ComplianceCheckResult(
            framework="ISO27001",
            status=status,
            score=max(0.0, score),
            findings=findings,
            checked_at=datetime.now(tz=UTC).isoformat(),
        )

    def check_gdpr(self, audit_data: dict[str, Any] | None = None) -> ComplianceCheckResult:
        """GDPR (EU一般データ保護規則) チェック"""
        data = audit_data or {}
        findings: list[ComplianceFinding] = []
        score = 100.0

        # Art.30: 処理活動記録
        if not data.get("processing_records"):
            findings.append(
                ComplianceFinding(
                    control_id="Art.30",
                    description="データ処理活動の記録が不十分です",
                    severity="high",
                    recommendation="全データ処理活動の記録を作成・維持してください",
                )
            )
            score -= 20.0

        # Art.32: セキュリティ措置
        if not data.get("encryption_at_rest"):
            findings.append(
                ComplianceFinding(
                    control_id="Art.32",
                    description="個人データの暗号化措置が不十分です",
                    severity="high",
                    recommendation="個人データの暗号化・仮名化を実施してください",
                )
            )
            score -= 15.0

        # Art.35: DPIA
        if not data.get("dpia_completed"):
            findings.append(
                ComplianceFinding(
                    control_id="Art.35",
                    description="データ保護影響評価（DPIA）が未実施です",
                    severity="medium",
                    recommendation="高リスク処理についてDPIAを実施してください",
                )
            )
            score -= 10.0

        # Art.17: 削除権
        if not data.get("data_deletion_capability"):
            findings.append(
                ComplianceFinding(
                    control_id="Art.17",
                    description="データ削除権への対応が未実装です",
                    severity="medium",
                    recommendation="データ主体からの削除要求に対応するプロセスを構築してください",
                )
            )
            score -= 10.0

        status = self._score_to_status(score)
        return ComplianceCheckResult(
            framework="GDPR",
            status=status,
            score=max(0.0, score),
            findings=findings,
            checked_at=datetime.now(tz=UTC).isoformat(),
        )

    def check_pdpa(self, audit_data: dict[str, Any] | None = None) -> ComplianceCheckResult:
        """PDPA (シンガポール個人データ保護法) チェック"""
        data = audit_data or {}
        findings: list[ComplianceFinding] = []
        score = 100.0

        # 同意取得
        if not data.get("consent_management"):
            findings.append(
                ComplianceFinding(
                    control_id="PDPA-S13",
                    description="個人データ収集時の同意管理が不十分です",
                    severity="high",
                    recommendation="同意管理フレームワークの導入を推奨します",
                )
            )
            score -= 20.0

        # データ保護ポリシー
        if not data.get("data_protection_policy"):
            findings.append(
                ComplianceFinding(
                    control_id="PDPA-S24",
                    description="データ保護ポリシーが未策定です",
                    severity="medium",
                    recommendation="組織のデータ保護ポリシーを策定・公開してください",
                )
            )
            score -= 15.0

        # データ侵害通知
        if not data.get("breach_notification_process"):
            findings.append(
                ComplianceFinding(
                    control_id="PDPA-S26D",
                    description="データ侵害通知プロセスが未整備です",
                    severity="high",
                    recommendation="PDPC/当事者への通知プロセスを構築してください",
                )
            )
            score -= 15.0

        status = self._score_to_status(score)
        return ComplianceCheckResult(
            framework="PDPA",
            status=status,
            score=max(0.0, score),
            findings=findings,
            checked_at=datetime.now(tz=UTC).isoformat(),
        )

    def check_pipl(self, audit_data: dict[str, Any] | None = None) -> ComplianceCheckResult:
        """PIPL (中国個人情報保護法) チェック"""
        data = audit_data or {}
        findings: list[ComplianceFinding] = []
        score = 100.0

        # データローカライゼーション
        if not data.get("data_localization"):
            findings.append(
                ComplianceFinding(
                    control_id="PIPL-Art.40",
                    description="中国国内のデータローカライゼーション要件を満たしていません",
                    severity="high",
                    recommendation="中国国内でのデータ保管・処理体制を構築してください",
                )
            )
            score -= 25.0

        # 越境データ移転
        if not data.get("cross_border_assessment"):
            findings.append(
                ComplianceFinding(
                    control_id="PIPL-Art.38",
                    description="越境データ移転のセキュリティ評価が未実施です",
                    severity="high",
                    recommendation="CACによるセキュリティ評価または標準契約の締結を実施してください",
                )
            )
            score -= 20.0

        # 個人情報保護責任者
        if not data.get("dpo_appointed"):
            findings.append(
                ComplianceFinding(
                    control_id="PIPL-Art.52",
                    description="個人情報保護責任者が未任命です",
                    severity="medium",
                    recommendation="個人情報保護責任者の任命と連絡先の公開を推奨します",
                )
            )
            score -= 10.0

        status = self._score_to_status(score)
        return ComplianceCheckResult(
            framework="PIPL",
            status=status,
            score=max(0.0, score),
            findings=findings,
            checked_at=datetime.now(tz=UTC).isoformat(),
        )

    def check_all_frameworks(
        self,
        region: str,
        audit_data: dict[str, Any] | None = None,
    ) -> list[ComplianceCheckResult]:
        """リージョンに適用される全フレームワークをチェック"""
        frameworks = self.get_applicable_frameworks(region)
        results: list[ComplianceCheckResult] = []

        checker_map = {
            ComplianceFramework.SOC2: self.check_soc2,
            ComplianceFramework.ISO27001: self.check_iso27001,
            ComplianceFramework.GDPR: self.check_gdpr,
            ComplianceFramework.PDPA: self.check_pdpa,
            ComplianceFramework.PIPL: self.check_pipl,
            ComplianceFramework.JSOX: self.check_soc2,  # J-SOXはSOC2ベースで代替
        }

        for fw in frameworks:
            checker = checker_map.get(fw)
            if checker:
                result = checker(audit_data)
                if fw == ComplianceFramework.JSOX:
                    result.framework = "J-SOX"
                results.append(result)
                logger.info("コンプライアンスチェック完了: {} = {} ({:.1f})", fw, result.status, result.score)

        return results

    @staticmethod
    def _score_to_status(score: float) -> ComplianceStatus:
        """スコアからステータスを判定"""
        if score >= 80:
            return ComplianceStatus.COMPLIANT
        if score >= 50:
            return ComplianceStatus.PARTIAL
        return ComplianceStatus.NON_COMPLIANT
