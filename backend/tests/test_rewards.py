"""Ballar, missiyalar, bounty va firibgarlikka qarshi qoidalar."""

import itertools
import uuid

import pytest

from app.db import SessionLocal
from app.models import Pack, Participant
from app.seed_trace import scenario_codes
from app.services import codes, rewards, trace

from conftest import login

_used: set[int] = set()


def fresh_packs(n: int, status: str = "at_pharmacy"):
    """Hali boshqa testlarda ishlatilmagan, toza (ok) va missiya boʻlmagan dorixonadagi qutilar."""
    with SessionLocal() as db:
        mission_ph = set(rewards._picked(db, __import__("datetime").datetime.utcnow()))
        scenario = {x["serial"] for x in scenario_codes()}  # demo stsenariy qutilariga tegmaymiz
        rows = (db.query(Pack).join(Participant, Pack.owner_id == Participant.id)
                .filter(Pack.status == status, Participant.kind == "pharmacy").order_by(Pack.id.desc()).all())
        out = []
        for p in rows:
            if p.id in _used or not p.drug.price_uzs or p.owner_id in mission_ph or p.serial in scenario:
                continue
            code = codes.build(p.gtin, p.serial, expiry=p.expiry, batch=p.batch, key91=p.crypto_tail or "EE07")
            if trace.verify(db, raw_code=code, pharmacy_id=p.owner_id, record=False).verdict != "ok":
                continue
            _used.add(p.id)
            out.append({"code": code,
                        "pharmacy_id": p.owner_id, "gtin": p.gtin, "serial": p.serial, "price": p.drug.price_uzs,
                        "batch": p.batch})
            if len(out) == n:
                return out
    raise AssertionError("demo qutilar yetmadi")


def dev():
    return f"test-{uuid.uuid4()}"


