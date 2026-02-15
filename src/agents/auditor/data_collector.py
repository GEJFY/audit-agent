"""Data Collector Agent — 監査データ自動取得"""

from typing import Any

from loguru import logger

from src.agents.base import BaseAuditAgent
from src.agents.state import AuditorState
from src.connectors.base import BaseConnector


class DataCollectorAgent(BaseAuditAgent[AuditorState]):
    """データ自動取得Agent — ERP・ファイルサーバ・DBからデータ収集

    テスト手続に定義されたデータソースに基づき、
    適切なコネクタを選択してデータを取得・検証する。
    """

    @property
    def agent_name(self) -> str:
        return "auditor_data_collector"

    @property
    def agent_description(self) -> str:
        return "監査データ自動取得 — 対象システムからのデータ抽出・変換・検証"

    async def execute(self, state: AuditorState) -> AuditorState:
        """監査計画に基づいてデータを収集"""
        logger.info("Data Collector: データ収集開始")

        plan = state.audit_plan
        test_procedures = plan.get("test_procedures", [])

        collected_data: list[dict[str, Any]] = []

        for procedure in test_procedures:
            data = await self._collect_for_procedure(procedure)
            collected_data.append(data)

            confidence = 0.9 if data.get("record_count", 0) > 0 else 0.3
            self.record_decision(  # type: ignore[call-arg]
                tenant_id=state.tenant_id,
                decision="data_collected",
                reasoning=(
                    f"手続: {data.get('procedure', '')[:100]}, "
                    f"件数: {data.get('record_count', 0)}, "
                    f"ソース: {data.get('source', '')}"
                ),
                confidence=confidence,
                resource_type="audit_data",
            )

        state.metadata["collected_data"] = collected_data
        state.metadata["collection_status"] = "completed"
        state.current_agent = self.agent_name

        logger.info("Data Collector: {}件のデータセット収集完了", len(collected_data))
        return state

    async def _collect_for_procedure(self, procedure: dict[str, Any] | str) -> dict[str, Any]:
        """テスト手続に基づいてデータ収集 — コネクタ経由"""
        if isinstance(procedure, str):
            procedure = {"description": procedure, "source_type": "sap", "module": "fi"}

        source_type = procedure.get("source_type", "sap")
        query = procedure.get("query", procedure.get("description", ""))

        connector = self._get_connector(source_type)
        if connector is None:
            logger.warning("コネクタ未設定: source_type={}", source_type)
            return {
                "procedure": str(procedure),
                "status": "skipped",
                "record_count": 0,
                "source": source_type,
                "error": f"コネクタ '{source_type}' が利用不可",
            }

        try:
            connected = await connector.connect()
            if not connected:
                return {
                    "procedure": str(procedure),
                    "status": "connection_failed",
                    "record_count": 0,
                    "source": source_type,
                }

            results = await connector.search(
                query,
                module=procedure.get("module", "fi"),
                top=procedure.get("max_records", 1000),
            )

            quality = self._validate_data_quality(results)

            return {
                "procedure": str(procedure.get("description", procedure)),
                "status": "collected",
                "record_count": len(results),
                "source": source_type,
                "data": results,
                "quality": quality,
            }
        except Exception as e:
            logger.error("データ収集エラー: source={}, error={}", source_type, str(e))
            return {
                "procedure": str(procedure),
                "status": "error",
                "record_count": 0,
                "source": source_type,
                "error": str(e),
            }
        finally:
            await connector.disconnect()

    def _get_connector(self, source_type: str) -> BaseConnector | None:
        """ソースタイプに応じたコネクタを取得"""
        if source_type in ("sap", "erp"):
            from src.connectors.sap import SAPConnector

            return SAPConnector()
        elif source_type == "sharepoint":
            from src.connectors.sharepoint import SharePointConnector

            return SharePointConnector()
        elif source_type == "email":
            from src.connectors.email import EmailConnector

            return EmailConnector()
        return None

    def _validate_data_quality(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """データ品質チェック"""
        if not data:
            return {"completeness": 0.0, "issues": ["データなし"]}

        total_fields = 0
        null_fields = 0
        issues: list[str] = []

        for record in data:
            for key, value in record.items():
                if key in ("source", "module"):
                    continue
                total_fields += 1
                if value is None or value == "":
                    null_fields += 1

        completeness = 1.0 - (null_fields / max(total_fields, 1))

        if completeness < 0.8:
            issues.append(f"NULL率が高い ({null_fields}/{total_fields})")

        # 重複チェック
        if len(data) > 1:
            string_reps = [str(sorted(d.items())) for d in data]
            unique = len(set(string_reps))
            if unique < len(data):
                issues.append(f"重複レコード {len(data) - unique}件")

        return {
            "completeness": round(completeness, 3),
            "record_count": len(data),
            "null_fields": null_fields,
            "issues": issues,
        }
