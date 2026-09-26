"""Bojxona integratsiyasi.

Bojxonadan oʻtgan har bir dori partiyasi tizimga kiritiladi va tekshiriladi:
  - tovar tavsifi dori reestriga moslanadi (GTIN → rapidfuzz → Claude);
  - importyor litsenziyasi, kelib chiqish mamlakati, markirovka soni tekshiriladi;
  - deklaratsiyadagi seriya raqamlari qutilar sifatida roʻyxatga olinadi
    ("Bojxonadan rasmiylashtirildi" hodisasi bilan).

Haqiqiy bojxona tizimiga ulanish uchun HttpCustomsSource ishlatiladi (CUSTOMS_API_URL).
Rasmiy API ga kirish Bojxona qoʻmitasi bilan kelishuvni talab qiladi; hozircha DemoCustomsSource
seed/customs_feed.json dan yangi deklaratsiyalarni "keltiradi".
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

import httpx
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from ..config import settings
from ..models import CustomsDeclaration, CustomsLine, Drug, Pack, PackEvent, Participant
from . import ai
from .catalog import find_by_gtin, normalize

FEED = Path(__file__).resolve().parent.parent.parent / "seed" / "customs_feed.json"
FUZZY_ACCEPT = 85

# Deklaratsiyalar odatda xalqaro (inglizcha) nomlar bilan yoziladi
INN_ALIASES = {
    "amlodipin": "amlodipine", "metformin": "metformin", "losartan": "losartan", "atorvastatin": "atorvastatin",
    "bisoprolol": "bisoprolol", "enalapril": "enalapril", "omeprazol": "omeprazole",
    "amoksitsillin": "amoxicillin", "paratsetamol": "paracetamol", "levotiroksin": "levothyroxine",
    "tramadol": "tramadol",
}
FORM_ALIASES = {"tabletka": "tablets tab", "kapsula": "capsules caps"}
FUZZY_CANDIDATE = 50


# ---------------------------------------------------------------- manbalar (adapterlar)

class CustomsSource(Protocol):
    name: str

    def fetch(self, known_numbers: set[str]) -> list[dict]: ...


class DemoCustomsSource:
    name = "demo"

    def fetch(self, known_numbers: set[str]) -> list[dict]:
        items = json.loads(FEED.read_text(encoding="utf-8"))
        return [d for d in items if d["number"] not in known_numbers][:1]  # har safar bittadan


class HttpCustomsSource:
    """Haqiqiy integratsiya uchun shablon. Kutilgan format: DemoCustomsSource bilan bir xil JSON."""

    name = "http"

    def fetch(self, known_numbers: set[str]) -> list[dict]:
        r = httpx.get(f"{settings.customs_api_url.rstrip('/')}/declarations",
                      headers={"Authorization": f"Bearer {settings.customs_api_token}"}, timeout=30)
        r.raise_for_status()
        return [d for d in r.json() if d["number"] not in known_numbers]


def get_source() -> CustomsSource:
    return HttpCustomsSource() if settings.customs_api_url else DemoCustomsSource()


# ---------------------------------------------------------------- moslash va tekshirish

def _tokens(text: str) -> list[str]:
    t = normalize(text)
    t = re.sub(r"(\d)([a-z])", r"\1 \2", t)  # "20mg" → "20 mg"
    return re.findall(r"[a-z0-9]+", t.replace("'", ""))


def _has(tokens: list[str], word: str, threshold: int = 90) -> bool:
    return any(fuzz.ratio(tok, word) >= threshold for tok in tokens if len(tok) >= 3)


def _score(desc: list[str], d: Drug) -> int:
    """Tushuntiriladigan moslik bali: modda 50 + doza 25 + shakl 10 + ishlab chiqaruvchi/brend 15."""
    inn = normalize(d.inn)
    if not (_has(desc, inn) or _has(desc, INN_ALIASES.get(inn, inn))):
        return 0
    score = 50
    number, *unit = d.strength.split()
    for i, tok in enumerate(desc[:-1]):
        if tok == number and (not unit or desc[i + 1] == normalize(unit[0])):
            score += 25
            break
    forms = [normalize(d.form), *FORM_ALIASES.get(normalize(d.form), "").split()]
    if any(f and f in desc for f in forms):
        score += 10
    brand_words = {normalize(d.trade_name), normalize(d.manufacturer.name).split()[0]}
    if any(_has(desc, w, 85) for w in brand_words):
        score += 15
    return score


def match_line(db: Session, description: str, gtin: str) -> tuple[Drug | None, str, str]:
    """(dori, usul, izoh). Usul: gtin, fuzzy, ai, none."""
    if gtin:
        d = find_by_gtin(db, gtin)
        if d:
            return d, "gtin", ""
        return None, "none", f"GTIN {gtin} reestrda yoʻq"
    desc = _tokens(description)
    scored = []
    for d in db.query(Drug).all():
        score = _score(desc, d)
        if score:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    if scored and scored[0][0] >= FUZZY_ACCEPT and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 10):
        return scored[0][1], "fuzzy", f"modda, doza va shakl mos ({scored[0][0]}/100)"
    candidates = [d for s, d in scored if s >= FUZZY_CANDIDATE][:6]
    did, reason = ai.match_customs_line_ai(description, candidates)
    if did:
        return db.get(Drug, did), "ai", reason
    return None, "none", "reestrdagi dori bilan ishonchli moslanmadi"


def validate_line(line: CustomsLine) -> list[str]:
    flags = []
    decl = line.declaration
    d = line.matched_drug
    if line.match_method in ("fuzzy", "ai"):
        how = "AI" if line.match_method == "ai" else "matn oʻxshashligi"
        flags.append(f"GTIN koʻrsatilmagan: reestrga tavsif boʻyicha moslandi ({how}), tasdiqlash kerak")
    if not d:
        flags.append("Reestrda topilmadi: roʻyxatdan oʻtmagan dori importi boʻlishi mumkin")
    else:
        if d.manufacturer.is_local:
            flags.append("Mahalliy ishlab chiqaruvchining dorisi import sifatida rasmiylashtirilgan")
        elif normalize(d.manufacturer.country) != normalize(decl.origin_country):
            flags.append(f"Kelib chiqish mamlakati ({decl.origin_country}) ishlab chiqaruvchi mamlakatiga "
                         f"({d.manufacturer.country}) mos emas")
        if d.dispense_category == "controlled":
            flags.append("Nazoratdagi modda: maxsus import ruxsatnomasi tekshirilishi kerak")
    if decl.importer and not decl.importer.license_ok:
        flags.append(f"Importyor ({decl.importer.name}) litsenziyasi amalda emas")
    if line.quantity and line.registered_packs < line.quantity:
        flags.append(f"Markirovka: deklaratsiyada {line.quantity} quti, tizimda {line.registered_packs} ta "
                     "seriya roʻyxatga olingan")
    return flags


def revalidate_all(db: Session) -> None:
    db.flush()
    db.expire_all()
    for line in db.query(CustomsLine).all():
        line.flags = "|".join(validate_line(line))
    db.commit()


def ingest(db: Session, data: dict, source: str = "api") -> CustomsDeclaration:
    """Deklaratsiyani qabul qiladi, qatorlarni moslaydi, seriyalarni roʻyxatga oladi va tekshiradi."""
    if db.query(CustomsDeclaration).filter(CustomsDeclaration.number == data["number"]).first():
        raise ValueError(f"Deklaratsiya {data['number']} allaqachon mavjud")
    importer = db.query(Participant).filter(Participant.tin == data["importer_tin"]).first()
    if not importer:
        importer = Participant(kind="importer", name=data.get("importer_name") or f"STIR {data['importer_tin']}",
                               tin=data["importer_tin"], region=data.get("importer_region", ""),
                               license_ok=bool(data.get("importer_license_ok", False)), is_demo=source == "demo")
        db.add(importer)
        db.flush()
    cleared = datetime.fromisoformat(data["cleared_at"]) if data.get("cleared_at") else datetime.utcnow()
    decl = CustomsDeclaration(number=data["number"], cleared_at=cleared, customs_post=data.get("customs_post", ""),
                              importer_id=importer.id, origin_country=data.get("origin_country", ""),
                              source=source, is_demo=source == "demo")
    db.add(decl)
    db.flush()
    for ld in data.get("lines", []):
        drug, method, note = match_line(db, ld.get("description", ""), ld.get("gtin", ""))
        line = CustomsLine(declaration=decl, description=ld.get("description", ""),
                           gtin=(drug.gtin if drug else ld.get("gtin", "")), batch=ld.get("batch", ""),
                           quantity=int(ld.get("quantity", 0)), matched_drug_id=drug.id if drug else None,
                           match_method=method)
        db.add(line)
        db.flush()
        registered = 0
        if drug:
            expiry = (datetime.fromisoformat(ld["expiry"]).date() if ld.get("expiry")
                      else (cleared + timedelta(days=730)).date())
            for s in ld.get("serials", []):
                serial, key = (s.get("serial"), s.get("key91", "")) if isinstance(s, dict) else (s, "")
                if db.query(Pack).filter(Pack.serial == serial, Pack.gtin == drug.gtin).first():
                    continue
                p = Pack(drug_id=drug.id, gtin=drug.gtin, serial=serial, crypto_tail=key, batch=line.batch,
                         expiry=expiry, status="imported", owner_id=importer.id, customs_line_id=line.id,
                         is_demo=source == "demo")
                db.add(p)
                db.flush()
                db.add(PackEvent(pack_id=p.id, type="customs_cleared", participant_id=importer.id, at=cleared,
                                 document=decl.number))
                registered += 1
        line.registered_packs = registered
        db.flush()
        db.refresh(line)
        line.flags = "|".join(validate_line(line))
    db.commit()
    return decl


def sync(db: Session) -> list[CustomsDeclaration]:
    src = get_source()
    known = {n for (n,) in db.query(CustomsDeclaration.number).all()}
    return [ingest(db, d, source=src.name) for d in src.fetch(known)]
