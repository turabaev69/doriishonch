"""Haqiqiy dorixonalar: OpenStreetMap Overpass API (bepul, kalit talab qilinmaydi).

Xaridor "Yaqin dorixonani aniqlash" tugmasini bossa, brauzer joylashuvni beradi, biz esa
atrofdagi dorixonalarni OSM dan olib, ishtirokchilar jadvaliga (is_demo=False) qoʻshamiz.
Shunda skanerlashlar va zanjir yozuvlari haqiqiy dorixonaga bogʻlanadi.

Overpass foydalanish qoidalari: oʻrtacha yuklama, User-Agent koʻrsatish, natijalarni keshlash.
https://wiki.openstreetmap.org/wiki/Overpass_API
"""

import math
import time
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Participant

# Viloyat markazlari (taxminiy) — joylashuvdan viloyatni aniqlash uchun
REGIONS = {
    "Toshkent": (41.311, 69.279),
    "Toshkent viloyati": (40.95, 69.60),
    "Andijon": (40.783, 72.344),
    "Fargʻona": (40.389, 71.783),
    "Namangan": (40.998, 71.672),
    "Samarqand": (39.654, 66.960),
    "Buxoro": (39.768, 64.421),
    "Navoiy": (40.103, 65.374),
    "Qashqadaryo": (38.861, 65.798),
    "Surxondaryo": (37.224, 67.278),
    "Jizzax": (40.116, 67.842),
    "Sirdaryo": (40.490, 68.784),
    "Xorazm": (41.550, 60.631),
    "Qoraqalpogʻiston": (42.460, 59.603),
}
TASHKENT_CITY_KM = 16

_cache: dict[tuple, tuple[float, list[dict]]] = {}
CACHE_SECONDS = 600
_transport: httpx.BaseTransport | None = None  # testlar uchun


class PlacesError(Exception):
    pass


def distance_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def region_for(lat: float, lon: float) -> str:
    if distance_m(lat, lon, *REGIONS["Toshkent"]) <= TASHKENT_CITY_KM * 1000:
        return "Toshkent"
    return min((r for r in REGIONS if r != "Toshkent"), key=lambda r: distance_m(lat, lon, *REGIONS[r]))


@dataclass
class Place:
    osm_id: str
    name: str
    lat: float
    lon: float
    address: str


def _query(lat: float, lon: float, radius: int) -> list[dict]:
    key = (round(lat, 3), round(lon, 3), radius, settings.pharmacy_region)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    q = (f'[out:json][timeout:15];('
         f'node["amenity"="pharmacy"](around:{radius},{lat},{lon});'
         f'way["amenity"="pharmacy"](around:{radius},{lat},{lon}););out center 40;')
    if settings.pharmacy_region:
        q = ('[out:json][timeout:15];area["ISO3166-2"="UZ-NG"]["boundary"="administrative"]->.pilot;'
             f'nwr["amenity"="pharmacy"](area.pilot)(around:{radius},{lat},{lon});out center 40;')
    try:
        with httpx.Client(timeout=20, transport=_transport,
                          headers={"User-Agent": "DoriIshonch/0.3 (hackathon; pharmacy verification)"}) as c:
            r = c.post(settings.overpass_url, data={"data": q})
            if r.status_code == 406:
                r = c.get(settings.overpass_url, params={"data": q})
            r.raise_for_status()
            elements = r.json().get("elements", [])
    except (httpx.HTTPError, ValueError) as e:
        raise PlacesError(f"OpenStreetMap bilan aloqa yoʻq: {e}") from e
    _cache[key] = (time.time(), elements)
    return elements


def _place(el: dict) -> Place | None:
    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lon = el.get("lon") or (el.get("center") or {}).get("lon")
    if lat is None or lon is None:
        return None
    t = el.get("tags") or {}
    name = t.get("name:uz") or t.get("name") or t.get("name:ru") or t.get("brand") or "Nomsiz dorixona"
    addr = ", ".join(filter(None, [t.get("addr:street"), t.get("addr:housenumber")])) or t.get("addr:full", "")
    return Place(osm_id=f"{el.get('type', 'node')}/{el['id']}", name=name, lat=float(lat), lon=float(lon), address=addr)


def nearby(db: Session, lat: float, lon: float, radius: int = 1500) -> list[tuple[Participant, float]]:
    """Atrofdagi dorixonalar (yaqinidan uzoqqa). Har biri ishtirokchilar jadvaliga saqlanadi."""
    places = [p for p in (_place(e) for e in _query(lat, lon, radius)) if p]
    out = []
    for pl in places:
        part = db.query(Participant).filter(Participant.osm_id == pl.osm_id).first()
        if not part:
            part = Participant(kind="pharmacy", name=pl.name, region=settings.pharmacy_region or region_for(pl.lat, pl.lon),
                               address=pl.address, osm_id=pl.osm_id, lat=pl.lat, lon=pl.lon,
                               license_ok=False, is_demo=False)
            db.add(part)
        else:
            part.name, part.address, part.lat, part.lon = pl.name, pl.address or part.address, pl.lat, pl.lon
            if settings.pharmacy_region:
                part.region = settings.pharmacy_region
        out.append((part, distance_m(lat, lon, pl.lat, pl.lon)))
    db.commit()
    out.sort(key=lambda x: x[1])
    return out[:25]
