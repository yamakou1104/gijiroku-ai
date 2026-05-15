import os
import pytest
from utils.crypto import ensure_key, encrypt_and_write, read_and_decrypt


@pytest.fixture
def env_with_key(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("GIJIROKU_ENCRYPTION_KEY", key)
    return key


def test_encrypt_decrypt_roundtrip(env_with_key, tmp_path):
    path = str(tmp_path / "token.json")
    original = '{"access_token": "secret123", "refresh_token": "refresh456"}'
    encrypt_and_write(path, original)
    result = read_and_decrypt(path)
    assert result == original


def test_encrypted_file_not_plaintext(env_with_key, tmp_path):
    path = str(tmp_path / "token.json")
    original = '{"access_token": "secret123"}'
    encrypt_and_write(path, original)
    with open(path, "rb") as f:
        raw = f.read()
    assert b"secret123" not in raw


def test_file_permissions(env_with_key, tmp_path):
    path = str(tmp_path / "token.json")
    encrypt_and_write(path, "test data")
    stat = os.stat(path)
    assert oct(stat.st_mode)[-3:] == "600"


def test_migrate_plaintext_to_encrypted(env_with_key, tmp_path):
    path = str(tmp_path / "token.json")
    plaintext = '{"token": "old_plaintext"}'
    with open(path, "w") as f:
        f.write(plaintext)

    result = read_and_decrypt(path)
    assert result == plaintext

    with open(path, "rb") as f:
        raw = f.read()
    assert b"old_plaintext" not in raw


def test_no_key_writes_plaintext(tmp_path, monkeypatch):
    monkeypatch.delenv("GIJIROKU_ENCRYPTION_KEY", raising=False)
    path = str(tmp_path / "token.json")
    original = '{"token": "value"}'
    encrypt_and_write(path, original)
    result = read_and_decrypt(path)
    assert result == original


def test_ensure_key_generates_key(tmp_path, monkeypatch):
    monkeypatch.delenv("GIJIROKU_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr("utils.resource_path.get_app_data_dir",
                         lambda: str(tmp_path))

    env_path = str(tmp_path / ".env")
    with open(env_path, "w") as f:
        f.write("")

    ensure_key()
    assert os.environ.get("GIJIROKU_ENCRYPTION_KEY")
    assert len(os.environ["GIJIROKU_ENCRYPTION_KEY"]) > 0
