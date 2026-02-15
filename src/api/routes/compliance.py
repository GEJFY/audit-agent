"""コンプライアンスエンドポイント — 規制準拠状況の確認・チェック"""

from typing import Any

from fastapi import APIRouter

from src.config.regions import REGION_CONFIGS, get_region_config
from src.security.compliance import ComplianceChecker

router = APIRouter()


@router.get("/status")
async def get_compliance_status(
    region: str = "JP",
) -> dict[str, Any]:
    """リージョン別コンプライアンス状況を取得

    Args:
        region: ISO 3166-1 alpha-2 リージョンコード
    """
    try:
        config = get_region_config(region)
    except ValueError:
        return {
            "status": "error",
            "message": f"Unsupported region: {region}",
            "supported_regions": list(REGION_CONFIGS.keys()),
        }

    return {
        "region": config.code,
        "region_name": config.name_en,
        "accounting_standard": config.accounting_standard,
        "audit_framework": config.audit_framework,
        "data_residency_required": config.data_residency_required,
        "regulatory_bodies": config.regulatory_bodies,
        "status": "active",
    }


@router.post("/check")
async def run_compliance_check(
    body: dict[str, Any],
) -> dict[str, Any]:
    """コンプライアンスチェックを実行

    Body:
        region: リージョンコード
        tenant_id: テナントID
        checks: チェック項目リスト (省略時は全チェック)
    """
    region = body.get("region", "JP")
    tenant_id = body.get("tenant_id", "")
    checks = body.get("checks", [])

    checker = ComplianceChecker()
    check_results = checker.check_all_frameworks(region=region)

    results: list[dict[str, Any]] = [
        {
            "check_id": r.framework,
            "framework": r.framework,
            "status": "passed" if r.status == "compliant" else "failed",
            "score": r.score,
            "finding_count": r.finding_count,
        }
        for r in check_results
    ]

    if checks:
        results = [r for r in results if r.get("check_id") in checks]

    passed = sum(1 for r in results if r.get("status") == "passed")
    failed = sum(1 for r in results if r.get("status") == "failed")

    return {
        "region": region,
        "tenant_id": tenant_id,
        "total_checks": len(results),
        "passed": passed,
        "failed": failed,
        "compliance_rate": round(passed / len(results) * 100, 1) if results else 0,
        "results": results,
    }
