"""
Bundle encryption — Fernet symmetric encryption for sync payloads.

Uses the Connection's shared key to derive a Fernet key.
Cheap, fast, and standard (AES-128-CBC with HMAC-SHA256).

For large payloads: encrypt to a file, return path + file-specific key.
"""

import base64
import hashlib
import json
import os
import time
from pathlib import Path

from cryptography.fernet import Fernet


# Max payload size before writing to file (bytes of JSON)
LARGE_PAYLOAD_THRESHOLD = 64 * 1024  # 64 KB

# Where encrypted payload files are stored
PAYLOAD_DIR = Path.home() / "webclerk_sync" / "payloads"


def _derive_fernet_key(shared_key: str) -> bytes:
    """Derive a Fernet key from the connection's shared key."""
    digest = hashlib.sha256(shared_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_payload(payload: dict, shared_key: str) -> dict:
    """Encrypt a payload dict. Returns either inline or file reference.

    Small payloads: {"encrypted": "<base64>", "inline": true}
    Large payloads: {"file_path": "<path>", "file_key": "<key>", "inline": false}
    """
    raw = json.dumps(payload, separators=(",", ":")).encode()
    fernet_key = _derive_fernet_key(shared_key)
    f = Fernet(fernet_key)

    if len(raw) <= LARGE_PAYLOAD_THRESHOLD:
        token = f.encrypt(raw)
        return {"encrypted": token.decode(), "inline": True}

    # Large payload — write to encrypted file with its own key
    file_key_bytes = Fernet.generate_key()
    file_fernet = Fernet(file_key_bytes)
    encrypted_data = file_fernet.encrypt(raw)

    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"bundle_{int(time.time() * 1000)}_{os.urandom(4).hex()}.enc"
    file_path = PAYLOAD_DIR / filename
    file_path.write_bytes(encrypted_data)

    # Encrypt the file key with the connection key so only the recipient can read it
    encrypted_file_key = f.encrypt(file_key_bytes)

    return {
        "file_path": str(file_path),
        "file_key": encrypted_file_key.decode(),
        "inline": False,
    }


def decrypt_payload(envelope: dict, shared_key: str) -> dict:
    """Decrypt a payload envelope back to the original dict."""
    fernet_key = _derive_fernet_key(shared_key)
    f = Fernet(fernet_key)

    if envelope.get("inline", True):
        raw = f.decrypt(envelope["encrypted"].encode())
        return json.loads(raw)

    # Large payload — decrypt the file key, then decrypt the file
    file_key_bytes = f.decrypt(envelope["file_key"].encode())
    file_fernet = Fernet(file_key_bytes)

    file_path = Path(envelope["file_path"])
    if not file_path.exists():
        raise FileNotFoundError(f"Encrypted payload file not found: {file_path}")

    encrypted_data = file_path.read_bytes()
    raw = file_fernet.decrypt(encrypted_data)
    return json.loads(raw)
