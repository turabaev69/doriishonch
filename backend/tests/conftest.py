import os
import tempfile

import pytest

# Testlar alohida vaqtinchalik bazada, AI oʻchirilgan holda ishlaydi.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["PHARMACY_REGION"] = ""
os.environ["ML_DIR"] = f"{_tmp}/ml"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.ml import risk_model  # noqa: E402

# Xavf modeli oldindan (kichik simulyatsiyada) oʻqitiladi — server fonda oʻqitishni boshlamaydi
risk_model.train(n_synth=6000)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, username: str, password: str) -> dict:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="session")
def admin(client):
    """Admin tokeni bilan client (xodimlar endpointlari uchun)."""
    headers = login(client, "admin", "admin123")
    with TestClient(app, headers=headers) as c:
        yield c


def find_id(client, name: str) -> int:
    r = client.get("/search", params={"q": name})
    return next(d["id"] for d in r.json()["results"] if d["trade_name"] == name)