def verify(client, code, device, mode="before", pharmacy_id=None, **kw):
    r = client.post("/verify", json={"code": code, "mode": mode, "device_id": device, "pharmacy_id": pharmacy_id, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def me(client, device):
    return client.get("/rewards/me", params={"device_id": device}).json()


def test_scan_and_purchase_points(client):
    d = dev()
    box = fresh_packs(1)[0]
    r = verify(client, box["code"], d, pharmacy_id=box["pharmacy_id"])
    assert r["reward"]["earned"] == 15, r["reward"]  # +10 skaner, +5 dorixona
    again = verify(client, box["code"], d, pharmacy_id=box["pharmacy_id"])
    assert again["reward"]["earned"] == 0  # bitta quti — bir marta
    buy = verify(client, box["code"], d, mode="after", pharmacy_id=box["pharmacy_id"])
    assert buy["reward"]["earned"] >= 20
    s = me(client, d)
    assert s["points"] == s["lifetime"] >= 35
    assert any(b["key"] == "buyer" and b["earned"] for b in s["badges"])
    # boshqa qurilma shu qutini "sotib oldim" desa — xarid balli yoʻq
    other = verify(client, box["code"], dev(), mode="after", pharmacy_id=box["pharmacy_id"])
    assert not any("xarid" in m for m in other["reward"]["messages"])


def test_no_device_no_reward(client):
    box = fresh_packs(1)[0]
    r = client.post("/verify", json={"code": box["code"], "mode": "before"}).json()
    assert r["reward"] is None


def test_box_device_limit(client):
    box = fresh_packs(1)[0]
    earned = [verify(client, box["code"], dev())["reward"]["earned"] for _ in range(4)]
    assert earned[:3] == [10, 10, 10] and earned[3] == 0


def test_daily_cap(client):
    d = dev()
    total = 0
    for box in fresh_packs(12):
        r = verify(client, box["code"], d, pharmacy_id=box["pharmacy_id"])
        total += r["reward"]["earned"]
    assert total == rewards.DAILY_CAP
    assert any("chegara" in m for m in r["reward"]["messages"])
    assert me(client, d)["today"]["earned"] == rewards.DAILY_CAP


def test_velocity_flag(client, monkeypatch):
    monkeypatch.setattr(rewards, "VELOCITY_LIMIT", 2)
    d = dev()
    boxes = fresh_packs(4)
    for b in boxes[:3]:
        verify(client, b["code"], d)
    r = verify(client, boxes[3]["code"], d)
    assert r["reward"]["earned"] == 0 and "gʻayrioddiy" in r["reward"]["messages"][0]
    assert me(client, d)["flagged"]
    assert d not in [x["name"] for x in client.get("/rewards/leaderboard").json()]


def test_fake_catch_is_pending_until_inspector_confirms(client):
    d = dev()
    code = "(01)04780000000017(21)FAKE" + uuid.uuid4().hex[:8].upper()
    r = verify(client, code, d)
    if r["verdict"] != "danger":  # GTIN reestrda boʻlmasa, crowd rejim — boshqa roʻyxatdagi GTIN bilan
        box = fresh_packs(1)[0]
        code = f"(01){box['gtin']}(21)FAKE{uuid.uuid4().hex[:8].upper()}"
        r = verify(client, code, d)
    assert r["verdict"] == "danger"
    assert r["reward"]["pending"] == 50 and r["reward"]["earned"] == 0
    rep = client.post("/reports", json={"scan_id": r["scan_id"], "note": "test", "reason": "fake"}).json()
    assert rep["pending_points"] == 20 and "+100" in rep["message"]
    s = me(client, d)
    assert s["pending"] == 70 and s["points"] == 0
    # xaridor inspektor endpointini chaqira olmaydi
    assert client.post(f"/inspector/reports/{r['scan_id']}/resolve", json={"confirmed": True}).status_code == 401
    insp = login(client, "inspektor", "inspektor123")
    res = client.post(f"/inspector/reports/{r['scan_id']}/resolve", json={"confirmed": True}, headers=insp).json()
    assert res["status"] == "tasdiqlandi" and res["credited"] == 170
    s = me(client, d)
    assert s["points"] == 170 and s["pending"] == 0
    assert any(b["key"] == "guardian" and b["earned"] for b in s["badges"])
    alerts = client.get("/inspector/alerts", headers=insp).json()
    a = next(x for x in alerts if x["scan_id"] == r["scan_id"])
    assert a["report_reason"] == "Qalbaki deb gumon" and a["report_status"] == "tasdiqlandi"


def test_rejected_report_gets_nothing(client):
    d = dev()
    box = fresh_packs(1)[0]
    r = verify(client, f"(01){box['gtin']}(21)NOPE{uuid.uuid4().hex[:8].upper()}", d)
    client.post("/reports", json={"scan_id": r["scan_id"], "reason": "fake"})
    insp = login(client, "inspektor", "inspektor123")
    res = client.post(f"/inspector/reports/{r['scan_id']}/resolve", json={"confirmed": False}, headers=insp).json()
    assert res["credited"] == 0 and me(client, d)["points"] == 0


def test_missions(client):
    d = dev()
    ms = client.get("/missions", params={"device_id": d}).json()
    assert 1 <= len(ms) <= rewards.MISSION_COUNT
    m = ms[0]
    assert "xavfli" not in (m["title"] + m["why"]).lower()  # dorixona ommaga "xavfli" deb koʻrsatilmaydi
    with SessionLocal() as db:
        scenario = {x["serial"] for x in scenario_codes()}
        pack = (db.query(Pack).filter(Pack.status == "at_pharmacy", Pack.id.notin_(_used),
                                      Pack.serial.notin_(scenario)).first())
        _used.add(pack.id)
        code = codes.build(pack.gtin, pack.serial, expiry=pack.expiry, batch=pack.batch, key91=pack.crypto_tail or "EE07")
    r = verify(client, code, d, pharmacy_id=m["pharmacy_id"])
    assert any("missiya" in x for x in r["reward"]["messages"])
    assert next(x for x in client.get("/missions", params={"device_id": d}).json() if x["id"] == m["id"])["done"]


def test_nickname_leaderboard_redeem(client):
    d = dev()
    assert client.post("/rewards/nickname", json={"device_id": d, "nickname": "x"}).status_code == 400
    assert client.post("/rewards/nickname", json={"device_id": d, "nickname": "Admin_1"}).status_code == 400
    assert client.post("/rewards/nickname", json={"device_id": d, "nickname": "Dilnoza_T"}).status_code == 400  # band
    assert client.post("/rewards/nickname", json={"device_id": d, "nickname": "Test Posbon"}).json()["nickname"] == "Test Posbon"
    assert client.post("/rewards/redeem", json={"device_id": d, "reward_key": "bp_check"}).status_code == 400
    for box in fresh_packs(7):
        verify(client, box["code"], d, pharmacy_id=box["pharmacy_id"])
    s = me(client, d)
    assert s["points"] >= 100 and s["nickname"] == "Test Posbon" and s["rank"]
    board = client.get("/rewards/leaderboard", params={"device_id": d}).json()
    assert any(r["me"] and r["name"] == "Test Posbon" for r in board)
    assert any(r["name"] == "Dilnoza_T" for r in board)  # demo hamyonlar
    red = client.post("/rewards/redeem", json={"device_id": d, "reward_key": "bp_check"}).json()
    assert red["code"].startswith("DI-")
    s2 = me(client, d)
    assert s2["points"] == s["points"] - 100 and s2["lifetime"] == s["lifetime"]
    assert s2["redemptions"][0]["code"] == red["code"]
    cat = client.get("/rewards/catalog").json()
    assert cat["daily_cap"] == rewards.DAILY_CAP and len(cat["items"]) >= 3


def test_price_too_low_signal(client):
    box = fresh_packs(1)[0]
    r = verify(client, box["code"], dev(), mode="after", pharmacy_id=box["pharmacy_id"], price_paid=box["price"] // 3)
    assert any(c["key"] == "price_too_low" for c in r["checks"])
    assert r["verdict"] in ("warning", "danger")
    ok = verify(client, fresh_packs(1)[0]["code"], dev(), mode="after", price_paid=None)
    assert not any(c["key"] == "price_too_low" for c in ok["checks"])


def test_batch_signals_from_no_effect_reports(client):
    boxes = fresh_packs(40)
    by_batch = {}
    for b in boxes:
        by_batch.setdefault(b["batch"], []).append(b)
    same = next(v for v in by_batch.values() if len(v) >= 2)[:2]
    for b in same:
        r = verify(client, b["code"], dev(), mode="after", pharmacy_id=b["pharmacy_id"])
        client.post("/reports", json={"scan_id": r["scan_id"], "reason": "no_effect", "note": "taʼsir qilmadi"})
    insp = login(client, "inspektor", "inspektor123")
    sig = client.get("/inspector/batch-signals", headers=insp).json()
    row = next(x for x in sig if x["batch"] == same[0]["batch"])
    assert row["quality_reports"] >= 2 and row["level"] in ("oʻrta", "yuqori")
    assert client.get("/inspector/batch-signals").status_code == 401


def test_rewards_require_device(client):
    assert client.get("/rewards/me", params={"device_id": ""}).status_code == 400
