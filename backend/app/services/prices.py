import re
from datetime import datetime, timedelta
from statistics import median

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models import ConsumerScan, Pack
from . import codes, coverage, ledger, trace

MAX_PRICE = 100_000_000
PERIOD_DAYS = 90
MIN_SAMPLES = 3


def identity(scan: ConsumerScan) -> tuple[str, str]:
    if scan.pack:
        return scan.pack.gtin.zfill(14), scan.pack.serial
    raw = scan.raw_code.strip()
    if re.fullmatch(r"[0-9]{8,14}/[^/]*", raw):
        gtin, serial = raw.split("/", 1)
        return gtin.zfill(14), serial
    parsed = codes.parse(raw)
    return parsed.gtin, parsed.serial


def owned_scan(db: Session, scan_id: int, device_id: str) -> ConsumerScan:
    scan = db.get(ConsumerScan, scan_id)
    device = ledger.device_hash(device_id)
    if not scan or not device or scan.device_hash != device:
        raise HTTPException(404, "Skan topilmadi. Qutini qayta skanerlang.")
    gtin, serial = identity(scan)
    drug = trace.find_by_gtin(db, gtin) if gtin else None
    demo = bool(scan.pack and scan.pack.is_demo) or bool(drug and drug.is_demo)
    if not gtin or not demo and not trace.gtin_check_digit_ok(gtin):
        raise HTTPException(422, "Narx kiritish uchun qutidagi toʻgʻri kod kerak.")
    if scan.pharmacy and not coverage.in_scope(scan.pharmacy.region):
        raise HTTPException(422, "Hozir faqat Namangan dorixonalari bilan ishlaymiz.")
    return scan


def summary(db: Session, scan: ConsumerScan) -> dict:
    gtin, serial = identity(scan)
    drug = trace.find_by_gtin(db, gtin)
    demo = scan.is_demo or bool(scan.pack and scan.pack.is_demo) or bool(drug and drug.is_demo)
    result = {"saved_price": scan.price_paid, "sample_count": 0, "median_price": None,
              "min_price": None, "max_price": None, "difference_percent": None,
              "period_days": PERIOD_DAYS, "is_demo": demo, "region": settings.pharmacy_region}
    if demo:
        return result
    query = (db.query(ConsumerScan).outerjoin(Pack, ConsumerScan.pack_id == Pack.id)
             .options(joinedload(ConsumerScan.pack), joinedload(ConsumerScan.pharmacy))
             .filter(ConsumerScan.price_paid.between(1, MAX_PRICE),
                     ConsumerScan.at >= datetime.utcnow() - timedelta(days=PERIOD_DAYS),
                     ConsumerScan.is_demo.is_(False), ConsumerScan.device_hash != "",
                     ConsumerScan.device_hash != scan.device_hash,
                     or_(Pack.gtin == gtin, ConsumerScan.raw_code.contains(gtin.lstrip("0"))))
             .order_by(ConsumerScan.at.desc(), ConsumerScan.id.desc()))
    seen_devices = set()
    seen_serials = {serial} if serial else set()
    values = []
    for candidate in query.limit(5000):
        if settings.pharmacy_region and (not candidate.pharmacy or not coverage.in_scope(candidate.pharmacy.region)):
            continue
        if candidate.pharmacy and candidate.pharmacy.is_demo:
            continue
        if candidate.pack and candidate.pack.is_demo:
            continue
        candidate_gtin, candidate_serial = identity(candidate)
        if candidate_gtin != gtin or candidate.device_hash in seen_devices:
            continue
        seen_devices.add(candidate.device_hash)
        if candidate_serial and candidate_serial in seen_serials:
            continue
        if candidate_serial:
            seen_serials.add(candidate_serial)
        values.append(candidate.price_paid)
    result["sample_count"] = len(values)
    if len(values) >= MIN_SAMPLES:
        typical = round(median(values))
        result.update(median_price=typical, min_price=min(values), max_price=max(values))
        if scan.price_paid:
            result["difference_percent"] = round((scan.price_paid - typical) / typical * 100, 1)
    return result


def save(db: Session, scan: ConsumerScan, price: int) -> dict:
    if scan.at < datetime.utcnow() - timedelta(days=7):
        raise HTTPException(422, "Bu skan eskirgan. Qutini qayta skanerlang.")
    if scan.price_paid is not None and scan.price_paid != price:
        raise HTTPException(409, "Bu skan uchun narx allaqachon saqlangan.")
    if scan.price_paid is None:
        updated = (db.query(ConsumerScan).filter(ConsumerScan.id == scan.id, ConsumerScan.price_paid.is_(None))
                   .update({ConsumerScan.price_paid: price}, synchronize_session=False))
        db.commit()
        db.refresh(scan)
        if not updated and scan.price_paid != price:
            raise HTTPException(409, "Bu skan uchun narx allaqachon saqlangan.")
    return summary(db, scan)
