"""暗号化サービス テスト"""

import pytest

from src.security.encryption import EncryptionService, HashChain


@pytest.mark.unit
class TestEncryptionService:
    """暗号化サービスのユニットテスト"""

    def test_encrypt_decrypt_string(self) -> None:
        """文字列の暗号化・復号テスト"""
        service = EncryptionService(key="test-key-for-encryption-testing!!")
        plaintext = "機密データ：売上¥1,000,000"

        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert encrypted != plaintext
        assert decrypted == plaintext

    def test_encrypt_decrypt_bytes(self) -> None:
        """バイト列の暗号化・復号テスト"""
        service = EncryptionService(key="test-key-for-encryption-testing!!")
        data = b"binary evidence data"

        encrypted = service.encrypt_bytes(data)
        decrypted = service.decrypt_bytes(encrypted)

        assert encrypted != data
        assert decrypted == data

    def test_compute_hash(self) -> None:
        """ハッシュ計算テスト"""
        data = b"test data for hashing"
        hash_value = EncryptionService.compute_hash(data)

        assert len(hash_value) == 64  # SHA-256
        # 同じデータは同じハッシュ
        assert EncryptionService.compute_hash(data) == hash_value

    def test_generate_key(self) -> None:
        """キー生成テスト"""
        key = EncryptionService.generate_key()
        assert len(key) == 44  # Fernet key length

    def test_generate_salt(self) -> None:
        """ソルト生成テスト"""
        salt1 = EncryptionService.generate_salt()
        salt2 = EncryptionService.generate_salt()
        assert salt1 != salt2  # 毎回異なる


@pytest.mark.unit
class TestHashChain:
    """ハッシュチェーンのユニットテスト"""

    def test_add_entry(self) -> None:
        """エントリ追加テスト"""
        chain = HashChain()
        hash1 = chain.add_entry({"action": "create", "data": "test1"})
        hash2 = chain.add_entry({"action": "update", "data": "test2"})

        assert hash1 != hash2
        assert len(hash1) == 64

    def test_verify_chain(self) -> None:
        """チェーン検証テスト"""
        chain = HashChain()
        entries = [
            {"action": "create", "data": "entry1"},
            {"action": "update", "data": "entry2"},
            {"action": "delete", "data": "entry3"},
        ]
        hashes = [chain.add_entry(e) for e in entries]

        # 検証
        verifier = HashChain()
        assert verifier.verify_chain(entries, hashes) is True

    def test_detect_tampering(self) -> None:
        """改ざん検出テスト"""
        chain = HashChain()
        entries = [
            {"action": "create", "data": "entry1"},
            {"action": "update", "data": "entry2"},
        ]
        hashes = [chain.add_entry(e) for e in entries]

        # エントリを改ざん
        tampered_entries = entries.copy()
        tampered_entries[0] = {"action": "create", "data": "TAMPERED"}

        verifier = HashChain()
        assert verifier.verify_chain(tampered_entries, hashes) is False
