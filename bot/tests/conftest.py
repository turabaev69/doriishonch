"""Bot testlari haqiqiy backend ilovasiga (ASGI orqali, tarmoqsiz) ulanadi."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "bot"), str(ROOT / "backend")]
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/bot-test.db"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ML_DIR"] = f"{_tmp}/ml"

import asyncio  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from core import Brain  # noqa: E402
from app.ml import risk_model  # noqa: E402

risk_model.train(n_synth=6000)


@pytest.fixture(scope="session", autouse=True)
def backend():
    with TestClient(app):  # lifespan: baza va demo maʼlumotlar
        yield


@pytest.fixture
def brain():
    b = Brain(httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test"),
              "https://demo.trycloudflare.com")
    yield b
    asyncio.run(b.http.aclose())


def run(coro):
    return asyncio.run(coro)
