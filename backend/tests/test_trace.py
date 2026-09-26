from datetime import timedelta

import pytest

from app.db import SessionLocal
from app.services import codes, trace


# ---------------------------------------------------------------- GS1 parser

def test_parse_gs_separated():
    raw = codes.build("04780000007919", "ABCDEFGHIJ123", key91="EE07", crypto92="x" * 44)
    p = codes.parse(raw)
    assert (p.gtin, p.serial, p.key91) == ("04780000007919", "ABCDEFGHIJ123", "EE07")
    assert p.crypto92 == "x" * 44


def test_parse_with_symbology_prefix_expiry_and_batch():
    from datetime import date
    raw = "]d2" + codes.build("04780000007919", "SER0000000001", expiry=date(2027, 5, 31), batch="LOT-7")
    p = codes.parse(raw)
    assert p.serial == "SER0000000001"
    assert p.batch == "LOT-7"
    assert p.expiry == date(2027, 5, 31)


def test_parse_parentheses_form():
    p = codes.parse("(01)04780000007919(21)SER0000000001(91)EE07")
    assert (p.gtin, p.serial, p.key91) == ("04780000007919", "SER0000000001", "EE07")


def test_parse_without_separators_uses_13_char_serial():
    p = codes.parse("0104780000007919" + "21SER0000000001" + "91EE07")
    assert p.serial == "SER0000000001"
    assert p.key91 == "EE07"


def test_parse_plain_barcode():
    p = codes.parse("4780000007919")
    assert p.gtin == "04780000007919" and not p.serial


# ---------------------------------------------------------------- stsenariylar

@pytest.fixture(scope="module")
def demo(client):
    return {d["key"]: d for d in client.get("/demo/codes").json()}


@pytest.mark.parametrize("key", [
    "ok", "reused", "fake", "unregistered", "clone", "grey_import", "recall", "controlled",
    "not_registered_sale", "diverted", "expired", "bad_key", "claimed",
])
def test_demo_scenarios_give_expected_verdict(client, demo, key):
    d = demo[key]
    r = client.post("/verify", json={"code": d["code"], "mode": d["mode"], "pharmacy_id": d["pharmacy_id"]})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == d["expected"], (key, body["headline"], body["checks"])
    assert body["explanation"]
    assert body["scan_id"]


def test_reused_box_shows_where_it_was_sold(client, demo):
    d = demo["reused"]
    body = client.post("/verify", json={"code": d["code"], "mode": "before", "pharmacy_id": 302}).json()
    check = next(c for c in body["checks"] if c["key"] == "already_sold")
    assert "Samarqand" in check["text"] and "47 kun oldin" in check["text"]
    assert [e["type"] for e in body["chain"]][-1] == "sold"
    assert any("sotib olmang" in a for a in body["advice"])


def test_import_chain_starts_with_customs(client, demo):
    body = client.post("/verify", json={"code": demo["reused"]["code"]}).json()
    assert body["chain"][0]["type"] == "customs_cleared"
    assert any(c["key"] == "customs" for c in body["checks"])


def test_controlled_drug_dispense_note(client, demo):
    body = client.post("/verify", json={"code": demo["controlled"]["code"], "pharmacy_id": 301}).json()
    assert body["dispense"]["category"] == "controlled"
    assert "QR retsept" in body["dispense"]["note"]


def test_manual_gtin_serial_entry(client):
    body = client.post("/verify", json={"gtin": "04780000237570", "serial": "DEMOOK0000001"}).json()
    # Tumatirox GTIN + boshqa dorining seriyasi → tizimda yoʻq
    assert body["verdict"] == "danger"


def test_barcode_only_asks_for_datamatrix(client):
    body = client.post("/verify", json={"code": "04780000237570"}).json()
    assert any(c["key"] == "no_serial" for c in body["checks"])


def test_unreadable_code(client):
    body = client.post("/verify", json={"code": "salom"}).json()
    assert body["verdict"] == "unknown"


def test_verify_requires_input(client):
    assert client.post("/verify", json={}).status_code == 400


def test_after_purchase_recent_sale_is_ok():
    with SessionLocal() as db:
        pack = trace.load_pack(db, "04780000007919", "DEMOREUSE0001")
        sold = next(e for e in pack.events if e.type == "sold")
        res = trace.verify(db, gtin=pack.gtin, serial=pack.serial, mode="after",
                           pharmacy_id=sold.participant_id, now=sold.at + timedelta(minutes=30), record=False)
        assert res.verdict == "ok"
        assert any(c.key == "sale_registered" for c in res.checks)


