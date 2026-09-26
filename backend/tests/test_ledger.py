from datetime import datetime, timedelta

from app.db import SessionLocal
from app.models import LedgerBlock
from app.services import codes, ledger, trace

REAL = "0104601234567893" + "21" + "X7Kq2mZp9Lw3T" + "\x1d91AB12\x1d92" + "Q" * 44  # haqiqiy GS1 tuzilma


def test_seeded_chain_is_valid(client):
    r = client.get("/ledger/verify").json()
    assert r["ok"] is True and r["blocks"] > 100


def test_scan_appends_block_linked_to_previous(client):
    before = client.get("/ledger/latest", params={"limit": 1}).json()[0]
    body = client.post("/verify", json={"code": REAL, "device_id": "dev-1"}).json()
    blk = body["ledger"]["block"]
    assert blk["index"] == before["index"] + 1
    assert blk["prev_hash"] == before["hash"]
    assert body["ledger"]["history"][-1]["hash"] == blk["hash"]


def test_crowd_mode_for_unknown_real_code(client):
    code = REAL.replace("X7Kq2mZp9Lw3T", "CROWD00000001")
    body = client.post("/verify", json={"code": code, "device_id": "d"}).json()
    assert body["source"] == "crowd"
    assert body["verdict"] == "ok"
    keys = {c["key"] for c in body["checks"]}
    assert {"first_scan", "gtin_ok", "crypto_present", "official_unavailable"} <= keys
    assert "haqiqiy" not in body["headline"]  # rasmiy tekshirilmagan: haqiqiy deb daʼvo qilmaymiz


def test_bad_gtin_check_digit_warns(client):
    code = REAL.replace("04601234567893", "04601234567890").replace("X7Kq2mZp9Lw3T", "CROWD00000002")
    body = client.post("/verify", json={"code": code}).json()
    assert any(c["key"] == "bad_gtin" for c in body["checks"])


def test_purchase_claim_then_resale_is_danger(client):
    code = REAL.replace("X7Kq2mZp9Lw3T", "CLAIMTEST0001")
    # 1) Xaridor A sotib oldi
    a = client.post("/verify", json={"code": code, "mode": "after", "pharmacy_id": 303, "device_id": "buyer-A"}).json()
    assert a["verdict"] == "ok" and a["ledger"]["block"]["kind"] == "purchase"
    # A oʻzi qayta tekshirsa: muammo yoʻq
    again = client.post("/verify", json={"code": code, "mode": "after", "device_id": "buyer-A"}).json()
    assert again["verdict"] == "ok"
    # 2) Keyinroq B shu qutini dorixonada koʻrdi
    with SessionLocal() as db:
        res = trace.verify(db, raw_code=code, mode="before", pharmacy_id=303, device_id="buyer-B",
                           now=datetime.utcnow() + timedelta(days=10), record=False)
        assert res.verdict == "danger"
        assert any(c.key == "already_claimed" for c in res.checks)
        # 3) B ham "sotib oldim" desa: ikki marta sotilgan quti
        res2 = trace.verify(db, raw_code=code, mode="after", pharmacy_id=303, device_id="buyer-B",
                            now=datetime.utcnow() + timedelta(days=10), record=False)
        assert any(c.key == "double_claim" for c in res2.checks)


def test_same_place_within_two_hours_is_same_buyer(client):
    code = REAL.replace("X7Kq2mZp9Lw3T", "CLAIMTEST0002")
    client.post("/verify", json={"code": code, "mode": "after", "pharmacy_id": 301})
    body = client.post("/verify", json={"code": code, "mode": "after", "pharmacy_id": 301}).json()
    assert body["verdict"] == "ok"


def test_tampering_is_detected(client):
    with SessionLocal() as db:
        b = db.query(LedgerBlock).filter(LedgerBlock.id == 5).one()
        original = b.region
        b.region = "Oʻzgartirilgan"
        db.commit()
        check = ledger.verify_chain(db)
        assert not check.ok and check.broken_at == 5
        b.region = original
        db.commit()
        assert ledger.verify_chain(db).ok


def test_report_is_written_to_chain(client):
    code = REAL.replace("X7Kq2mZp9Lw3T", "REPORTTEST001")
    body = client.post("/verify", json={"code": code}).json()
    client.post("/reports", json={"scan_id": body["scan_id"], "note": "x"})
    hist = client.get("/ledger/code", params={"gtin": "04601234567893", "serial": "REPORTTEST001"}).json()
    assert [h["kind"] for h in hist] == ["scan", "report"]


def test_gtin_check_digit():
    assert trace.gtin_check_digit_ok("04601234567893")
    assert trace.gtin_check_digit_ok("4006381333931")  # EAN-13 misol
    assert not trace.gtin_check_digit_ok("04601234567890")
