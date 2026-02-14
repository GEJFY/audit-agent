"""構造化ログ設定 — loguru + JSON形式"""

import sys
from contextvars import ContextVar
from typing import Any

from loguru import logger

# リクエストスコープの相関ID・テナントIDを保持
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")


def _json_formatter(record: dict[str, Any]) -> str:
    """JSON構造化ログフォーマッタ"""
    import orjson

    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "correlation_id": correlation_id_var.get(""),
        "tenant_id": tenant_id_var.get(""),
    }

    # extra フィールドを追加
    if record.get("extra"):
        for key, value in record["extra"].items():
            if key not in ("correlation_id", "tenant_id"):
                log_entry[key] = value

    # 例外情報を追加
    if record["exception"]:
        log_entry["exception"] = {
            "type": record["exception"].type.__name__ if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
        }

    return orjson.dumps(log_entry).decode() + "\n"


def setup_logging(level: str = "INFO", json_output: bool = True) -> None:
    """ログ設定を初期化

    Args:
        level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: JSON形式で出力するか（本番=True, 開発=False）
    """
    # 既存ハンドラを削除
    logger.remove()

    if json_output:
        logger.add(
            sys.stdout,
            format=_json_formatter,
            level=level,
            serialize=False,
        )
    else:
        # 開発用: 読みやすいカラー出力
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "{message}"
            ),
            level=level,
            colorize=True,
        )

    # ファイル出力（ローテーション付き）
    logger.add(
        "logs/audit-agent_{time:YYYY-MM-DD}.log",
        rotation="100 MB",
        retention="30 days",
        compression="gz",
        format=_json_formatter if json_output else "{time} | {level} | {module}:{function}:{line} | {message}",
        level=level,
    )

    logger.info("ログ設定初期化完了", level=level, json_output=json_output)


def get_logger(name: str) -> Any:
    """モジュール名付きloggerを返す"""
    return logger.bind(module_name=name)
