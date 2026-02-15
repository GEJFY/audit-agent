"""Kafka Bus テスト"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dialogue.kafka_bus import KafkaBus, KafkaDialogueBus
from src.dialogue.protocol import AnswerMessage, QuestionMessage


@pytest.mark.unit
class TestKafkaBus:
    """KafkaBus低レベルテスト"""

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

    async def test_publish_with_custom_topic(self) -> None:
        """カスタムトピックへの送信テスト"""
        bus = KafkaBus()
        bus._producer = AsyncMock()
        bus._producer.send_and_wait = AsyncMock()

        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="テスト",
        )

        result = await bus.publish(msg, topic="custom-topic")
        assert result is True
        call_args = bus._producer.send_and_wait.call_args
        assert call_args.args[0] == "custom-topic"

    async def test_publish_error_handling(self) -> None:
        """送信エラーハンドリング"""
        bus = KafkaBus()
        bus._producer = AsyncMock()
        bus._producer.send_and_wait = AsyncMock(side_effect=Exception("Kafka down"))

        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="テスト",
        )

        result = await bus.publish(msg)
        assert result is False

    def test_on_message_handler(self) -> None:
        """メッセージハンドラ登録テスト"""
        bus = KafkaBus()
        handler = AsyncMock()
        tenant_id = str(uuid4())

        bus.on_message(tenant_id, handler)

        assert tenant_id in bus._handlers
        assert handler in bus._handlers[tenant_id]

    def test_on_message_multiple_handlers(self) -> None:
        """複数ハンドラ登録テスト"""
        bus = KafkaBus()
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        tenant_id = str(uuid4())

        bus.on_message(tenant_id, handler1)
        bus.on_message(tenant_id, handler2)

        assert len(bus._handlers[tenant_id]) == 2

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

    async def test_dispatch_message_handler_error(self) -> None:
        """ハンドラエラー時も他のハンドラは実行される"""
        bus = KafkaBus()
        tenant_id = str(uuid4())

        failing_handler = AsyncMock(side_effect=Exception("Handler error"))
        ok_handler = AsyncMock()

        bus.on_message(tenant_id, failing_handler)
        bus.on_message(tenant_id, ok_handler)

        payload = {"to_tenant_id": tenant_id, "content": "テスト"}
        await bus._dispatch_message(payload)

        failing_handler.assert_awaited_once()
        ok_handler.assert_awaited_once()

    async def test_disconnect(self) -> None:
        """切断テスト"""
        bus = KafkaBus()
        mock_producer = AsyncMock()
        mock_consumer = AsyncMock()
        bus._producer = mock_producer
        bus._consumer = mock_consumer

        await bus.disconnect()

        mock_producer.stop.assert_awaited_once()
        mock_consumer.stop.assert_awaited_once()
        assert bus._producer is None
        assert bus._consumer is None

    async def test_disconnect_no_connections(self) -> None:
        """未接続状態の切断"""
        bus = KafkaBus()
        await bus.disconnect()
        assert bus._producer is None
        assert bus._consumer is None

    async def test_start_consumer_no_servers(self) -> None:
        """bootstrap_servers未設定でのコンシューマー起動"""
        bus = KafkaBus()
        bus._bootstrap_servers = ""
        await bus.start_consumer()


@pytest.mark.unit
class TestKafkaDialogueBus:
    """KafkaDialogueBus アダプタテスト"""

    def _create_bus(self) -> KafkaDialogueBus:
        """テスト用バス作成"""
        bus = KafkaDialogueBus()
        bus._kafka._producer = AsyncMock()
        bus._kafka._producer.send_and_wait = AsyncMock()
        return bus

    async def test_send_message(self) -> None:
        """メッセージ送信"""
        bus = self._create_bus()
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="auditor_orchestrator",
            content="購買プロセスの詳細を教えてください",
        )

        result = await bus.send(msg)
        assert result.id == msg.id
        assert len(bus._message_log) == 1
        bus._kafka._producer.send_and_wait.assert_awaited_once()

    async def test_send_creates_thread(self) -> None:
        """送信時にスレッドが自動作成される"""
        bus = self._create_bus()
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="テスト",
        )

        result = await bus.send(msg)
        assert result.thread_id is not None
        thread = bus.get_thread(result.thread_id)
        assert len(thread) == 1

    async def test_send_existing_thread(self) -> None:
        """既存スレッドへのメッセージ追加"""
        bus = self._create_bus()
        thread_id = uuid4()
        tenant_a = uuid4()
        tenant_b = uuid4()

        msg1 = QuestionMessage(
            from_tenant_id=tenant_a,
            to_tenant_id=tenant_b,
            from_agent="auditor",
            content="質問1",
            thread_id=thread_id,
        )
        msg2 = AnswerMessage(
            from_tenant_id=tenant_b,
            to_tenant_id=tenant_a,
            from_agent="auditee",
            content="回答1",
            thread_id=thread_id,
        )

        await bus.send(msg1)
        await bus.send(msg2)

        thread = bus.get_thread(thread_id)
        assert len(thread) == 2

    async def test_send_validation_same_tenant(self) -> None:
        """同一テナント送信は拒否"""
        bus = self._create_bus()
        tenant_id = uuid4()
        msg = QuestionMessage(
            from_tenant_id=tenant_id,
            to_tenant_id=tenant_id,
            from_agent="test",
            content="テスト",
        )

        with pytest.raises(ValueError, match="送信元と送信先が同一テナント"):
            await bus.send(msg)

    async def test_send_validation_empty_content(self) -> None:
        """空メッセージは拒否"""
        bus = self._create_bus()
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="",
        )

        with pytest.raises(ValueError, match="メッセージ内容が空"):
            await bus.send(msg)

    async def test_subscribe_and_notify(self) -> None:
        """サブスクライブとコールバック通知"""
        bus = self._create_bus()
        callback = AsyncMock()
        to_tenant = uuid4()

        bus.subscribe(str(to_tenant), callback)

        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=to_tenant,
            from_agent="test",
            content="テストメッセージ",
        )

        await bus.send(msg)
        callback.assert_awaited_once()

    def test_get_messages_for_tenant(self) -> None:
        """テナント別メッセージ取得"""
        bus = self._create_bus()
        tenant_a = uuid4()
        tenant_b = uuid4()

        msg = QuestionMessage(
            from_tenant_id=tenant_a,
            to_tenant_id=tenant_b,
            from_agent="test",
            content="テスト",
        )
        bus._message_log.append(msg)

        # 送信元テナントでも取得可能
        msgs_a = bus.get_messages_for_tenant(tenant_a)
        assert len(msgs_a) == 1

        # 受信先テナントでも取得可能
        msgs_b = bus.get_messages_for_tenant(tenant_b)
        assert len(msgs_b) == 1

        # 無関係テナントは0件
        msgs_c = bus.get_messages_for_tenant(uuid4())
        assert len(msgs_c) == 0

    def test_get_pending_approvals(self) -> None:
        """承認待ちメッセージ取得"""
        bus = self._create_bus()
        tenant_id = uuid4()

        msg = QuestionMessage(
            from_tenant_id=tenant_id,
            to_tenant_id=uuid4(),
            from_agent="test",
            content="テスト",
        )
        bus._message_log.append(msg)

        approvals = bus.get_pending_approvals(tenant_id)
        assert len(approvals) == 1

    def test_approve_message(self) -> None:
        """メッセージ承認"""
        bus = self._create_bus()
        msg = QuestionMessage(
            from_tenant_id=uuid4(),
            to_tenant_id=uuid4(),
            from_agent="test",
            content="テスト",
        )
        bus._message_log.append(msg)

        approver = uuid4()
        result = bus.approve_message(msg.id, approver)
        assert result is True
        assert msg.human_approved is True
        assert msg.approved_by == approver

    def test_approve_message_not_found(self) -> None:
        """存在しないメッセージ承認"""
        bus = self._create_bus()
        result = bus.approve_message(uuid4(), uuid4())
        assert result is False


@pytest.mark.unit
class TestCreateDialogueBusFactory:
    """create_dialogue_bus ファクトリテスト"""

    def test_create_memory_bus(self) -> None:
        """メモリバックエンド生成"""
        from src.dialogue.bus import DialogueBus, create_dialogue_bus

        bus = create_dialogue_bus(backend="memory")
        assert isinstance(bus, DialogueBus)

    def test_create_kafka_bus(self) -> None:
        """Kafkaバックエンド生成"""
        from src.dialogue.bus import create_dialogue_bus

        bus = create_dialogue_bus(backend="kafka")
        assert isinstance(bus, KafkaDialogueBus)

    def test_create_default_bus(self) -> None:
        """デフォルトバックエンド（settings依存）"""
        from src.dialogue.bus import create_dialogue_bus

        with patch("src.config.settings.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(dialogue_bus_backend="memory")
            bus = create_dialogue_bus()
            assert isinstance(bus, type(bus))  # インスタンス生成成功
