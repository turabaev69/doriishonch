"""Xarita va hududlar."""


def test_map_pharmacies_cover_all_regions(client):
    body = client.get("/map/pharmacies").json()
    rows = body["pharmacies"]
    assert body["center"]["zoom"] > 0
    assert len(rows) >= 18
    assert all(r["lat"] and r["lon"] and r["region_key"] for r in rows)
    assert len({r["region_key"] for r in rows}) == 14  # har bir hududda kamida bitta dorixona
    assert any(r["checks_30d"] > 0 for r in rows)
    # ommaviy xaritada xavf darajasi yoʻq
    assert all("level" not in r and "signals" not in r for r in rows)


def test_map_has_missions(client):
    rows = client.get("/map/pharmacies").json()["pharmacies"]
    assert any(r["mission_points"] for r in rows)


def test_regions(client):
    regs = client.get("/map/regions").json()
    assert len(regs) == 14
    assert all(r["pharmacies"] >= 1 for r in regs)
    assert sum(r["checks_30d"] for r in regs) > 0


def test_inspector_map_requires_login(client, admin):
    assert client.get("/map/inspector").status_code == 401
    rows = admin.get("/map/inspector").json()
    assert rows and {"level", "signals"} <= set(rows[0])
    assert any(r["level"] in ("yuqori", "oʻrta") for r in rows)


def test_pharmacies_endpoint_returns_coordinates(client):
    rows = client.get("/pharmacies").json()
    assert any(r["lat"] for r in rows)


# ---------------------------------------------------------------- yangi mahsulotlar va joylashuv

def test_ad_qr_code_is_not_a_medicine_code(client):
    body = client.post("/verify", json={"code": "https://t.me/Biolife24_bot"}).json()
    assert body["headline"] == "Bu dori kodi emas"
    assert body["checks"][0]["key"] == "not_medicine_code"
    assert body["scan_id"] is None  # saqlanmaydi


def test_gs1_digital_link_is_parsed(client):
    body = client.post("/verify", json={"code": "https://id.gs1.org/01/04780000007919/21/DEMOFAKE00001"}).json()
    assert body["parsed"]["gtin"] == "04780000007919" and body["parsed"]["serial"] == "DEMOFAKE00001"


def test_unknown_product_is_added_with_location(client):
    ean = "4780123456781"  # reestrda yoʻq mahsulot
    first = client.post("/verify", json={"code": ean, "lat": 41.31123, "lon": 69.27971}).json()
    assert first["new_product"]["is_new"] is True and first["new_product"]["has_location"]
    assert "qoʻshildi" in first["headline"]
    assert first["ai_risk"] is None and "bazamizda hali yoʻq" in first["explanation"]
    second = client.post("/verify", json={"code": ean, "pharmacy_id": 303}).json()
    assert second["new_product"]["is_new"] is False and second["new_product"]["scans"] == 2
    named = client.post(f"/map/products/{ean}/name", json={"name": "Biolife Vitamin C"}).json()
    assert named["name"] == "Biolife Vitamin C"
    rows = client.get("/map/products").json()
    p = next(r for r in rows if r["gtin"] == ean.zfill(14))
    assert p["name"] == "Biolife Vitamin C" and p["scans"] == 2 and p["region"] == "Samarqand"
    assert p["lat"] and p["lon"]


def test_location_is_coarsened_and_scan_points(client):
    body = client.post("/verify", json={"code": "4780123450000", "lat": 41.123456, "lon": 69.654321}).json()
    from app.db import SessionLocal
    from app.models import ConsumerScan

    db = SessionLocal()
    try:
        s = db.get(ConsumerScan, body["scan_id"])
        assert (s.lat, s.lon) == (41.123, 69.654)
    finally:
        db.close()
    pts = client.get("/map/scans").json()
    assert {"lat": 41.123, "lon": 69.654} in pts


def test_outside_uzbekistan_location_ignored(client):
    body = client.post("/verify", json={"code": "4780123450017", "lat": 51.5, "lon": -0.1}).json()
    assert body["new_product"]["has_location"] is False


def test_rescan_after_purchase_shows_where_it_was_sold(client):
    from app.db import SessionLocal
    from app.models import Pack

    db = SessionLocal()
    try:
        pk = db.query(Pack).filter(Pack.status == "at_pharmacy", ~Pack.serial.startswith("DEMO")).order_by(Pack.id).offset(3).first()
        ok = {"code": f"01{pk.gtin}21{pk.serial}"}
    finally:
        db.close()
    a, b = "device-aaaa-1111", "device-bbbb-2222"
    first = client.post("/verify", json={"code": ok["code"], "device_id": a, "lat": 41.30, "lon": 69.24}).json()
    assert first["verdict"] == "ok"
    client.post("/verify", json={"code": ok["code"], "device_id": a, "mode": "after", "lat": 41.30, "lon": 69.24})
    mine = client.post("/verify", json={"code": ok["code"], "device_id": a}).json()
    assert mine["headline"].startswith("Bu quti sizniki")
    assert any(c["key"] == "own_purchase" for c in mine["checks"])
    other = client.post("/verify", json={"code": ok["code"], "device_id": b, "pharmacy_id": 305}).json()
    assert other["verdict"] == "danger" and any(c["key"] == "already_claimed" for c in other["checks"])
    kinds = {p["kind"] for p in other["places"]}
    assert "purchase" in kinds and "scan" in kinds
    buy = next(p for p in other["places"] if p["kind"] == "purchase")
    assert (buy["lat"], buy["lon"]) == (41.3, 69.24)


def test_places_for_barcode_only_product(client):
    ean = "4780123456781"
    client.post("/verify", json={"code": ean, "lat": 40.10, "lon": 65.37})
    body = client.post("/verify", json={"code": ean, "pharmacy_id": 306}).json()
    assert len(body["places"]) >= 2
