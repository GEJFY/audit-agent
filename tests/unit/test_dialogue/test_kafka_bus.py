"""Kafka Bus テスト"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.dialogue.kafka_bus import KafkaBus
from src.dialogue.protocol import QuestionMessage


@pytest.mark.unit
class TestKafkaBus:
    """KafkaBusのユニットテスト"""

    def test_init(self) -> None:
        """初期化テスト"""
        bus = KafkaBus()
        assert bus._producer is None
        assert bus._consumer is None

    async def test_connect_no_servers(self) -> None:
        """bootstrap_servers未設定での接続テスト"""
        bus = KafkaBus()
        bus._bootstrap_servers = ""

        result = await bus.connect()
        assert result is False

    async def test_publish_without_connection(self) -> None:
        """未接続での送信テスト"""
        bus = KafkaBus()
        bus._bootstrap_servers = ""

        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="テスト",
        )

        result = await bus.publish(msg)
        assert result is False

    async def test_publish_with_mock_producer(self) -> None:
        """モックプロデューサーでの送信テスト"""
        bus = KafkaBus()
        bus._producer = AsyncMock()
        bus._producer.send_and_wait = AsyncMock()

        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_controls_tester",
            content="購買承認フローの詳細を教えてください",
        )

        result = await bus.publish(msg)
        assert result is True
        bus._producer.send_and_wait.assert_awaited_once()

    def test_on_message_handler(self) -> None:
        """メッセージハンドラ登録テスト"""
        bus = KafkaBus()
        handler = AsyncMock()
        tenant_id = str(uuid4())

        bus.on_message(tenant_id, handler)

        assert tenant_id in bus._handlers
        assert handler in bus._handlers[tenant_id]

    async def test_dispatch_message(self) -> None:
        """メッセージディスパッチテスト"""
        bus = KafkaBus()
        handler = AsyncMock()
        tenant_id = str(uuid4())

        bus.on_message(tenant_id, handler)

        payload = {
            "to_tenant_id": tenant_id,
            "content": "テストメッセージ",
        }

        await bus._dispatch_message(payload)
        handler.assert_awaited_once_with(payload)

    async def test_dispatch_message_no_handler(self) -> None:
        """ハンドラなしのメッセージディスパッチ"""
        bus = KafkaBus()
        payload = {
            "to_tenant_id": str(uuid4()),
            "content": "テスト",
        }

        # エラーなしで実行完了すること
        await bus._dispatch_message(payload)

    async def test_disconnect(self) -> None:
        """切断テスト"""
        bus = KafkaBus()
        bus._producer = AsyncMock()
        bus._consumer = AsyncMock()

        await bus.disconnect()

        bus._producer.stop.assert_awaited_once()
        bus._consumer.stop.assert_awaited_once()
        assert bus._producer is None
        assert bus._consumer is None
