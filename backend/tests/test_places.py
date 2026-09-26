import httpx
import pytest

from app.services import places

OSM = {"elements": [
    {"type": "node", "id": 111, "lat": 41.3115, "lon": 69.2795,
     "tags": {"amenity": "pharmacy", "name": "Dori-Darmon 24", "addr:street": "Amir Temur", "addr:housenumber": "5"}},
    {"type": "way", "id": 222, "center": {"lat": 41.3200, "lon": 69.2900}, "tags": {"amenity": "pharmacy"}},
    {"type": "node", "id": 333, "tags": {"amenity": "pharmacy"}},  # koordinatasiz: tashlab yuboriladi
]}


@pytest.fixture
def osm(monkeypatch):
    seen = []

    def handler(req: httpx.Request):
        seen.append(req)
        return httpx.Response(200, json=OSM)

    monkeypatch.setattr(places, "_transport", httpx.MockTransport(handler))
    places._cache.clear()
    return seen


def test_nearby_pharmacies_from_osm(client, osm):
    r = client.get("/pharmacies/nearby", params={"lat": 41.3111, "lon": 69.2797})
    assert r.status_code == 200
    body = r.json()
    assert [b["pharmacy"]["name"] for b in body] == ["Dori-Darmon 24", "Nomsiz dorixona"]
    assert body[0]["distance_m"] < body[1]["distance_m"]
    assert body[0]["pharmacy"]["region"] == "Toshkent" and body[0]["pharmacy"]["is_demo"] is False
    assert b"amenity" in osm[0].content  # Overpass soʻrovi yuborildi


def test_nearby_is_cached_and_upserted(client, osm):
    client.get("/pharmacies/nearby", params={"lat": 41.3111, "lon": 69.2797})
    n1 = len(client.get("/pharmacies").json())
    client.get("/pharmacies/nearby", params={"lat": 41.3111, "lon": 69.2797})
    assert len(osm) == 1  # ikkinchisi keshdan
    assert len(client.get("/pharmacies").json()) == n1  # takror qoʻshilmadi


def test_scan_linked_to_real_pharmacy(client, osm):
    ph = client.get("/pharmacies/nearby", params={"lat": 41.3111, "lon": 69.2797}).json()[0]["pharmacy"]
    code = "0104601234567893" + "21" + "OSMTEST000001"
    body = client.post("/verify", json={"code": code, "pharmacy_id": ph["id"]}).json()
    assert body["ledger"]["block"]["pharmacy"] == "Dori-Darmon 24"


def test_outside_uzbekistan_rejected(client):
    assert client.get("/pharmacies/nearby", params={"lat": 51.5, "lon": -0.1}).status_code == 400


def test_osm_down_gives_502(client, monkeypatch):
    monkeypatch.setattr(places, "_transport", httpx.MockTransport(lambda r: httpx.Response(504)))
    places._cache.clear()
    assert client.get("/pharmacies/nearby", params={"lat": 40.1, "lon": 65.37}).status_code == 502


def test_region_for():
    assert places.region_for(39.65, 66.97) == "Samarqand"
    assert places.region_for(41.30, 69.25) == "Toshkent"
    assert places.region_for(42.46, 59.6) == "Qoraqalpogʻiston"
