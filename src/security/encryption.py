"""暗号化ユーティリティ — AES-256-GCM + Fernet"""

import base64
import hashlib
import os
from typing import Any

from cryptography.fernet import Fernet
from loguru import logger

from src.config.settings import get_settings


class EncryptionService:
    """データ暗号化・復号サービス"""

    def __init__(self, key: str | None = None) -> None:
        settings = get_settings()
        encryption_key = key or settings.encryption_key
        if not encryption_key:
            logger.warning("暗号化キー未設定 — 自動生成キーを使用（開発環境のみ）")
            encryption_key = Fernet.generate_key().decode()
        self._fernet = Fernet(self._ensure_valid_key(encryption_key))

    @staticmethod
    def _ensure_valid_key(key: str) -> bytes:
        """Fernet互換の32バイトBase64キーを生成"""
        if len(key) == 44 and key.endswith("="):
            # 既にFernetキー形式
            return key.encode()
        # 任意の文字列からFernetキーを派生
        derived = hashlib.sha256(key.encode()).digest()
        return base64.urlsafe_b64encode(derived)

    def encrypt(self, plaintext: str) -> str:
        """文字列を暗号化してBase64文字列を返す"""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """暗号化文字列を復号"""
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def encrypt_bytes(self, data: bytes) -> bytes:
        """バイト列を暗号化"""
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        """バイト列を復号"""
        return self._fernet.decrypt(data)

    @staticmethod
    def generate_key() -> str:
        """新しいFernet暗号化キーを生成"""
        return Fernet.generate_key().decode()

    @staticmethod
    def compute_hash(data: bytes, algorithm: str = "sha256") -> str:
        """データのハッシュ値を計算（改ざん検出用）"""
        h = hashlib.new(algorithm)
        h.update(data)
        return h.hexdigest()

    @staticmethod
    def generate_salt(length: int = 32) -> str:
        """暗号学的に安全なソルトを生成"""
        return base64.urlsafe_b64encode(os.urandom(length)).decode()


class HashChain:
    """ハッシュチェーン — 監査証跡の改ざん防止

    各エントリのハッシュに前エントリのハッシュを含めることで、
    途中の改ざんを検出可能にする。
    """

    def __init__(self, algorithm: str = "sha256") -> None:
        self._algorithm = algorithm
        self._previous_hash = "0" * 64  # genesis

    def add_entry(self, data: dict[str, Any]) -> str:
        """新しいエントリをチェーンに追加してハッシュを返す"""
        import json

        entry_str = json.dumps(data, sort_keys=True, default=str)
        combined = f"{self._previous_hash}:{entry_str}"
        new_hash = hashlib.new(self._algorithm, combined.encode()).hexdigest()
        self._previous_hash = new_hash
        return new_hash

    def verify_chain(self, entries: list[dict[str, Any]], hashes: list[str]) -> bool:
        """チェーン全体の整合性を検証"""
        import json

        if len(entries) != len(hashes):
            return False

        prev_hash = "0" * 64
        for entry, expected_hash in zip(entries, hashes, strict=False):
            entry_str = json.dumps(entry, sort_keys=True, default=str)
            combined = f"{prev_hash}:{entry_str}"
            computed_hash = hashlib.new(self._algorithm, combined.encode()).hexdigest()
            if computed_hash != expected_hash:
                return False
            prev_hash = computed_hash

        return True
