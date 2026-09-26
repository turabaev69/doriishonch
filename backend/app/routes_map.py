"""Xarita: dorixonalar (demo + foydalanuvchilar tanlagan OSM dorixonalari) va hududlar.

Ommaviy xaritada dorixona hech qachon "xavfli" deb belgilanmaydi — faqat neytral maʼlumot:
tekshiruvlar soni, oxirgi tekshiruv, missiya (ball) bor-yoʻqligi. Xavf darajasi faqat inspektor uchun.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import require_role
from .config import settings
from .db import get_db
from .models import ConsumerScan, CrowdProduct, Participant
from .regions import REGIONS, region_key
from .services import coverage, rewards, risk

router = APIRouter(prefix="/map")


def _pharmacies(db: Session):
    return coverage.pharmacies(db.query(Participant)
            .filter(Participant.kind == "pharmacy", Participant.lat.isnot(None), Participant.lon.isnot(None))) \
            .order_by(Participant.is_demo, Participant.region, Participant.name).all()


def _p(p: Participant) -> dict:
    return {"id": p.id, "name": p.name, "region": p.region, "region_key": region_key(p.region), "address": p.address,
            "lat": p.lat, "lon": p.lon, "license_ok": p.license_ok, "is_demo": p.is_demo}


@router.get("/pharmacies")
def map_pharmacies(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    since = now - timedelta(days=30)
    stats = dict(db.query(ConsumerScan.pharmacy_id, func.count(ConsumerScan.id))
                 .filter(ConsumerScan.at >= since, ConsumerScan.pharmacy_id.isnot(None))
                 .group_by(ConsumerScan.pharmacy_id).all())
    last = dict(db.query(ConsumerScan.pharmacy_id, func.max(ConsumerScan.at))
                .filter(ConsumerScan.pharmacy_id.isnot(None)).group_by(ConsumerScan.pharmacy_id).all())
    try:
        mission = {m["pharmacy_id"]: m["points"] for m in rewards.missions(db, now)}
    except Exception:  # noqa: BLE001 — missiyasiz ham xarita ishlaydi
        mission = {}
    rows = [{**_p(p), "checks_30d": stats.get(p.id, 0),
             "last_check": last[p.id].isoformat() if last.get(p.id) else None,
             "mission_points": mission.get(p.id)} for p in _pharmacies(db)]
    return {"center": coverage.center(), "pharmacies": rows}


@router.get("/regions")
def map_regions(db: Session = Depends(get_db)):
    """Hududlar boʻyicha: dorixonalar va oxirgi 30 kundagi tekshiruvlar soni."""
    since = datetime.utcnow() - timedelta(days=30)
    ph = db.query(Participant.region, func.count(Participant.id)).filter(Participant.kind == "pharmacy") \
        .group_by(Participant.region).all()
    sc = db.query(ConsumerScan.region, func.count(ConsumerScan.id)).filter(ConsumerScan.at >= since) \
        .group_by(ConsumerScan.region).all()
    by_ph, by_sc = {}, {}
    for name, n in ph:
        k = region_key(name)
        if k:
            by_ph[k] = by_ph.get(k, 0) + n
    for name, n in sc:
        k = region_key(name or "")
        if k:
            by_sc[k] = by_sc.get(k, 0) + n
    return [{**{k: r[k] for k in ("key", "name", "center", "lat", "lon")},
             "pharmacies": by_ph.get(r["key"], 0), "checks_30d": by_sc.get(r["key"], 0)} for r in REGIONS if coverage.in_scope(r["name"])]


@router.get("/inspector", dependencies=[Depends(require_role("inspector"))])
def map_inspector(db: Session = Depends(get_db)):
    """Inspektor xaritasi: dorixonalar xavf darajasi bilan (signal, isbot emas)."""
    levels = {r.pharmacy.id: (r.level, r.signals) for r in risk.compute(db)}
    return [{**_p(p), "level": levels.get(p.id, ("past", []))[0], "signals": levels.get(p.id, ("past", []))[1][:3]}
            for p in _pharmacies(db)]


# ---------------------------------------------------------------- xaridorlar qoʻshgan mahsulotlar

class ProductName(BaseModel):
    name: str = Field(min_length=2, max_length=80)


def _product(p: CrowdProduct) -> dict:
    return {"gtin": p.gtin, "name": p.name, "scans": p.scans, "first_seen": p.first_seen.isoformat(),
            "last_seen": p.last_seen.isoformat(), "lat": p.last_lat, "lon": p.last_lon, "region": p.last_region,
            "pharmacy": p.last_pharmacy.name if p.last_pharmacy else "", "gtin_valid": p.gtin_valid}


@router.get("/products")
def crowd_products(limit: int = 200, db: Session = Depends(get_db)):
    """Reestrda yoʻq, xaridorlar skanerlagan mahsulotlar (xaritada binafsha nuqtalar)."""
    query = db.query(CrowdProduct)
    if settings.pharmacy_region:
        query = query.filter(func.lower(func.trim(CrowdProduct.last_region)).in_(coverage.NAMANGAN_NAMES))
    rows = query.order_by(CrowdProduct.last_seen.desc()).limit(min(limit, 500)).all()
    return [_product(p) for p in rows]


@router.post("/products/{gtin}/name")
def name_product(gtin: str, body: ProductName, db: Session = Depends(get_db)):
    """Xaridor mahsulot nomini yozadi (qutidagi nom). Birinchi yozilgan nom saqlanadi, inspektor tuzatadi."""
    p = db.query(CrowdProduct).filter(CrowdProduct.gtin == gtin.zfill(14)).first()
    if not p:
        raise HTTPException(404, "Mahsulot topilmadi")
    name = re.sub(r"[<>{}\\[\\]]", "", body.name).strip()
    if not p.name:
        p.name = name[:80]
        db.commit()
    return _product(p)


@router.get("/scans")
def scan_points(days: int = 30, db: Session = Depends(get_db)):
    """Soʻnggi tekshiruvlar joyi (xaritadagi kichik nuqtalar). Natija rangi yoʻq — faqat faollik."""
    since = datetime.utcnow() - timedelta(days=min(days, 90))
    query = (db.query(ConsumerScan.lat, ConsumerScan.lon, Participant.lat, Participant.lon)
            .outerjoin(Participant, Participant.id == ConsumerScan.pharmacy_id)
            .filter(ConsumerScan.at >= since))
    if settings.pharmacy_region:
        query = query.filter(func.lower(func.trim(ConsumerScan.region)).in_(coverage.NAMANGAN_NAMES))
    rows = query.limit(2000).all()
    pts = [{"lat": a if a is not None else c, "lon": b if b is not None else d}
           for a, b, c, d in rows if (a is not None or c is not None)]
    return pts
