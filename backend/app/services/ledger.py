"""DoriIshonch skanerlashlar zanjiri (hash-chain).

Har bir xaridor skanerlashi zanjirga yangi blok boʻlib qoʻshiladi:
    hash = sha256(oldingi_hash + blok maʼlumotlari)
Shu tufayli:
  * bir quti (GTIN + seriya) boʻyicha barcha skanerlashlar tarixini koʻrsatish mumkin;
  * "Sotib oldim" rejimidagi skanerlash qutini xaridorga "bogʻlaydi". Keyin kimdir shu qutini
    dorixonada skanerlasa, tizim "bu quti allaqachon sotib olingan" deydi. Bu dorixona sotuvni
    kassadan oʻtkazmagan holatda ham ishlaydi (Asl Belgisi buni koʻrmaydi);
  * yozuvni jimgina oʻzgartirib yoki oʻchirib boʻlmaydi: /ledger/verify zanjirni tekshiradi.

Qurilma belgisi (device_hash) — brauzerda yaratilgan tasodifiy ID ning hashi. Ism, telefon, joylashuv saqlanmaydi.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import LedgerBlock

GENESIS = "0" * 64
SALT = "doriishonch-v1"
SAME_BUYER_WINDOW = timedelta(hours=2)


def device_hash(device_id: str | None) -> str:
    if not device_id:
        return ""
    return hashlib.sha256(f"{SALT}:{device_id}".encode()).hexdigest()


def _payload(b: LedgerBlock) -> dict:
    return {
        "index": b.id,
        "prev_hash": b.prev_hash,
        "created_at": b.created_at.replace(microsecond=0).isoformat(),
        "kind": b.kind,
        "gtin": b.gtin,
        "serial": b.serial,
        "pharmacy_id": b.pharmacy_id,
        "region": b.region,
        "verdict": b.verdict,
        "device_hash": b.device_hash,
    }


def compute_hash(b: LedgerBlock) -> str:
    data = json.dumps(_payload(b), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def append(db: Session, *, kind: str, gtin: str, serial: str, pharmacy_id: int | None = None, region: str = "",
           verdict: str = "", device: str = "", scan_id: int | None = None, at: datetime | None = None,
           is_demo: bool = False, commit: bool = True) -> LedgerBlock:
    """Zanjir oxiriga blok qoʻshadi. `device` — allaqachon hashlangan qurilma belgisi."""
    last = db.query(LedgerBlock).order_by(LedgerBlock.id.desc()).first()
    b = LedgerBlock(
        id=(last.id + 1) if last else 1,
        prev_hash=last.hash if last else GENESIS,
        created_at=(at or datetime.utcnow()).replace(microsecond=0),
        kind=kind, gtin=gtin.lstrip("0").zfill(14), serial=serial, pharmacy_id=pharmacy_id, region=region,
        verdict=verdict, device_hash=device, scan_id=scan_id, is_demo=is_demo,
    )
    b.hash = compute_hash(b)
    db.add(b)
    if commit:
        db.commit()
    else:
        db.flush()
    return b


def history(db: Session, gtin: str, serial: str) -> list[LedgerBlock]:
    g = gtin.lstrip("0").zfill(14)
    return (db.query(LedgerBlock).filter(LedgerBlock.gtin == g, LedgerBlock.serial == serial)
            .order_by(LedgerBlock.id).all())


@dataclass
class ChainCheck:
    ok: bool
    blocks: int
    broken_at: int | None = None
    reason: str = ""
    last_hash: str = ""


def verify_chain(db: Session) -> ChainCheck:
    prev = GENESIS
    n = 0
    last_hash = GENESIS
    for b in db.query(LedgerBlock).order_by(LedgerBlock.id).yield_per(1000):
        n += 1
        if b.id != n:
            return ChainCheck(False, n, b.id, f"blok raqami uzilgan: {n} kutilgan, {b.id} topildi")
        if b.prev_hash != prev:
            return ChainCheck(False, n, b.id, "oldingi blok hashi mos emas")
        if compute_hash(b) != b.hash:
            return ChainCheck(False, n, b.id, "blok maʼlumotlari oʻzgartirilgan")
        prev = last_hash = b.hash
    return ChainCheck(True, n, last_hash=last_hash)


@dataclass
class LedgerFacts:
    scans: list[LedgerBlock]
    purchases: list[LedgerBlock]

    @property
    def first(self) -> LedgerBlock | None:
        return self.scans[0] if self.scans else None

    def foreign_purchase(self, device: str, now: datetime, pharmacy_id: int | None) -> LedgerBlock | None:
        """Boshqa xaridor (yoki ancha oldin) qayd etgan sotib olish. Oʻsha xaridorning oʻzi qayta
        skanerlashi (bir qurilma yoki 2 soat ichida shu dorixonada) hisobga olinmaydi."""
        for p in reversed(self.purchases):
            same_device = device and p.device_hash == device
            # 2 soat ichida AYNAN shu dorixonada qayta skan — xaridorning oʻzi (boshqa telefondan) deb hisoblanadi
            # (joy nomaʼlum boʻlsa — faqat qurilmasiz soʻrovda; ilovadan kelgan boshqa qurilma = boshqa odam)
            if p.pharmacy_id is not None and pharmacy_id is not None:
                place_match = p.pharmacy_id == pharmacy_id
            else:
                place_match = not device
            recent_same_place = now - p.created_at <= SAME_BUYER_WINDOW and place_match
            if not same_device and not recent_same_place:
                return p
        return None


def facts(db: Session, gtin: str, serial: str) -> LedgerFacts:
    h = history(db, gtin, serial)
    return LedgerFacts(scans=h, purchases=[b for b in h if b.kind == "purchase"])
