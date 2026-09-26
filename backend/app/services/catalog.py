"""Qidiruv, Ishonch kartasi va analoglar.

Muhim: bu yerda hech qanday ball yoki reyting hisoblanmaydi. Faqat tekshiriladigan
faktlar va ularning manbalari qaytariladi.
"""

import re
from datetime import date

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session, joinedload

from ..models import Drug, Manufacturer
from ..schemas import AnalogOut, DrugBrief, Fact, ManufacturerOut, TrustCard

DISCLAIMER = (
    "Bu sahifa rasmiy manbalardagi faktlarni koʻrsatadi va dori tanlash boʻyicha tibbiy maslahat emas. "
    "Dorini almashtirishdan oldin shifokor yoki farmatsevt bilan maslahatlashing."
)

_APOS = re.compile(r"[ʻʼ'`‘’]")


def normalize(text: str) -> str:
    return _APOS.sub("'", text).strip().lower()


def to_brief(d: Drug) -> DrugBrief:
    m: Manufacturer = d.manufacturer
    return DrugBrief(
        id=d.id, trade_name=d.trade_name, inn=d.inn, strength=d.strength, form=d.form,
        atc_group=d.atc_group, price_uzs=d.price_uzs, pack_size=d.pack_size,
        prescription_only=d.prescription_only, is_demo=d.is_demo,
        manufacturer=ManufacturerOut(id=m.id, name=m.name, country=m.country,
                                     is_local=m.is_local, is_demo=m.is_demo),
    )


def _all_drugs(db: Session) -> list[Drug]:
    return db.query(Drug).options(joinedload(Drug.manufacturer)).all()


def get_drug(db: Session, drug_id: int) -> Drug | None:
    return (
        db.query(Drug)
        .options(
            joinedload(Drug.manufacturer).joinedload(Manufacturer.certificates),
            joinedload(Drug.registry_entries),
            joinedload(Drug.quality_alerts),
            joinedload(Drug.evidence_docs),
        )
        .filter(Drug.id == drug_id)
        .first()
    )


def find_by_gtin(db: Session, gtin: str) -> Drug | None:
    g = gtin.lstrip("0")
    for d in _all_drugs(db):
        if d.gtin and d.gtin.lstrip("0") == g:
            return d
    return None


def search(db: Session, q: str, limit: int = 10) -> list[Drug]:
    """Savdo nomi va XNN boʻyicha noaniq (fuzzy) qidiruv. Imlo xatolariga chidamli."""
    q_norm = normalize(q)
    if not q_norm:
        return []
    drugs = _all_drugs(db)
    if q_norm.isdigit() and len(q_norm) >= 8:
        hit = find_by_gtin(db, q_norm)
        return [hit] if hit else []

    choices = {}
    for d in drugs:
        choices[(d.id, "t")] = normalize(d.trade_name)
        choices[(d.id, "i")] = normalize(d.inn)
    scored: dict[int, float] = {}
    for _, score, key in process.extract(q_norm, choices, scorer=fuzz.WRatio, limit=len(choices)):
        if score < 70:
            continue
        drug_id = key[0]
        scored[drug_id] = max(scored.get(drug_id, 0), score)

    by_id = {d.id: d for d in drugs}
    ranked = sorted(scored, key=lambda i: (-scored[i], by_id[i].trade_name))
    return [by_id[i] for i in ranked[:limit]]


def _valid_certs(d: Drug, today: date):
    return [c for c in d.manufacturer.certificates if c.valid_until >= today]


