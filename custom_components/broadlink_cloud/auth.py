"""BroadLink Cloud login encoding (unofficial protocol).

The algorithm and constants were adapted from the MIT-licensed
skymike/homebridge-broadlink-cloud project. See LICENSE and README.
"""

from __future__ import annotations

import hashlib
import json
import time

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class BroadlinkAuth:
    """Produce the encrypted login request expected by the EU service."""

    COMPANY_ID = "b0491bc574dfa144908c3cd671f56370"
    LICENSE_ID = "5eda600025ae5057181daaa2124f79b7"
    PASSWORD_SALT = "4969fj#k23#"
    TOKEN_SALT = "xgx3d*fe3478$ukx"
    KEY_SALT = "kdixkdqp54545^#*"
    IV = bytes.fromhex("eaaaaa3abb5862a21918b5771d1615aa")

    @classmethod
    def encrypt_login(cls, email: str, password: str) -> dict[str, str | bytes]:
        """Prepare encrypted payload without persisting plaintext credentials."""

        timestamp = str(int(time.time()))
        pw_hash = hashlib.sha1(
            (password + cls.PASSWORD_SALT).encode("utf-8")
        ).hexdigest()
        payload = {
            "email": email,
            "password": pw_hash,
            "companyid": cls.COMPANY_ID,
            "lid": cls.LICENSE_ID,
        }
        json_payload = json.dumps(
            payload, separators=(",", ":"), ensure_ascii=False
        )
        token = hashlib.md5(
            (json_payload + cls.TOKEN_SALT).encode("utf-8")
        ).hexdigest()
        key = hashlib.md5(
            (timestamp + cls.KEY_SALT).encode("utf-8")
        ).digest()
        data = json_payload.encode("utf-8")
        # Preserve upstream login padding including an extra AES block.
        padding_length = ((len(data) + 15) // 16) * 16 + 16
        padded = data.ljust(padding_length, b"\x00")
        encryptor = Cipher(algorithms.AES(key), modes.CBC(cls.IV)).encryptor()
        encrypted = encryptor.update(padded) + encryptor.finalize()
        return {"timestamp": timestamp, "token": token, "body": encrypted}
