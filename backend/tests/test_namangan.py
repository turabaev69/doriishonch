import json

import pytest

from app.config import settings
from app.db import SessionLocal
from app.models import ConsumerScan, Participant
from app.services import coverage, places, rewards


@pytest.fixture
def namangan(monkeypatch):
    monkeypatch.setattr(settings, "pharmacy_region", "Namangan")
    rewards._cache.clear()
    yield
    rewards._cache.clear()


def test_namangan_catalog_and_map(client, namangan):
    pharmacies = client.get("/pharmacies").json()
    assert pharmacies and all(coverage.in_scope(row["region"]) for row in pharmacies)
    body = client.get("/map/pharmacies").json()
    assert body["center"] == coverage.NAMANGAN_CENTER
    assert body["pharmacies"] and all(row["region_key"] == "namangan" for row in body["pharmacies"])
    assert [row["key"] for row in client.get("/map/regions").json()] == ["namangan"]
    assert all(coverage.in_scope(row["region"]) for row in client.get("/missions").json())


def test_outside_pharmacy_rejected_before_scan(client, namangan):
    with SessionLocal() as db:
        before = db.query(ConsumerScan).count()
    response = client.post("/verify", json={"code": "4780123456781", "pharmacy_id": 301})
    assert response.status_code == 422
    assert "Namangan" in response.json()["detail"]
    image = client.post("/verify/image", data={"pharmacy_id": "301"}, files={"file": ("box.jpg", b"invalid", "image/jpeg")})
    assert image.status_code == 422 and "Namangan" in image.json()["detail"]
    with SessionLocal() as db:
        assert db.query(ConsumerScan).count() == before


def test_pharmacy_optional_or_in_namangan(client, namangan):
    assert client.post("/verify", json={"code": "4780999999909"}).status_code == 200
    assert client.post("/verify", json={"code": "4780999999909", "pharmacy_id": 309}).status_code == 200
    assert client.post("/verify", json={"code": "4780123456781", "pharmacy_id": 999999}).status_code == 422


def test_nearby_query_restricted_to_namangan(monkeypatch, namangan):
    import httpx

    requests = []
    monkeypatch.setattr(places, "_transport", httpx.MockTransport(lambda request: requests.append(request) or httpx.Response(200, json={"elements": []})))
    places._cache.clear()
    assert places._query(40.9983, 71.6726, 1500) == []
    from urllib.parse import parse_qs

    query = parse_qs(requests[0].content.decode())["data"][0]
    assert '"ISO3166-2"="UZ-NG"' in query and "(area.pilot)(around:" in query


def test_demo_sale_is_explicit_not_cash_register_accusation(client):
    scenarios = client.get("/demo/codes").json()
    scenario = next(row for row in scenarios if row["key"] == "not_registered_sale")
    response = client.post("/verify", json={"code": scenario["code"], "mode": "after"}).json()
    assert response["is_demo"] is True
    check = next(row for row in response["checks"] if row["key"] == "sale_not_registered")
    assert check["title"] == "Sotuv qaydi topilmadi"
    assert "haqiqiy kassa holatini bildirmaydi" in check["text"]
    assert "kassadan oʻtkazilmagan" not in json.dumps(response, ensure_ascii=False)


def test_pilot_demo_links_do_not_select_other_regions(client, namangan):
    rows = client.get("/demo/codes").json()
    assert all(row["pharmacy_id"] in (None, 309) for row in rows)


def test_import_is_idempotent_and_not_license_verification(client, tmp_path, namangan, monkeypatch):
    from scripts.import_namangan import import_snapshot

    snapshot = tmp_path / "namangan.json"
    snapshot.write_text(json.dumps({"osm3s": {"timestamp_osm_base": "2026-09-26T12:15:05Z"}, "elements": [
        {"type": "node", "id": 999000123, "lat": 40.999, "lon": 71.668, "tags": {"amenity": "pharmacy", "name": "Import test dorixonasi"}},
    ]}))
    assert import_snapshot(snapshot) == 1
    assert import_snapshot(snapshot) == 1
    monkeypatch.setattr(places, "_query", lambda *args: pytest.fail("Stored Namangan pharmacies must not require Overpass"))
    with SessionLocal() as db:
        rows = db.query(Participant).filter(Participant.osm_id == "node/999000123").all()
        assert len(rows) == 1 and rows[0].region == "Namangan"
        assert rows[0].is_demo is False and rows[0].license_ok is False
        response = client.get("/pharmacies/nearby", params={"lat": 40.999, "lon": 71.668})
        assert response.status_code == 200
        assert all(row["pharmacy"]["region"] == "Namangan" for row in response.json())
        assert any(row["pharmacy"]["id"] == rows[0].id for row in response.json())
        db.delete(rows[0])
        db.commit()
