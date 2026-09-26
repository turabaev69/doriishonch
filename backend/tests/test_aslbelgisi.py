"""Asl Belgisi xTrace ulagichi: haqiqiy API oʻrniga httpx MockTransport."""

import json
from datetime import datetime, timedelta

import httpx
import pytest

from app.config import settings
from app.services import aslbelgisi, codes

GTIN = "04780000007919"  # Norvadin (demo katalogda bor)
NOW = datetime.utcnow()


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _item(serial, status, history=(), ext=""):
    return {
        "code": f"01{GTIN}21{serial}", "packageType": "UNIT", "status": status, "extendedStatus": ext,
        "issuerShortInfo": {"issuerTin": "300000101", "issuerName": {"uz": "Farm Import Demo MChJ"}},
        "gtin": GTIN, "productSeries": "NO-1", "expirationDate": _iso(NOW + timedelta(days=400)),
        "codeHistory": list(history),
    }


def _ev(etype, days_ago, sender="", receiver="", doc="", status=""):
    return {"eventType": etype, "eventBusinessDate": _iso(NOW - timedelta(days=days_ago)), "senderTin": sender,
            "receiverTin": receiver, "documentType": doc, "eventSourceId": f"DOC-{etype}",
            "eventChangedCodeStatus": status}


REMOTE = {
    "REALSOLD00001": _item("REALSOLD00001", "WITHDRAWN", [
        _ev("IMPORT", 90, receiver="300000101", doc="CUSTOMS_DECLARATION", status="INTRODUCED"),
        _ev("ACCEPTANCE", 80, "300000101", "300000303", doc="INVOICE"),
        _ev("WITHDRAWAL", 30, "300000303", doc="RETAIL_SALE_RECEIPT", status="WITHDRAWN"),
    ]),
    "REALSTOCK0001": _item("REALSTOCK0001", "INTRODUCED", [
        _ev("IMPORT", 60, receiver="300000101", doc="CUSTOMS_DECLARATION", status="INTRODUCED"),
        _ev("ACCEPTANCE", 50, "300000101", "300000301", doc="INVOICE"),
    ]),
    "REALEMIT00001": _item("REALEMIT00001", "UTILIZED"),
    "REALRECALL001": _item("REALRECALL001", "WITHDRAWN", [_ev("WITHDRAWAL", 5, "300000301", doc="DESTRUCTION")],
                           ext="DESTRUCTION"),
}
calls = []


def handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    calls.append((request, body))
    if request.headers.get("authorization") != "Bearer test-key":
        return httpx.Response(401, json={"error": "unauthorized"})
    parsed = codes.parse(body["codes"][0])
    item = REMOTE.get(parsed.serial)
    return httpx.Response(200, json=[item] if item else [])


@pytest.fixture
def remote(monkeypatch):
    monkeypatch.setattr(settings, "asl_belgisi_api_key", "test-key")
    client = aslbelgisi.AslBelgisiClient("https://xtrace.stage.aslbelgisi.uz", "test-key",
                                         transport=httpx.MockTransport(handler))
    monkeypatch.setattr(aslbelgisi, "_client", client)
    calls.clear()
    yield client


def verify(client, serial, mode="before", pharmacy_id=None):
    code = codes.build(GTIN, serial)
    return client.post("/verify", json={"code": code, "mode": mode, "pharmacy_id": pharmacy_id}).json()


def test_request_format(client, remote):
    verify(client, "REALSTOCK0001")
    req, body = calls[-1]
    assert req.url.path == "/public/api/cod/public/codes"
    assert body["addCodeHistory"] is True
    assert "\x1d" in body["codes"][0]  # GS ajratgich JSON da \u001d boʻlib ketadi


def test_remote_sold_box_is_danger(client, remote):
    r = verify(client, "REALSOLD00001", pharmacy_id=303)
    assert r["source"] == "asl_belgisi"
    assert r["verdict"] == "danger"
    check = next(c for c in r["checks"] if c["key"] == "already_sold")
    assert "Bahor Demo Dorixona" in check["text"]  # STIR orqali nomi topildi
    assert [e["type"] for e in r["chain"]][0] == "customs_cleared"
    assert r["chain"][-1]["type"] == "sold"


def test_remote_in_stock_ok_before_and_warning_after(client, remote):
    assert verify(client, "REALSTOCK0001", pharmacy_id=301)["verdict"] == "ok"
    after = verify(client, "REALSTOCK0001", mode="after", pharmacy_id=301)
    assert after["verdict"] == "warning"
    assert any(c["key"] == "sale_not_registered" for c in after["checks"])


def test_remote_other_owner(client, remote):
    r = verify(client, "REALSTOCK0001", pharmacy_id=302)
    assert any(c["key"] == "other_owner" for c in r["checks"])


def test_remote_not_introduced_and_withdrawn(client, remote):
    assert verify(client, "REALEMIT00001")["verdict"] == "warning"
    r = verify(client, "REALRECALL001")
    assert r["verdict"] == "danger" and any(c["key"] == "withdrawn" for c in r["checks"])


def test_remote_unknown_code_is_danger(client, remote):
    r = verify(client, "NOTEXIST00001")
    assert r["verdict"] == "danger" and r["source"] == "asl_belgisi"


def test_demo_codes_stay_local_even_with_key(client, remote):
    r = client.post("/verify", json={"code": codes.build(GTIN, "DEMOREUSE0001"), "pharmacy_id": 303}).json()
    assert r["source"] == "local" and r["verdict"] == "danger"


def test_bad_key_falls_back_to_local(client, monkeypatch):
    monkeypatch.setattr(settings, "asl_belgisi_api_key", "wrong")
    monkeypatch.setattr(aslbelgisi, "_client", aslbelgisi.AslBelgisiClient(
        "https://x", "wrong", transport=httpx.MockTransport(handler)))
    r = verify(client, "REALSTOCK0001")
    assert r["source"] == "local"
    assert any(c["key"] == "remote_unavailable" for c in r["checks"])


def test_health_reports_integrations(client, remote):
    h = client.get("/health").json()
    assert h["asl_belgisi"] is True and h["customs_api"] is False
