"""構造化ログ _json_formatter のユニットテスト"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.monitoring.logging import _json_formatter, setup_logging


def _make_record(
    message: str = "テストメッセージ",
    level_name: str = "INFO",
    module: str = "test_module",
    function: str = "test_func",
    line: int = 42,
    extra: dict[str, Any] | None = None,
    exception: Any = None,
) -> dict[str, Any]:
    """テスト用ログレコード辞書を生成するヘルパー"""
    time_mock = MagicMock()
    time_mock.isoformat.return_value = "2026-02-22T12:00:00+00:00"

    level_mock = MagicMock()
    level_mock.name = level_name

    return {
        "time": time_mock,
        "level": level_mock,
        "message": message,
        "module": module,
        "function": function,
        "line": line,
        "extra": extra or {},
        "exception": exception,
    }


@pytest.mark.unit
class TestJsonFormatter:
    """_json_formatter 関数のテスト"""

    def test_basic_fields_present(self) -> None:
        """基本フィールドがJSONに含まれている"""
        import orjson

        record = _make_record(message="hello", level_name="DEBUG")
        result = _json_formatter(record)

        parsed = orjson.loads(result.strip())
        assert parsed["message"] == "hello"
        assert parsed["level"] == "DEBUG"
        assert parsed["module"] == "test_module"
        assert parsed["function"] == "test_func"
        assert parsed["line"] == 42
        assert "timestamp" in parsed
        assert "correlation_id" in parsed
        assert "tenant_id" in parsed

    def test_output_ends_with_newline(self) -> None:
        """出力が改行で終わる"""
        record = _make_record()
        result = _json_formatter(record)
        assert result.endswith("\n")

    def test_extra_fields_included(self) -> None:
        """extra フィールドがログエントリに追加される"""
        import orjson

        record = _make_record(extra={"request_id": "req-999", "user": "alice"})
        result = _json_formatter(record)

        parsed = orjson.loads(result.strip())
        assert parsed["request_id"] == "req-999"
        assert parsed["user"] == "alice"

    def test_extra_correlation_id_excluded(self) -> None:
        """extra の correlation_id / tenant_id はスキップされる（重複防止）"""
        import orjson

        record = _make_record(extra={"correlation_id": "SHOULD_SKIP", "tenant_id": "SHOULD_SKIP"})
        result = _json_formatter(record)

        # correlation_id は context var から取得されるので extra の値で上書きされない
        parsed = orjson.loads(result.strip())
        # フィールドは存在するが extra 由来ではない（空文字かデフォルト値）
        assert parsed["correlation_id"] != "SHOULD_SKIP"
        assert parsed["tenant_id"] != "SHOULD_SKIP"

    def test_no_exception_field_when_none(self) -> None:
        """例外なしの場合 exception フィールドは含まれない"""
        import orjson

        record = _make_record(exception=None)
        result = _json_formatter(record)
        parsed = orjson.loads(result.strip())
        assert "exception" not in parsed

    def test_exception_field_when_present(self) -> None:
        """例外がある場合 exception フィールドが含まれる"""
        import orjson

        exc_mock = MagicMock()
        exc_mock.type = ValueError
        exc_mock.value = ValueError("エラー発生")

        record = _make_record(exception=exc_mock)
        result = _json_formatter(record)
        parsed = orjson.loads(result.strip())

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert "エラー発生" in parsed["exception"]["value"]

    def test_exception_with_none_type_and_value(self) -> None:
        """例外オブジェクトが存在するが type/value が None の場合"""
        import orjson

        exc_mock = MagicMock()
        exc_mock.type = None
        exc_mock.value = None

        record = _make_record(exception=exc_mock)
        result = _json_formatter(record)
        parsed = orjson.loads(result.strip())

        assert "exception" in parsed
        assert parsed["exception"]["type"] is None
        assert parsed["exception"]["value"] is None

    def test_context_vars_reflected(self) -> None:
        """correlation_id_var / tenant_id_var の値がログに反映される"""
        import orjson

        from src.monitoring.logging import correlation_id_var, tenant_id_var

        corr_token = correlation_id_var.set("corr-abc")
        ten_token = tenant_id_var.set("ten-xyz")
        try:
            record = _make_record()
            result = _json_formatter(record)
            parsed = orjson.loads(result.strip())
            assert parsed["correlation_id"] == "corr-abc"
            assert parsed["tenant_id"] == "ten-xyz"
        finally:
            correlation_id_var.reset(corr_token)
            tenant_id_var.reset(ten_token)

    def test_empty_extra_dict(self) -> None:
        """extra が空辞書の場合でも正常動作する"""
        import orjson

        record = _make_record(extra={})
        result = _json_formatter(record)
        parsed = orjson.loads(result.strip())
        assert parsed["message"] == "テストメッセージ"


@pytest.mark.unit
class TestSetupLoggingExtra:
    """setup_logging 未カバー分岐のテスト"""

    def test_setup_logging_json_false_runs_without_error(self) -> None:
        """json_output=False の開発モードが例外なく完了する"""
        # ファイルハンドラ追加を patch して実際のファイルシステムに書かない
        with patch("src.monitoring.logging.logger") as mock_logger:
            mock_logger.remove = MagicMock()
            mock_logger.add = MagicMock()
            mock_logger.info = MagicMock()
            setup_logging(level="DEBUG", json_output=False)
            # remove が呼ばれ、add が2回呼ばれる（stdout + ファイル）
            mock_logger.remove.assert_called_once()
            assert mock_logger.add.call_count == 2

    def test_setup_logging_json_true_runs_without_error(self) -> None:
        """json_output=True の本番モードが例外なく完了する"""
        with patch("src.monitoring.logging.logger") as mock_logger:
            mock_logger.remove = MagicMock()
            mock_logger.add = MagicMock()
            mock_logger.info = MagicMock()
            setup_logging(level="INFO", json_output=True)
            mock_logger.remove.assert_called_once()
            assert mock_logger.add.call_count == 2

    def test_setup_logging_custom_level(self) -> None:
        """カスタムログレベルで add が正しく呼ばれる"""
        with patch("src.monitoring.logging.logger") as mock_logger:
            mock_logger.remove = MagicMock()
            mock_logger.add = MagicMock()
            mock_logger.info = MagicMock()
            setup_logging(level="WARNING", json_output=True)
            # add 呼び出しに level="WARNING" が含まれているか確認
            calls = mock_logger.add.call_args_list
            assert any(call.kwargs.get("level") == "WARNING" for call in calls)
