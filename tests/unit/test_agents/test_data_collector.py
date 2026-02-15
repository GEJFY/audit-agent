"""DataCollectorAgent テスト"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.auditor.data_collector import DataCollectorAgent
from src.agents.state import AuditorState


@pytest.fixture
def agent(mock_llm_gateway: MagicMock) -> DataCollectorAgent:
    a = DataCollectorAgent(llm_gateway=mock_llm_gateway)
    a._audit_trail = MagicMock()
    # record_decisionをMock化（data_collectorはresource_id未指定のため）
    a.record_decision = MagicMock()
    return a


def _mock_connector(records: list | None = None, connect_ok: bool = True) -> MagicMock:
    """コネクタモックを生成"""
    connector = MagicMock()
    connector.connect = AsyncMock(return_value=connect_ok)
    connector.search = AsyncMock(return_value=records or [])
    connector.disconnect = AsyncMock()
    return connector


@pytest.mark.unit
class TestDataCollectorAgent:
    def test_agent_name(self, agent: DataCollectorAgent) -> None:
        assert agent.agent_name == "auditor_data_collector"

    def test_agent_description(self, agent: DataCollectorAgent) -> None:
        assert agent.agent_description != ""

    async def test_execute_no_procedures(self, agent: DataCollectorAgent) -> None:
        """テスト手続なしの場合"""
        state = AuditorState(
            project_id=str(uuid4()),
            tenant_id=str(uuid4()),
            audit_plan={},
        )
        result = await agent.execute(state)
        assert result.metadata["collected_data"] == []
        assert result.metadata["collection_status"] == "completed"
        assert result.current_agent == "auditor_data_collector"

    async def test_collect_success(self, agent: DataCollectorAgent) -> None:
        """正常データ収集"""
        records = [{"id": "1", "amount": 100}, {"id": "2", "amount": 200}]
        connector = _mock_connector(records=records)

        with patch.object(agent, "_get_connector", return_value=connector):
            state = AuditorState(
                project_id=str(uuid4()),
                tenant_id=str(uuid4()),
                audit_plan={"test_procedures": [{"description": "売上テスト", "source_type": "sap", "module": "fi"}]},
            )
            result = await agent.execute(state)

        assert len(result.metadata["collected_data"]) == 1
        assert result.metadata["collected_data"][0]["status"] == "collected"
        assert result.metadata["collected_data"][0]["record_count"] == 2

    async def test_collect_connection_failure(self, agent: DataCollectorAgent) -> None:
        """接続失敗"""
        connector = _mock_connector(connect_ok=False)

        with patch.object(agent, "_get_connector", return_value=connector):
            state = AuditorState(
                project_id=str(uuid4()),
                tenant_id=str(uuid4()),
                audit_plan={"test_procedures": [{"description": "テスト", "source_type": "sap"}]},
            )
            result = await agent.execute(state)

        assert result.metadata["collected_data"][0]["status"] == "connection_failed"

    async def test_collect_connector_unavailable(self, agent: DataCollectorAgent) -> None:
        """コネクタ未設定"""
        with patch.object(agent, "_get_connector", return_value=None):
            state = AuditorState(
                project_id=str(uuid4()),
                tenant_id=str(uuid4()),
                audit_plan={"test_procedures": [{"description": "テスト", "source_type": "unknown_system"}]},
            )
            result = await agent.execute(state)

        assert result.metadata["collected_data"][0]["status"] == "skipped"

    async def test_collect_exception(self, agent: DataCollectorAgent) -> None:
        """収集中の例外"""
        connector = MagicMock()
        connector.connect = AsyncMock(return_value=True)
        connector.search = AsyncMock(side_effect=RuntimeError("接続タイムアウト"))
        connector.disconnect = AsyncMock()

        with patch.object(agent, "_get_connector", return_value=connector):
            state = AuditorState(
                project_id=str(uuid4()),
                tenant_id=str(uuid4()),
                audit_plan={"test_procedures": [{"description": "テスト", "source_type": "sap"}]},
            )
            result = await agent.execute(state)

        assert result.metadata["collected_data"][0]["status"] == "error"
        assert "接続タイムアウト" in result.metadata["collected_data"][0]["error"]

    async def test_string_procedure_defaults(self, agent: DataCollectorAgent) -> None:
        """文字列形式のテスト手続はデフォルトsap/fiに変換"""
        connector = _mock_connector(records=[])

        with patch.object(agent, "_get_connector", return_value=connector):
            state = AuditorState(
                project_id=str(uuid4()),
                tenant_id=str(uuid4()),
                audit_plan={"test_procedures": ["売上テスト"]},
            )
            await agent.execute(state)

        connector.search.assert_called_once()

    def test_validate_data_quality_empty(self, agent: DataCollectorAgent) -> None:
        """空データの品質チェック"""
        quality = agent._validate_data_quality([])
        assert quality["completeness"] == 0.0
        assert "データなし" in quality["issues"]

    def test_validate_data_quality_complete(self, agent: DataCollectorAgent) -> None:
        """完全データの品質チェック"""
        data = [{"id": "1", "amount": 100, "name": "テスト"}]
        quality = agent._validate_data_quality(data)
        assert quality["completeness"] == 1.0
        assert quality["issues"] == []

    def test_validate_data_quality_nulls(self, agent: DataCollectorAgent) -> None:
        """NULL含有データの品質チェック"""
        data = [{"id": "1", "amount": None, "name": ""}, {"id": "2", "amount": None, "name": "ok"}]
        quality = agent._validate_data_quality(data)
        assert quality["completeness"] < 1.0
        assert quality["null_fields"] > 0

    def test_validate_data_quality_duplicates(self, agent: DataCollectorAgent) -> None:
        """重複データ検出"""
        data = [{"id": "1", "amount": 100}, {"id": "1", "amount": 100}]
        quality = agent._validate_data_quality(data)
        assert any("重複" in issue for issue in quality["issues"])

    def test_get_connector_sap(self, agent: DataCollectorAgent) -> None:
        """SAPコネクタ取得（lazy import）"""
        with patch("src.connectors.sap.SAPConnector"):
            connector = agent._get_connector("sap")
            assert connector is not None

    def test_get_connector_erp(self, agent: DataCollectorAgent) -> None:
        """ERPはSAPと同じコネクタ"""
        with patch("src.connectors.sap.SAPConnector"):
            connector = agent._get_connector("erp")
            assert connector is not None

    def test_get_connector_unknown(self, agent: DataCollectorAgent) -> None:
        """未知のソースタイプ"""
        connector = agent._get_connector("unknown_system")
        assert connector is None