def test_before_mode_just_sold_is_warning_not_danger():
    with SessionLocal() as db:
        pack = trace.load_pack(db, "04780000007919", "DEMOREUSE0001")
        sold = next(e for e in pack.events if e.type == "sold")
        res = trace.verify(db, gtin=pack.gtin, serial=pack.serial, mode="before",
                           now=sold.at + timedelta(minutes=30), record=False)
        assert res.verdict == "warning"


def test_report_marks_scan_and_shows_in_alerts(client, admin, demo):
    body = client.post("/verify", json={"code": demo["fake"]["code"], "pharmacy_id": 301}).json()
    r = client.post("/reports", json={"scan_id": body["scan_id"], "note": "Sotuvchi chek bermadi"})
    assert r.status_code == 200
    alerts = admin.get("/inspector/alerts").json()
    assert alerts[0]["reported"] is True and alerts[0]["report_note"] == "Sotuvchi chek bermadi"
    assert client.post("/reports", json={"scan_id": 999999}).status_code == 404


def test_verify_image_without_key_gives_clear_error(client):
    r = client.post("/verify/image", files={"file": ("a.jpg", b"notanimage", "image/jpeg")})
    assert r.status_code == 422
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]


# ---------------------------------------------------------------- inspektor

def test_inspector_flags_bad_pharmacy_first(client, admin):
    rows = admin.get("/inspector/pharmacies").json()
    assert rows[0]["pharmacy"]["name"] == "Bahor Demo Dorixona"
    assert rows[0]["level"] == "yuqori"
    assert rows[0]["reuse"] >= 3
    assert any(r["level"] == "past" for r in rows)


def test_inspector_detail_summary(client, admin):
    rows = admin.get("/inspector/pharmacies").json()
    detail = admin.get(f"/inspector/pharmacies/{rows[0]['pharmacy']['id']}").json()
    assert detail["summary"] and detail["signals"]
    assert admin.get("/inspector/pharmacies/1").status_code == 404


# ---------------------------------------------------------------- bojxona

def test_seeded_declarations_have_flags(client, admin):
    decls = admin.get("/customs/declarations").json()
    flags = [f for d in decls for l in d["lines"] for f in l["flags"]]
    assert any("litsenziyasi amalda emas" in f for f in flags)
    assert any("Reestrda topilmadi" in f for f in flags)
    assert any("mos emas" in f for f in flags)
    fuzzy = [l for d in decls for l in d["lines"] if l["match_method"] == "fuzzy"]
    assert fuzzy and fuzzy[0]["drug"]["inn"] == "Metformin"


def test_ingest_registers_serials_and_then_verifiable(client, admin):
    payload = {
        "number": "TEST/0001", "cleared_at": "2026-09-20T09:00:00", "customs_post": "Test post",
        "importer_tin": "300000101", "origin_country": "Germaniya",
        "lines": [{"description": "ATORVASTATIN 20MG TABLETS N30", "gtin": "04780000095028", "batch": "T-1",
                   "quantity": 2, "serials": ["TESTSERIAL001", {"serial": "TESTSERIAL002", "key91": "AB12"}]}],
    }
    r = admin.post("/customs/declarations", json=payload)
    assert r.status_code == 200, r.text
    line = r.json()["lines"][0]
    assert line["registered_packs"] == 2 and line["flags"] == []
    body = client.post("/verify", json={"gtin": "04780000095028", "serial": "TESTSERIAL001"}).json()
    assert body["chain"][0]["type"] == "customs_cleared"
    assert admin.post("/customs/declarations", json=payload).status_code == 409


def test_ingest_fuzzy_match_without_gtin(client, admin):
    payload = {"number": "TEST/0002", "importer_tin": "300000102", "origin_country": "Hindiston",
               "lines": [{"description": "OMEPRAZOLE 20MG CAPSULES N20 GANGA", "batch": "X", "quantity": 1}]}
    line = admin.post("/customs/declarations", json=payload).json()["lines"][0]
    assert line["match_method"] == "fuzzy"
    assert line["drug"]["trade_name"] == "Omeganga"


def test_ingest_unknown_importer_is_flagged(client, admin):
    payload = {"number": "TEST/0003", "importer_tin": "999999999", "origin_country": "Germaniya",
               "lines": [{"description": "x", "gtin": "04780000007919", "quantity": 0}]}
    line = admin.post("/customs/declarations", json=payload).json()["lines"][0]
    assert any("litsenziyasi" in f for f in line["flags"])


def test_customs_sync_pulls_new_declaration(client, admin):
    first = admin.post("/customs/sync").json()
    assert len(first) == 1 and first[0]["lines"][0]["registered_packs"] == 6
    second = admin.post("/customs/sync").json()
    assert len(second) == 1
    assert admin.post("/customs/sync").json() == []
