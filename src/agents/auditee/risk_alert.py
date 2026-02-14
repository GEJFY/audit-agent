"""Risk Alert Agent — 365日リアルタイムリスク監視"""

import json
from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditeeState


class RiskAlertAgent(BaseAuditAgent[AuditeeState]):
    """リスクアラートAgent — 365日稼働のリアルタイム異常検知

    監視対象:
    - 財務: 異常仕訳、売上急変、在庫異常、滞留債権
    - 業務: 承認逸脱率、処理遅延、例外処理急増
    - IT: 不正アクセス、特権使用、大量DL
    - コンプライアンス: 規制変更影響、契約期限、研修未受講
    - 外部: 取引先信用低下、規制動向
    """

    @property
    def agent_name(self) -> str:
        return "auditee_risk_alert"

    @property
    def agent_description(self) -> str:
        return "365日リスク監視 — リアルタイム異常検知・KPI急変・SoD違反・外部リスク"

    async def execute(self, state: AuditeeState) -> AuditeeState:
        """リスク監視スキャン実行"""
        logger.info("Risk Alert: リスクスキャン開始")

        alerts: list[dict[str, Any]] = []

        # 各カテゴリのリスクチェック
        for category in ["financial", "operational", "it", "compliance", "external"]:
            category_alerts = await self._scan_category(category, state)
            alerts.extend(category_alerts)

        # 重大リスクの自動エスカレーション判定
        for alert in alerts:
            if alert.get("severity") in ("critical", "high"):
                alert["escalate_to_auditor"] = True
                logger.warning(
                    f"重大リスク検出 — Auditor側にエスカレーション",
                    alert_type=alert.get("type"),
                    severity=alert.get("severity"),
                )

        state.risk_alerts = alerts
        state.current_agent = self.agent_name
        logger.info(f"Risk Alert: {len(alerts)}件のアラート検出")
        return state

    async def _scan_category(
        self, category: str, state: AuditeeState
    ) -> list[dict[str, Any]]:
        """カテゴリ別リスクスキャン"""
        prompt = f"""
リスクカテゴリ「{category}」の監視データを分析してください。

テナントID: {state.tenant_id}
部門: {state.department}

以下のJSON形式でアラートを返してください:
[
    {{
        "type": "{category}",
        "severity": "critical|high|medium|low",
        "title": "アラートタイトル",
        "description": "詳細説明",
        "recommended_action": "推奨対応"
    }}
]

データがない場合は空配列[]を返してください。
"""
        response = await self.call_llm(prompt, use_fast_model=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return []
