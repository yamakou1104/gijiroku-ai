import logging
import os
import tempfile

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def ensure_key():
    if os.environ.get("GIJIROKU_ENCRYPTION_KEY"):
        return
    from dotenv import set_key
    from utils.resource_path import get_app_data_dir

    key = Fernet.generate_key()
    env_path = os.path.join(get_app_data_dir(), ".env")
    set_key(env_path, "GIJIROKU_ENCRYPTION_KEY", key.decode())
    os.chmod(env_path, 0o600)
    os.environ["GIJIROKU_ENCRYPTION_KEY"] = key.decode()


def _get_fernet():
    key_str = os.environ.get("GIJIROKU_ENCRYPTION_KEY")
    if not key_str:
        return None
    return Fernet(key_str.encode())


def encrypt_and_write(path, data):
    fernet = _get_fernet()
    if fernet:
        content = fernet.encrypt(data.encode("utf-8"))
    else:
        content = data.encode("utf-8")

    dir_name = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    except BaseException:
        os.unlink(tmp)
        raise


def read_and_decrypt(path):
    with open(path, "rb") as f:
        content = f.read()

    fernet = _get_fernet()
    if fernet:
        try:
            return fernet.decrypt(content).decode("utf-8")
        except InvalidToken:
            plaintext = content.decode("utf-8")
            logger.info("Migrating plaintext token file to encrypted: %s", path)
            encrypt_and_write(path, plaintext)
            return plaintext

    return content.decode("utf-8")
