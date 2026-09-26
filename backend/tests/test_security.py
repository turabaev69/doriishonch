"""Production himoyasi: soʻrovlar limiti, sarlavhalar, fayl hajmi, production sozlamalari."""

import pytest

from app.config import settings
from app import security


@pytest.fixture
def limits(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_write_per_min", 3)
    monkeypatch.setattr(settings, "rate_limit_login_per_min", 2)
    security.limiter.hits.clear()
    yield
    security.limiter.hits.clear()


def test_write_rate_limit(client, limits):
    codes = [client.post("/verify", json={"code": "(01)04780000000017(21)X", "mode": "before"}).status_code
             for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]
    r = client.post("/verify", json={"code": "x"})
    assert r.json()["detail"].startswith("Juda koʻp") and r.headers["retry-after"] == "60"
    assert client.get("/health").status_code == 200  # health cheklanmaydi


def test_login_rate_limit(client, limits):
    codes = [client.post("/auth/login", json={"username": "x", "password": "y"}).status_code for _ in range(4)]
    assert codes == [401, 401, 429, 429]


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_upload_size_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    big = b"\xff" * (1024 * 1024 + 10)
    r = client.post("/verify/image", files={"file": ("a.jpg", big, "image/jpeg")})
    assert r.status_code == 413


def test_production_config_check(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        security.check_production_config()
    monkeypatch.setattr(settings, "secret_key", "a" * 64)
    monkeypatch.setattr(settings, "show_demo_accounts", False)
    monkeypatch.setattr(settings, "seed_on_startup", False)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "cors_origins", "https://doriishonch.uz")
    security.check_production_config()  # xatosiz


def test_limits_are_per_client_behind_proxy(client, limits):
    a = {"cf-connecting-ip": "1.1.1.1"}
    b = {"cf-connecting-ip": "2.2.2.2"}
    for _ in range(3):
        assert client.post("/verify", json={"code": "x"}, headers=a).status_code != 429
    assert client.post("/verify", json={"code": "x"}, headers=a).status_code == 429
    assert client.post("/verify", json={"code": "x"}, headers=b).status_code != 429  # boshqa foydalanuvchi
