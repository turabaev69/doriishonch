"""CSV fayllardan bazani toʻldirish.

Ishga tushirish: `python -m app.seed` (backend/ papkasidan).
Barcha seed yozuvlar is_demo=True bilan belgilanadi. Haqiqiy maʼlumot qoʻshganda
CSV ga `is_demo` ustunini qoʻshib, 0 qiling.
"""

import csv
import logging
from datetime import date
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, SessionLocal, engine
from .models import Certificate, Drug, EvidenceDoc, Manufacturer, QualityAlert, RegistryEntry, SearchEvent

from .seed_trace import seed_trace

log = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def _rows(name: str):
    with open(SEED_DIR / name, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def _b(v: str) -> bool:
    return str(v).strip() in ("1", "true", "True", "ha")


def _d(v: str) -> date:
    return date.fromisoformat(v)


def _demo(row: dict) -> bool:
    return _b(row.get("is_demo", "1"))


def seed(db: Session) -> None:
    for r in _rows("manufacturers.csv"):
        db.add(Manufacturer(id=int(r["id"]), name=r["name"], country=r["country"],
                            is_local=_b(r["is_local"]), is_demo=_demo(r)))
    db.flush()
    for r in _rows("certificates.csv"):
        db.add(Certificate(manufacturer_id=int(r["manufacturer_id"]), type=r["type"], number=r["number"],
                           valid_until=_d(r["valid_until"]), source_url=r["source_url"],
                           updated_at=_d(r["updated_at"]), is_demo=_demo(r)))
    for r in _rows("drugs.csv"):
        db.add(Drug(id=int(r["id"]), trade_name=r["trade_name"], inn=r["inn"], strength=r["strength"],
                    form=r["form"], atc_group=r["atc_group"], manufacturer_id=int(r["manufacturer_id"]),
                    prescription_only=_b(r["prescription_only"]),
                    narrow_therapeutic_index=_b(r["narrow_therapeutic_index"]),
                    price_uzs=int(r["price_uzs"]), pack_size=r["pack_size"], gtin=r["gtin"],
                    has_marking=_b(r["has_marking"]),
                    dispense_category=r.get("dispense_category") or ("rx" if _b(r["prescription_only"]) else "otc"),
                    is_demo=_demo(r)))
    db.flush()
    for r in _rows("registry_entries.csv"):
        db.add(RegistryEntry(drug_id=int(r["drug_id"]), registry_number=r["registry_number"],
                             registered_on=_d(r["registered_on"]), status=r["status"],
                             source_url=r["source_url"], updated_at=_d(r["updated_at"]), is_demo=_demo(r)))
    for r in _rows("quality_alerts.csv"):
        db.add(QualityAlert(drug_id=int(r["drug_id"]), batch=r["batch"], type=r["type"],
                            reported_on=_d(r["reported_on"]), description=r["description"],
                            source_url=r["source_url"], is_demo=_demo(r)))
    for r in _rows("evidence_docs.csv"):
        db.add(EvidenceDoc(drug_id=int(r["drug_id"]), type=r["type"], title=r["title"],
                           provided_by_manufacturer=_b(r["provided_by_manufacturer"]),
                           source_url=r["source_url"], updated_at=_d(r["updated_at"]), is_demo=_demo(r)))
    db.commit()
    seed_demo_events(db)


def seed_demo_events(db: Session, n: int = 400) -> None:
    """Ishlab chiqaruvchi paneli boʻsh koʻrinmasligi uchun sunʼiy (is_demo) hodisalar."""
    import random
    from datetime import datetime, timedelta

    rnd = random.Random(42)
    drugs = db.query(Drug).all()
    topics = ["sifat"] * 5 + ["ekvivalentlik"] * 4 + ["haqiqiylik"] * 2 + ["narx"] * 2 + ["nojoya", "tibbiy", "boshqa"]
    now = datetime.utcnow()
    for _ in range(n):
        d = rnd.choice(drugs)
        kind = rnd.choice(["view", "view", "view", "question"])
        db.add(SearchEvent(kind=kind, query="", drug_id=d.id,
                           topic=rnd.choice(topics) if kind == "question" else "",
                           is_demo=True, created_at=now - timedelta(days=rnd.randint(0, 29))))
    db.commit()


# Sxema oʻzgarganda oshiriladi. Eski demo baza avtomatik qayta yaratiladi.
SCHEMA_VERSION = "8"


def _schema_outdated(bind) -> bool:
    insp = inspect(bind)
    if "app_meta" not in insp.get_table_names():
        return bool(insp.get_table_names())  # eski versiya: jadvallar bor, meta yoʻq
    with bind.connect() as c:
        row = c.execute(text("SELECT value FROM app_meta WHERE key='schema_version'")).first()
    return not row or row[0] != SCHEMA_VERSION


def init_db(seed_if_empty: bool = True, bind=None, session_factory=SessionLocal) -> None:
    if settings.is_production and seed_if_empty:
        raise RuntimeError("Productionda SEED_ON_STARTUP=false boʻlishi shart; demo seed bloklandi.")
    bind = bind or engine
    if _schema_outdated(bind):
        if settings.is_production or not seed_if_empty:
            raise RuntimeError("Baza sxemasi eskirgan: zaxira nusxa va migratsiya talab qilinadi. Baza oʻzgartirilmadi.")
        log.warning("Baza sxemasi eskirgan: demo baza qayta yaratilmoqda.")
        Base.metadata.drop_all(bind=bind)
        with bind.begin() as c:
            c.execute(text("DROP TABLE IF EXISTS app_meta"))
    Base.metadata.create_all(bind=bind)
    with bind.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS app_meta (key VARCHAR(40) PRIMARY KEY, value VARCHAR(40))"))
        c.execute(text("DELETE FROM app_meta WHERE key='schema_version'"))
        c.execute(text("INSERT INTO app_meta (key, value) VALUES ('schema_version', :v)"), {"v": SCHEMA_VERSION})
    if not seed_if_empty:
        return
    with session_factory() as db:
        if db.query(Drug).count() == 0:
            seed(db)
            seed_trace(db)
        from .auth import seed_users

        seed_users(db)
        from .services.rewards import seed_demo

        seed_demo(db)
        from .ml.learning import backfill

        backfill(db)  # demo skanlarga AI bahosi


if __name__ == "__main__":
    init_db()
    print("Baza tayyor.")
