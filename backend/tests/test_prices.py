from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.db import SessionLocal
from app.models import ConsumerScan, Participant
from app.services import codes, ledger


@pytest.fixture
def pharmacy(client, monkeypatch):
    monkeypatch.setattr(settings, "pharmacy_region", "Namangan")
    with SessionLocal() as db:
        row = Participant(kind="pharmacy", name="Narx sinovi", region="Namangan", is_demo=False, license_ok=False)
        db.add(row)
        db.commit()
        yield row.id
        db.query(ConsumerScan).filter(ConsumerScan.pharmacy_id == row.id).update({"pharmacy_id": None})
        db.delete(row)
        db.commit()


def new_scan(client, pharmacy, device=None, gtin="04780999999900", serial=None):
    device = device or str(uuid4())
    response = client.post("/verify", json={"code": codes.build(gtin, serial or uuid4().hex[:13]), "device_id": device, "pharmacy_id": pharmacy})
    assert response.status_code == 200
    return response.json()["scan_id"], device


def save(client, scan, amount=25000):
    scan_id, device = scan
    return client.post(f"/verify/{scan_id}/price", json={"device_id": device, "price_paid": amount})


def info(client, scan):
    scan_id, device = scan
    return client.get(f"/verify/{scan_id}/price", headers={"X-Device-Id": device})


def test_price_owned_and_idempotent_without_new_scan_or_points(client, pharmacy):
    scan = new_scan(client, pharmacy)
    with SessionLocal() as db:
        before_count = db.query(ConsumerScan).count()
        before_chain = ledger.verify_chain(db)
    assert info(client, scan).json()["saved_price"] is None
    assert save(client, scan).status_code == 200
    assert save(client, scan).status_code == 200
    assert save(client, scan, 26000).status_code == 409
    assert save(client, (scan[0], str(uuid4()))).status_code == 404
    assert info(client, (scan[0], str(uuid4()))).status_code == 404
    assert client.post(f"/verify/{scan[0]}/price", json={"price_paid": 25000}).status_code == 422
    with SessionLocal() as db:
        assert db.query(ConsumerScan).count() == before_count
        assert db.get(ConsumerScan, scan[0]).price_paid == 25000
        after_chain = ledger.verify_chain(db)
        assert (after_chain.blocks, after_chain.last_hash) == (before_chain.blocks, before_chain.last_hash)


@pytest.mark.parametrize("amount", [0, -1, 100_000_001, 1.5, True, "25000"])
def test_price_validation(client, pharmacy, amount):
    scan = new_scan(client, pharmacy)
    assert save(client, scan, amount).status_code == 422
    assert client.post("/verify", json={"code": "4780999999909", "price_paid": amount}).status_code == 422


def test_comparison_threshold_and_exact_product(client, pharmacy):
    current = new_scan(client, pharmacy)
    for amount in [20000, 30000]:
        assert save(client, new_scan(client, pharmacy), amount).status_code == 200
    assert info(client, current).json()["median_price"] is None
    assert save(client, new_scan(client, pharmacy), 40000).status_code == 200
    data = save(client, current, 36000).json()
    assert data["sample_count"] == 3
    assert data["median_price"] == 30000
    assert data["difference_percent"] == 20
    assert (data["min_price"], data["max_price"]) == (20000, 40000)
    assert data["region"] == "Namangan" and not data["is_demo"]


def test_duplicate_demo_old_outside_and_other_codes_excluded(client, pharmacy):
    current = new_scan(client, pharmacy)
    device = str(uuid4())
    same_box = uuid4().hex[:13]
    assert save(client, new_scan(client, pharmacy, device=device), 10000).status_code == 200
    assert save(client, new_scan(client, pharmacy, device=device, serial=same_box), 20000).status_code == 200
    assert save(client, new_scan(client, pharmacy, serial=same_box), 30000).status_code == 200
    for kind in ["demo", "old", "outside", "other", "anonymous"]:
        with SessionLocal() as db:
            db.add(ConsumerScan(raw_code=codes.build("04780999999900" if kind != "other" else "04780999999893", uuid4().hex[:13]),
                                device_hash=ledger.device_hash(str(uuid4())) if kind != "anonymous" else "",
                                pharmacy_id=pharmacy if kind != "outside" else 301,
                                verdict="ok", price_paid=990000,
                                at=datetime.utcnow() - timedelta(days=100 if kind == "old" else 0),
                                is_demo=kind == "demo"))
            db.commit()
    assert info(client, current).json()["sample_count"] == 1
    assert info(client, current).json()["median_price"] is None


def test_demo_prices_never_compared(client, pharmacy):
    scenario = next(row for row in client.get("/demo/codes").json() if row["key"] == "not_registered_sale")
    device = str(uuid4())
    response = client.post("/verify", json={"code": scenario["code"], "device_id": device}).json()
    result = save(client, (response["scan_id"], device)).json()
    assert result["is_demo"] is True
    assert result["saved_price"] == 25000 and result["sample_count"] == 0


def test_manual_gtin_serial_and_expired_scan(client, pharmacy):
    device = str(uuid4())
    response = client.post("/verify", json={"gtin": "4780999999900", "serial": "PRICE12345678", "device_id": device, "pharmacy_id": pharmacy}).json()
    scan = (response["scan_id"], device)
    assert save(client, scan).status_code == 200
    with SessionLocal() as db:
        row = db.get(ConsumerScan, scan[0])
        row.at = datetime.utcnow() - timedelta(days=8)
        db.commit()
    assert save(client, scan).status_code == 422


def test_invalid_code_does_not_accept_price(client, pharmacy):
    scan = new_scan(client, pharmacy, gtin="04780999999909")
    assert save(client, scan).status_code == 422


def test_image_scan_accepts_price(client, pharmacy, monkeypatch):
    from app.services import ai

    monkeypatch.setattr(ai, "decode_datamatrix", lambda image: codes.build("04780999999900", uuid4().hex[:13]))
    device = str(uuid4())
    response = client.post("/verify/image", data={"device_id": device, "pharmacy_id": pharmacy}, files={"file": ("box.jpg", b"test", "image/jpeg")})
    assert response.status_code == 200
    assert save(client, (response.json()["scan_id"], device)).status_code == 200