def trust_facts(d: Drug, today: date | None = None) -> list[Fact]:
    today = today or date.today()
    facts: list[Fact] = []

    # 1. Davlat reestri
    active = [r for r in d.registry_entries if r.status == "amalda"]
    if active:
        r = active[0]
        facts.append(Fact(
            key="registry", label="Davlat reestri", status="ok",
            text=f"Oʻzbekistonda roʻyxatdan oʻtgan: № {r.registry_number}, {r.registered_on:%d.%m.%Y} dan, holati: {r.status}.",
            source_url=r.source_url, updated_at=r.updated_at, is_demo=r.is_demo))
    else:
        facts.append(Fact(key="registry", label="Davlat reestri", status="missing",
                          text="Amaldagi roʻyxatdan oʻtish yozuvi bazada topilmadi."))

    # 2. GMP sertifikatlari (ishlab chiqaruvchi darajasida)
    certs = d.manufacturer.certificates
    if not certs:
        facts.append(Fact(key="gmp", label="GMP sertifikati", status="missing",
                          text=f"{d.manufacturer.name} uchun GMP sertifikati bazada topilmadi."))
    for c in certs:
        valid = c.valid_until >= today
        facts.append(Fact(
            key="gmp", label=c.type, status="ok" if valid else "warn",
            text=(f"{d.manufacturer.name}: № {c.number}, {c.valid_until:%d.%m.%Y} gacha amal qiladi."
                  if valid else
                  f"{d.manufacturer.name}: № {c.number} muddati {c.valid_until:%d.%m.%Y} da tugagan."),
            source_url=c.source_url, updated_at=c.updated_at, is_demo=c.is_demo))

    # 3. Sifat nuqsonlari va qalbakilik
    if d.quality_alerts:
        for a in sorted(d.quality_alerts, key=lambda a: a.reported_on, reverse=True):
            facts.append(Fact(
                key="quality_alert", label=a.type, status="warn",
                text=f"Seriya {a.batch}, {a.reported_on:%d.%m.%Y}: {a.description}",
                source_url=a.source_url, updated_at=a.reported_on, is_demo=a.is_demo))
    else:
        facts.append(Fact(key="quality_alert", label="Sifat ogohlantirishlari", status="ok",
                          text="Bazadagi sifat nuqsoni va qalbaki dorilar roʻyxatlarida bu dori boʻyicha yozuv yoʻq."))

    # 4. Raqamli markirovka
    facts.append(Fact(
        key="marking", label="Asl Belgisi markirovkasi", status="ok" if d.has_marking else "missing",
        text=("Qadoqda DataMatrix markirovka kodi bor: haqiqiyligini Asl Belgisi ilovasida tekshirish mumkin."
              if d.has_marking else "Bazada bu dori uchun markirovka maʼlumoti yoʻq."),
        source_url="https://crpt-turon.uz/uz/raqamli-markirovkalash/asl-belgisi-mobil-ilovasi/"))

    # 5. Ekvivalentlik dalillari
    if d.evidence_docs:
        for e in d.evidence_docs:
            facts.append(Fact(
                key="evidence", label=e.type, status="info", text=e.title,
                source_url=e.source_url, updated_at=e.updated_at,
                provided_by_manufacturer=e.provided_by_manufacturer, is_demo=e.is_demo))
    else:
        facts.append(Fact(key="evidence", label="Ekvivalentlik dalillari", status="missing",
                          text="Bioekvivalentlik yoki eritilish testi maʼlumoti bazada yoʻq."))

    # 6. Xavfsizlik eslatmalari
    if d.narrow_therapeutic_index:
        facts.append(Fact(key="nti", label="Tor terapevtik indeks", status="warn",
                          text="Bu dorida kichik farq ham taʼsirni oʻzgartirishi mumkin. Preparatni almashtirish faqat shifokor nazoratida."))
    facts.append(Fact(key="rx", label="Berilish tartibi", status="info",
                      text="Retsept boʻyicha beriladi." if d.prescription_only else "Retseptsiz beriladi."))
    return facts


def trust_card(d: Drug) -> TrustCard:
    return TrustCard(drug=to_brief(d), facts=trust_facts(d), disclaimer=DISCLAIMER)


def analogs(db: Session, base: Drug, today: date | None = None) -> list[AnalogOut]:
    """Faqat XNN, doza va dori shakli toʻliq mos preparatlar. Mahalliylar oldin, keyin narx boʻyicha."""
    today = today or date.today()
    candidates = [
        get_drug(db, d.id) for d in _all_drugs(db)
        if d.id != base.id
        and normalize(d.inn) == normalize(base.inn)
        and normalize(d.strength) == normalize(base.strength)
        and normalize(d.form) == normalize(base.form)
    ]
    out = []
    for d in candidates:
        diff = d.price_uzs - base.price_uzs
        pct = round(diff * 100 / base.price_uzs) if base.price_uzs else 0
        out.append(AnalogOut(
            drug=to_brief(d), price_diff_uzs=diff, price_diff_pct=pct,
            has_valid_gmp=bool(_valid_certs(d, today)),
            quality_alert_count=len(d.quality_alerts), evidence_count=len(d.evidence_docs)))
    out.sort(key=lambda a: (not a.drug.manufacturer.is_local, a.drug.price_uzs))
    return out
