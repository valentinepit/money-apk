import time

import pytest
from jose import jwt as jose_jwt

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_and_verify_roundtrip():
    hashed = hash_password("s3cret!")
    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token(subject="user-123")
    payload = decode_access_token(token)
    assert payload.subject == "user-123"


def test_decode_rejects_tampered_token():
    token = create_access_token(subject="user-123")
    header, payload, signature = token.split(".")
    # Портим сам payload (не последний символ подписи — там могут быть
    # незначащие биты base64url, из-за которых подмена иногда не меняет
    # декодированные байты подписи и тест был бы флейки).
    tampered_payload = ("a" if payload[0] != "a" else "b") + payload[1:]
    tampered = f"{header}.{tampered_payload}.{signature}"

    with pytest.raises(Exception):
        decode_access_token(tampered)


def test_decode_rejects_expired_token(monkeypatch):
    from app import security

    token = create_access_token(subject="user-123", expires_minutes=-1)

    with pytest.raises(Exception):
        decode_access_token(token)
