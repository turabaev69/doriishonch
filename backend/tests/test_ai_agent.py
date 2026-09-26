"""AI agentlar va qadoq ekspertizasi: haqiqiy Claude oʻrniga skriptli soxta client."""

import json
from types import SimpleNamespace as NS

import pytest

from app.config import settings
from app.services import ai, codes

from conftest import login


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append({**kw, "messages": list(kw.get("messages", []))})
        return self.script.pop(0)


def tool(name, inp, id_="t1"):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def text(t):
    return NS(type="text", text=t)


@pytest.fixture
def fake(monkeypatch):
    def install(script):
        c = FakeClient(script)
        monkeypatch.setattr(settings, "anthropic_api_key", "test")
        monkeypatch.setattr(ai, "_client", c)
        return c
    return install


def test_status_lists_ai_features(client):
    body = client.get("/ai/status").json()
    assert "assistant" in body["features"] and "box_inspection" in body["features"]


def test_assistant_uses_verify_tool(client, fake):
    demo = {d["key"]: d for d in client.get("/demo/codes").json()}
    c = fake([
        NS(stop_reason="tool_use", content=[text("Tekshiraman."), tool("verify_code", {"code": demo["reused"]["code"]})]),
        NS(stop_reason="end_turn", content=[text("Bu quti oldin sotilgan. Sotib olmang.")]),
    ])
    r = client.post("/ai/chat", json={"messages": [{"role": "user", "content": "Shu kodni tekshir: ..."}]}).json()
    assert r["ai_used"] is True
    assert r["answer"].startswith("Bu quti oldin sotilgan")
    assert r["steps"][0]["tool"] == "verify_code" and "danger" in r["steps"][0]["summary"]
    # ikkinchi chaqiruvda tool_result yuborilgan
    tool_result = c.calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and json.loads(tool_result["content"])["verdict"] == "danger"
    assert {t["name"] for t in c.calls[0]["tools"]} >= {"verify_code", "search_drug", "trust_card", "code_history"}


def test_assistant_does_not_write_to_ledger(client, fake):
    before = client.get("/ledger/latest", params={"limit": 1}).json()[0]["index"]
    fake([NS(stop_reason="tool_use", content=[tool("verify_code", {"gtin": "04601234567893", "serial": "AGENTTEST0001"})]),
          NS(stop_reason="end_turn", content=[text("ok")])])
    client.post("/ai/chat", json={"messages": [{"role": "user", "content": "tekshir"}]})
    assert client.get("/ledger/latest", params={"limit": 1}).json()[0]["index"] == before


def test_assistant_blocks_dose_questions_without_calling_ai(client, fake):
    c = fake([])
    r = client.post("/ai/chat", json={"messages": [{"role": "user", "content": "Kuniga necha tabletka ichay?"}]}).json()
    assert r["blocked"] is True and "shifokor" in r["answer"]
    assert c.calls == []


def test_assistant_filters_superlatives(client, fake):
    fake([NS(stop_reason="end_turn", content=[text("Bu eng yaxshi dori. GMP sertifikati bor.")])])
    r = client.post("/ai/chat", json={"messages": [{"role": "user", "content": "Amlozar qanday?"}]}).json()
    assert "eng yaxshi" not in r["answer"].lower()


def test_assistant_fallback_without_key(client):
    r = client.post("/ai/chat", json={"messages": [{"role": "user", "content": "Norvadin"}]}).json()
    assert r["ai_used"] is False and "Norvadin" in r["answer"] and "Mahalliy analoglar" in r["answer"]
    code = codes.build("04780000007919", "DEMOREUSE0001")
    r = client.post("/ai/chat", json={"messages": [{"role": "user", "content": code}]}).json()
    assert "sotib olingan" in r["answer"] or "sotilgan" in r["answer"]


def test_chat_requires_user_last(client):
    assert client.post("/ai/chat", json={"messages": [{"role": "assistant", "content": "x"}]}).status_code == 400


def test_inspector_copilot_requires_login(client):
    r = client.post("/ai/inspector", json={"messages": [{"role": "user", "content": "Kimni tekshiray?"}]})
    assert r.status_code == 401


def test_inspector_copilot_with_tools(client, fake):
    headers = login(client, "inspektor", "inspektor123")
    fake([NS(stop_reason="tool_use", content=[tool("pharmacy_risks", {})]),
          NS(stop_reason="end_turn", content=[text("Birinchi navbatda Bahor Demo Dorixonani tekshirish tavsiya etiladi.")])])
    r = client.post("/ai/inspector", headers=headers,
                    json={"messages": [{"role": "user", "content": "Qaysi dorixonani birinchi tekshiray?"}]}).json()
    assert "Bahor" in r["answer"] and r["steps"][0]["tool"] == "pharmacy_risks"


def test_inspector_copilot_fallback(client):
    headers = login(client, "inspektor", "inspektor123")
    r = client.post("/ai/inspector", headers=headers, json={"messages": [{"role": "user", "content": "?"}]}).json()
    assert r["ai_used"] is False and "Bahor Demo Dorixona" in r["answer"]


def test_box_inspection_compares_printed_data(client, fake):
    demo = {d["key"]: d for d in client.get("/demo/codes").json()}
    obs = {"printed_trade_name": "Norvadin", "printed_batch": "XX-0000", "printed_expiry": "2030-01",
           "tamper_signs": ["Himoya yorligʻi yirtilgan"], "print_issues": [], "image_quality": "yaxshi",
           "summary_uz": "Qutida ochilganlik belgisi bor."}
    fake([NS(stop_reason="end_turn", content=[text(json.dumps(obs, ensure_ascii=False))])])
    r = client.post("/ai/inspect-box", data={"code": demo["reused"]["code"]},
                    files={"file": ("box.jpg", b"img", "image/jpeg")}).json()
    keys = {c["key"]: c["status"] for c in r["checks"]}
    assert r["overall"] == "warning"
    assert keys["tamper"] == "warning" and keys["batch"] == "warning" and keys["name"] == "ok"


def test_box_inspection_needs_key(client):
    r = client.post("/ai/inspect-box", files={"file": ("box.jpg", b"img", "image/jpeg")})
    assert r.status_code == 422


def test_auth_roles(client):
    assert client.get("/inspector/pharmacies").status_code == 401
    customs = login(client, "bojxona", "bojxona123")
    assert client.get("/customs/declarations", headers=customs).status_code == 200
    assert client.get("/inspector/pharmacies", headers=customs).status_code == 403
    maker = login(client, "zarafshon", "zarafshon123")
    assert client.get("/manufacturers/1/insights", headers=maker).status_code == 200
    assert client.get("/manufacturers/2/insights", headers=maker).status_code == 403
    assert client.post("/auth/login", json={"username": "admin", "password": "xato"}).status_code == 401
    assert client.get("/auth/me", headers=customs).json()["role"] == "customs"
    assert client.get("/auth/me", headers={"Authorization": "Bearer buzilgan.token"}).status_code == 401


def test_consumer_endpoints_stay_open(client):
    assert client.post("/verify", json={"code": codes.build("04780000007919", "DEMOOK0000001")}).status_code == 200
    assert client.get("/pharmacies").status_code == 200
    assert client.get("/ledger/verify").status_code == 200
