"""Qutini tekshirish: kod → reestr → quti → yoʻli → xulosa.

Xulosa qoidalar asosida chiqariladi (tushuntirib boʻladigan va takrorlanadigan).
AI faqat natijani oddiy tilda tushuntiradi, xulosani oʻzgartirmaydi.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import json
import logging

from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..models import ConsumerScan, CrowdProduct, CustomsLine, Drug, Pack, PackEvent, Participant, QualityAlert
from . import aslbelgisi, codes, ledger
from .catalog import find_by_gtin

log = logging.getLogger(__name__)

SEVERITY = {"ok": 0, "info": 0, "warning": 1, "danger": 2}

STATUS_LABEL = {
    "emitted": "Kod yaratilgan, muomalaga chiqmagan",
    "imported": "Bojxonadan oʻtgan",
    "in_transit": "Distribyutorda / yoʻlda",
    "at_pharmacy": "Dorixonada, sotilmagan",
    "sold": "Sotilgan",
    "withdrawn": "Sotuvdan olib tashlangan",
}

EVENT_LABEL = {
    "produced": "Ishlab chiqarildi",
    "customs_cleared": "Bojxonadan rasmiylashtirildi",
    "received": "Qabul qilindi",
    "shipped": "Joʻnatildi",
    "sold": "Sotildi (kassa cheki)",
    "withdrawn": "Muomaladan chiqarildi",
}

DISPENSE = {
    "otc": ("Retseptsiz", "Bu dori retseptsiz beriladi."),
    "rx": ("Retsept bilan", "Bu dori shifokor retsepti bilan beriladi."),
    "controlled": ("Maxsus nazoratda (QR retsept)",
                   "Kuchli taʼsirli dori: faqat elektron QR retsept bilan beriladi. Retseptsiz taklif qilishsa, "
                   "sotib olmang va xabar bering."),
}

RECENT_SALE = timedelta(hours=24)
CLONE_WINDOW = timedelta(hours=72)
CLONE_REGIONS = 3


@dataclass
class Check:
    key: str
    status: str  # ok, info, warning, danger
    title: str
    text: str


@dataclass
class VerifyResult:
    verdict: str = "unknown"
    headline: str = ""
    checks: list[Check] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)
    drug: Drug | None = None
    pack: Pack | None = None
    parsed: codes.ParsedCode | None = None
    scan_id: int | None = None
    source: str = "local"  # local (demo baza), asl_belgisi yoki crowd (faqat DoriIshonch zanjiri)
    remote_chain: list[dict] = field(default_factory=list)
    mode: str = "before"
    ledger_facts: "ledger.LedgerFacts | None" = None
    ledger_block: object | None = None
    price_paid: int | None = None
    device: str = ""
    ai_risk: dict | None = None  # oʻz modelimiz: {score, level, reasons, model} — signal, xulosa emas
    new_product: dict | None = None  # reestrda yoʻq mahsulot (CrowdProduct)
    lat: float | None = None
    lon: float | None = None

    def add(self, key, status, title, text):
        self.checks.append(Check(key, status, title, text))


def _fmt(dt: datetime | date) -> str:
    if isinstance(dt, datetime):
        local = dt + timedelta(hours=settings.display_utc_offset_hours)  # bazada UTC
        return local.strftime("%d.%m.%Y %H:%M")
    return dt.strftime("%d.%m.%Y")


def _ago(dt: datetime, now: datetime) -> str:
    d = now - dt
    if d < timedelta(hours=1):
        return f"{max(1, int(d.total_seconds() // 60))} daqiqa oldin"
    if d < timedelta(days=1):
        return f"{int(d.total_seconds() // 3600)} soat oldin"
    return f"{d.days} kun oldin"


def _where(p: Participant | None) -> str:
    return f"{p.name} ({p.region})" if p else "nomaʼlum joy"


def load_pack(db: Session, gtin: str, serial: str) -> Pack | None:
    g = gtin.lstrip("0")
    candidates = (
        db.query(Pack)
        .options(joinedload(Pack.events).joinedload(PackEvent.participant), joinedload(Pack.owner),
                 joinedload(Pack.drug).joinedload(Drug.manufacturer))
        .filter(Pack.serial == serial)
        .all()
    )
    return next((p for p in candidates if p.gtin.lstrip("0") == g), None)


def verify(db: Session, raw_code: str | None = None, gtin: str | None = None, serial: str | None = None,
           key91: str | None = None, mode: str = "before", pharmacy_id: int | None = None,
           now: datetime | None = None, record: bool = True, device_id: str | None = None,
           price_paid: int | None = None, lat: float | None = None, lon: float | None = None) -> VerifyResult:
    now = now or datetime.utcnow()
    res = VerifyResult()
    res.lat, res.lon = _coarse(lat, lon)
    res.price_paid = price_paid if price_paid and price_paid > 0 else None
    device = ledger.device_hash(device_id)
    res.mode = mode
    parsed = codes.parse(raw_code) if raw_code else codes.ParsedCode()
    if gtin:
        parsed.gtin = gtin.strip().zfill(14)
    if serial:
        parsed.serial = serial.strip()
    if key91:
        parsed.key91 = key91.strip()
    res.parsed = parsed
    pharmacy = db.get(Participant, pharmacy_id) if pharmacy_id else None

    try:
        if parsed.url:
            record = False  # reklama QR — tekshiruv sifatida saqlanmaydi
            res.verdict = "unknown"
            res.headline = "Bu dori kodi emas"
            res.add("not_medicine_code", "warning", "Bu reklama yoki sayt QR kodi",
                    f"Skanerlangan kod havola: {parsed.url[:60]}. Dori kodi — qutidagi kichik kvadrat kod "
                    "(yonida GTIN/SN yozuvi bor) yoki raqamli shtrix-kod. Oʻshani kameraga tuting.")
            return res
        if not parsed.gtin:
            res.verdict = "unknown"
            res.headline = "Kod oʻqilmadi"
            res.add("unreadable", "warning", "Kod oʻqilmadi",
                    "Qutidagi kichik kvadrat kodni qayta skanerlang yoki uning ostidagi raqamlarni qoʻlda kiriting.")
            return res

        # DoriIshonch zanjiri: bu quti oldin skanerlanganmi / sotib olinganmi
        if parsed.serial:
            res.ledger_facts = ledger.facts(db, parsed.gtin, parsed.serial)
            _ledger_checks(db, res, res.ledger_facts, mode, pharmacy, now, device)

        # 0. Haqiqiy Asl Belgisi (API kalit boʻlsa)
        local_demo = parsed.serial and load_pack(db, parsed.gtin, parsed.serial)
        if parsed.serial and aslbelgisi.get_client() and not (local_demo and local_demo.is_demo):
            remote_res = _verify_remote(db, res, parsed, raw_code, mode, pharmacy, now)
            if remote_res is not None:
                return remote_res

        # 1. Davlat reestri
        drug = find_by_gtin(db, parsed.gtin)
        res.drug = drug
        if not drug:
            flagged = (db.query(CustomsLine).filter(CustomsLine.gtin == parsed.gtin,
                                                    CustomsLine.matched_drug_id.is_(None)).first())
            if flagged or settings.registry_complete:
                _remember_product(db, res, parsed, pharmacy, now)
                via = (f" Bu mahsulot bojxonada reestrga mos kelmagan import sifatida belgilangan "
                       f"(BYD {flagged.declaration.number}).") if flagged else ""
                res.add("unregistered", "danger", "Davlat roʻyxatida yoʻq",
                        f"Bu dori (kod {parsed.gtin}) Oʻzbekistonda roʻyxatdan oʻtgan dorilar orasida topilmadi.{via} "
                        "Bu dori qonuniy muomalada boʻlmasligi mumkin.")
                res.advice += ["Bu dorini sotib olmang.", "Xabar berish tugmasi orqali inspektorga yuboring."]
                return _finish(res)
            _crowd_checks(res, parsed, now)
            _remember_product(db, res, parsed, pharmacy, now)
            _finish(res)
            if res.new_product and res.verdict == "ok":
                res.headline = ("Yangi mahsulot bazaga qoʻshildi" if res.new_product["is_new"]
                                else "Bu mahsulot bazada bor (xaridorlar qoʻshgan)")
            return res
        res.add("registered", "ok", "Davlat roʻyxatida bor", f"{drug.trade_name} ({drug.inn} {drug.strength}) roʻyxatdan oʻtgan.")

        if not parsed.serial:
            res.add("no_serial", "warning", "Faqat oddiy shtrix-kod skanerlandi",
                    "Oddiy shtrix-kod faqat dori turini koʻrsatadi. Aynan shu qutini tekshirish uchun "
                    "kichik kvadrat kodni skanerlang.")
            _dispense(res, drug)
            return _finish(res)

        # 2. Aynan shu quti
        pack = load_pack(db, parsed.gtin, parsed.serial)
        res.pack = pack
        if not pack:
            res.add("serial_unknown", "danger", "Seriya raqami tizimda yoʻq",
                    f"Seriya {parsed.serial} markirovka tizimida roʻyxatga olinmagan. Kod soxta boʻlishi mumkin.")
            res.advice += ["Bu qutini sotib olmang.", "Xabar berish tugmasi orqali inspektorga yuboring."]
            _dispense(res, drug)
            return _finish(res)

        if parsed.key91 and pack.crypto_tail and parsed.key91 != pack.crypto_tail:
            res.add("key_mismatch", "danger", "Kodning himoya qismi mos emas",
                    "Seriya raqami haqiqiy qutiga tegishli, lekin kodning himoya qismi mos kelmadi. "
                    "Bu haqiqiy koddan koʻchirilgan soxta nusxa belgisi.")
            res.advice += ["Bu qutini sotib olmang.", "Xabar bering."]

        # 3. Muomaladan chiqarilgan / sifat ogohlantirishi / muddati
        if pack.status == "withdrawn":
            res.add("withdrawn", "danger", "Sotuvdan olib tashlangan",
                    "Bu quti tizimda muomaladan chiqarilgan deb belgilangan. U sotilmasligi kerak.")
        alert = (db.query(QualityAlert)
                 .filter(QualityAlert.drug_id == drug.id, QualityAlert.batch == pack.batch).first())
        if alert:
            res.add("batch_alert", "danger", f"Seriya boʻyicha ogohlantirish: {alert.type}",
                    f"{pack.batch} partiyasi {_fmt(alert.reported_on)} da ogohlantirish roʻyxatiga kiritilgan: "
                    f"{alert.description}")
            res.advice.append("Bu partiyadagi dorini sotib olmang va dorixonaga qaytaring.")
        if pack.expiry < now.date():
            res.add("expired", "danger", "Yaroqlilik muddati oʻtgan",
                    f"Muddati {_fmt(pack.expiry)} da tugagan.")
            res.advice.append("Muddati oʻtgan dorini ishlatmang.")
        else:
            res.add("expiry", "ok", "Yaroqlilik muddati", f"{_fmt(pack.expiry)} gacha.")

        # 4. Sotuv holati — qayta ishlatilgan qutini aniqlash
        _sale_checks(res, pack, mode, pharmacy, now)

        # 5. Bojxona (import dorilar)
        _customs_check(res, pack, drug)

        # 6. Kod nusxalanganmi (turli viloyatlarda qisqa vaqtda skanerlash)
        _clone_check(db, res, pack, pharmacy, now)

        # 7. Narx: haddan tashqari arzon — qalbaki yoki oʻgʻirlangan dori belgisi boʻlishi mumkin
        _price_check(res, drug)

        _dispense(res, drug)
        return _finish(res)
    finally:
        if record:
            _record(db, res, raw_code or f"{parsed.gtin}/{parsed.serial}", mode, pharmacy, now, device)


PRICE_LOW = 0.6  # reestr narxining 60% idan arzon — shubhali
PRICE_HIGH = 1.5  # 150% dan qimmat — narx qoidabuzarligi (qalbakilik emas)


def _price_check(res: VerifyResult, drug: Drug):
    paid, ref = res.price_paid, drug.price_uzs
    if not paid or not ref:
        return
    if paid < ref * PRICE_LOW:
        res.add("price_too_low", "warning", "Narx shubhali darajada arzon",
                f"Siz {paid:,} soʻm toʻladingiz, odatiy narx esa ~{ref:,} soʻm. Juda arzon dori qalbaki, "
                "muddati oʻtgan yoki oʻgʻirlangan boʻlishi mumkin.".replace(",", " "))
        res.advice.append("Dorixonadan yuk xati (nakladnoy) va sertifikatni soʻrang.")
    elif paid > ref * PRICE_HIGH:
        res.add("price_too_high", "info", "Narx odatdagidan yuqori",
                f"Siz {paid:,} soʻm toʻladingiz, odatiy narx ~{ref:,} soʻm.".replace(",", " "))


def _sale_checks(res: VerifyResult, pack: Pack, mode: str, pharmacy: Participant | None, now: datetime):
    sold = next((e for e in reversed(pack.events) if e.type == "sold"), None)
    if mode == "after":
        if pack.status == "sold" and sold:
            recent = now - sold.at <= RECENT_SALE
            same_place = not pharmacy or sold.participant_id == pharmacy.id
            if recent and same_place:
                res.add("sale_registered", "ok", "Sotuv qayd etilgan",
                        f"Sotuv {_where(sold.participant)} kassasi orqali {_ago(sold.at, now)} rasmiylashtirilgan.")
            elif recent:
                res.add("sold_elsewhere", "warning", "Boshqa dorixonada sotilgan",
                        f"Tizimda bu quti {_where(sold.participant)} da sotilgan, siz esa "
                        f"{_where(pharmacy)} ni tanlagansiz.")
            else:
                res.add("already_sold", "danger", "Bu quti ancha oldin sotilgan",
                        f"Quti {_fmt(sold.at)} da ({_ago(sold.at, now)}) {_where(sold.participant)} da sotilgan. "
                        "Sizga qayta ishlatilgan quti sotilgan boʻlishi mumkin.")
                res.advice += ["Dorini ishlatmang.", "Dorixonadan izoh soʻrang va xabar bering."]
        elif pack.status == "at_pharmacy":
            res.add("sale_not_registered", "warning", "Sotuv qaydi topilmadi",
                    "Demo bazada quti hali sotilmagan. Bu haqiqiy kassa holatini bildirmaydi." if pack.is_demo else
                    "Mavjud maʼlumotda sotuv qaydi yoʻq. Holat yangilanmagan boʻlishi mumkin; chekni tekshiring.")
            res.advice += ["Dorixonadan kassa chekini soʻrang.", "Chek berilmasa, xabar bering."]
        return

    # mode == "before": dorixonada, sotib olishdan oldin
    if pack.status == "sold" and sold:
        if now - sold.at <= timedelta(hours=2):
            res.add("just_sold", "warning", "Hozirgina sotilgan",
                    f"Quti {_ago(sold.at, now)} {_where(sold.participant)} da sotilgan. Agar uni hozir oʻzingiz "
                    "sotib olgan boʻlsangiz, \"Sotib oldim\" rejimida tekshiring.")
        else:
            res.add("already_sold", "danger", "Bu quti oldin sotilgan",
                    f"Quti {_fmt(sold.at)} da ({_ago(sold.at, now)}) {_where(sold.participant)} da sotilgan. "
                    "Qutisi qayta ishlatilgan, ichidagi dori soxta boʻlishi mumkin.")
            res.advice += ["Bu qutini sotib olmang.", "Xabar berish tugmasi orqali inspektorga yuboring."]
    elif pack.status == "at_pharmacy":
        if pharmacy and pack.owner_id != pharmacy.id:
            res.add("other_owner", "warning", "Quti boshqa dorixonaga tegishli",
                    f"Tizimda bu quti {_where(pack.owner)} da turibdi, siz esa {_where(pharmacy)} dasiz. "
                    "Hujjatsiz koʻchirilgan boʻlishi mumkin.")
            res.advice.append("Dorixonadan qutining kirim hujjatini soʻrang.")
        else:
            res.add("in_stock", "ok", "Sotilmagan, dorixonada",
                    f"Quti {_where(pack.owner)} ga rasmiy qabul qilingan va hali sotilmagan.")
    elif pack.status in ("in_transit", "imported", "emitted"):
        res.add("not_delivered", "warning", "Dorixonaga rasmiy yetib kelmagan",
                f"Tizimda quti hali {_where(pack.owner)} da ({STATUS_LABEL.get(pack.status, pack.status)}). "
                "Dorixona uni rasmiy qabul qilmagan.")


def _customs_check(res: VerifyResult, pack: Pack, drug: Drug):
    if drug.manufacturer.is_local:
        made = next((e for e in pack.events if e.type == "produced"), None)
        if made:
            res.add("produced", "ok", "Mahalliy ishlab chiqarilgan",
                    f"{_where(made.participant)} da {_fmt(made.at)} da ishlab chiqarilgan.")
        return
    cleared = next((e for e in pack.events if e.type == "customs_cleared"), None)
    if not cleared:
        res.add("no_customs", "warning", "Bojxonadan oʻtgani koʻrinmayapti",
                f"Dori {drug.manufacturer.country} da ishlab chiqarilgan, lekin bu quti uchun bojxona "
                "rasmiylashtiruvi topilmadi. Rasmiy yoʻlsiz (kulrang) import boʻlishi mumkin.")
        return
    line = pack.customs_line
    post = line.declaration.customs_post if line else ""
    res.add("customs", "ok", "Bojxonadan rasmiy oʻtgan",
            f"BYD {cleared.document}, {_fmt(cleared.at)}, {post}. Importyor: {_where(cleared.participant)}.")
    if cleared.participant and not cleared.participant.license_ok:
        res.add("importer_license", "warning", "Import qilgan kompaniya litsenziyasi",
                f"{cleared.participant.name} ning faoliyat litsenziyasi amalda emas.")


def _clone_check(db: Session, res: VerifyResult, pack: Pack, pharmacy: Participant | None, now: datetime):
    recent = (db.query(ConsumerScan)
              .filter(ConsumerScan.pack_id == pack.id, ConsumerScan.at >= now - CLONE_WINDOW).all())
    regions = {s.region for s in recent if s.region}
    if pharmacy:
        regions.add(pharmacy.region)
    if len(regions) >= CLONE_REGIONS:
        res.add("clone", "warning", "Kod nusxalangan boʻlishi mumkin",
                f"Bu quti oxirgi 3 kunda {len(regions)} ta viloyatda skanerlangan: {', '.join(sorted(regions))}. "
                "Bitta quti bir vaqtda turli joyda boʻla olmaydi.")
        res.advice.append("Ehtiyot boʻling va xabar bering.")


def _dispense(res: VerifyResult, drug: Drug):
    label, text = DISPENSE.get(drug.dispense_category, DISPENSE["rx"])
    res.add(f"dispense_{drug.dispense_category}", "info", label, text)


HEADLINES = {
    "already_sold": "Diqqat: bu quti oldin sotilgan",
    "serial_unknown": "Diqqat: kod tizimda yoʻq",
    "unregistered": "Diqqat: dori davlat roʻyxatida yoʻq",
    "key_mismatch": "Diqqat: kod soxta boʻlishi mumkin",
    "withdrawn": "Diqqat: dori sotuvdan olib tashlangan",
    "batch_alert": "Diqqat: bu partiya boʻyicha ogohlantirish bor",
    "expired": "Diqqat: muddati oʻtgan",
    "sale_not_registered": "Sotuv qaydi topilmadi",
    "clone": "Kod nusxalangan boʻlishi mumkin",
    "no_customs": "Bojxonadan oʻtgani koʻrinmayapti",
    "other_owner": "Quti boshqa dorixonaga tegishli",
    "not_delivered": "Quti dorixonaga rasmiy kelmagan",
    "sold_elsewhere": "Boshqa dorixonada sotilgan",
    "just_sold": "Quti hozirgina sotilgan",
    "importer_license": "Import qilgan kompaniyada muammo",
    "no_serial": "Qutidagi kichik kvadrat kodni skanerlang",
    "not_introduced": "Dori sotuvga rasmiy chiqarilmagan",
    "already_claimed": "Diqqat: bu quti allaqachon sotib olingan",
    "double_claim": "Diqqat: bu qutini boshqa xaridor sotib olgan",
    "bad_gtin": "Kod tuzilishi xato",
    "price_too_low": "Narx shubhali darajada arzon",
}
INFO_HEADLINES = {"own_purchase": "Bu quti sizniki: siz uni sotib olgansiz"}


def _finish(res: VerifyResult) -> VerifyResult:
    worst = max((c for c in res.checks), key=lambda c: SEVERITY.get(c.status, 0), default=None)
    level = SEVERITY.get(worst.status, 0) if worst else 0
    res.verdict = {0: "ok", 1: "warning", 2: "danger"}[level]
    if level == 0:
        own = next((c for c in res.checks if c.key in INFO_HEADLINES), None)
        if own and res.mode == "before":
            res.headline = INFO_HEADLINES[own.key]
        elif res.mode == "after":
            res.headline = "Xarid qayd etildi: quti endi sizga bogʻlandi"
            res.advice.append("Endi bu quti boshqa joyda qayta sotilsa, skanerlagan xaridor ogohlantiriladi.")
        elif res.source == "crowd":
            res.headline = "Quti oldin sotilgan deb qayd etilmagan"
        else:
            res.headline = "Tekshiruv yakunlandi"
        if res.mode == "before" and not res.advice:
            res.advice.append("Xarid qilgach, \"Sotib oldim\" rejimida qayta skanerlang: quti sizga bogʻlanadi.")
    else:
        res.headline = HEADLINES.get(worst.key, worst.title)
    # takroriy maslahatlarni olib tashlaymiz
    res.advice = list(dict.fromkeys(res.advice))
    return res


def _record(db: Session, res: VerifyResult, raw: str, mode: str, pharmacy: Participant | None, now: datetime,
            device: str = ""):
    reasons = [c.key for c in res.checks if c.status in ("warning", "danger")]
    res.device = device
    features = None
    # AI bahosi faqat reestrdagi dorilar uchun (model shu maʼlumotda oʻqitilgan)
    if res.parsed and res.parsed.gtin and res.drug is not None:
        from ..ml import risk_features, risk_model

        drug = res.drug
        features = risk_features.compute(
            db, {c.key for c in res.checks}, res.pack, pharmacy, res.price_paid,
            drug.price_uzs if drug else None,
            (not drug.manufacturer.is_local) if drug and drug.manufacturer else None, mode, now)
        res.ai_risk = risk_model.score(features, db)
    scan = ConsumerScan(pack_id=res.pack.id if res.pack else None, raw_code=raw[:200], mode=mode,
                        pharmacy_id=pharmacy.id if pharmacy else None, region=pharmacy.region if pharmacy else "",
                        verdict=res.verdict if res.verdict != "unknown" else "warning",
                        reasons="|".join(reasons), at=now, device_hash=device, price_paid=res.price_paid,
                        ml_features=json.dumps(features) if features else "",
                        ml_score=res.ai_risk["score"] if res.ai_risk else None, lat=res.lat, lon=res.lon)
    db.add(scan)
    db.flush()
    res.scan_id = scan.id
    p = res.parsed
    if p and p.gtin and p.serial:
        disputed = any(c.key in ("already_claimed", "double_claim") for c in res.checks)
        kind = ("disputed" if disputed else "purchase") if mode == "after" else "scan"
        block = ledger.append(db, kind=kind, gtin=p.gtin, serial=p.serial, pharmacy_id=scan.pharmacy_id,
                              region=scan.region, verdict=scan.verdict, device=device, scan_id=scan.id, at=now,
                              commit=False)
        res.ledger_block = block
    db.commit()


PLACE_LABEL = {"purchase": "Sotib olingan (xaridor)", "disputed": "Bahsli xarid", "scan": "Tekshirilgan",
               "sold": "Sotilgan (kassa)", "received": "Dorixonaga kelgan", "customs_cleared": "Bojxonadan oʻtgan"}


def places(db: Session, res: VerifyResult) -> list[dict]:
    """Xarita uchun: bu quti (yoki seriyasiz mahsulot) qayerda sotilgan, tekshirilgan, qabul qilingan."""
    out: list[dict] = []

    def add(kind, lat, lon, at, place, me=False):
        if lat is None or lon is None:
            return
        out.append({"kind": kind, "label": PLACE_LABEL.get(kind, kind), "lat": lat, "lon": lon,
                    "at": at.isoformat() if at else None, "place": place, "me": me})

    if res.pack is not None:
        for e in res.pack.events:
            if e.type in ("received", "sold") and e.participant is not None:
                add(e.type, e.participant.lat, e.participant.lon, e.at, _where(e.participant))
    p = res.parsed
    if p and p.gtin and p.serial:
        for b in ledger.history(db, p.gtin, p.serial)[-60:]:
            scan = db.get(ConsumerScan, b.scan_id) if b.scan_id else None
            lat = scan.lat if scan and scan.lat is not None else (b.pharmacy.lat if b.pharmacy else None)
            lon = scan.lon if scan and scan.lon is not None else (b.pharmacy.lon if b.pharmacy else None)
            add(b.kind, lat, lon, b.created_at, _where(b.pharmacy) if b.pharmacy else (b.region or ""),
                me=bool(res.device and b.device_hash == res.device))
    elif p and p.gtin:
        g13 = p.gtin.lstrip("0")
        rows = (db.query(ConsumerScan).filter(ConsumerScan.pack_id.is_(None), ConsumerScan.raw_code.contains(g13))
                .order_by(ConsumerScan.at.desc()).limit(60).all())
        for sc in rows:
            ph = sc.pharmacy
            add("scan", sc.lat if sc.lat is not None else (ph.lat if ph else None),
                sc.lon if sc.lon is not None else (ph.lon if ph else None), sc.at,
                _where(ph) if ph else (sc.region or ""), me=bool(res.device and sc.device_hash == res.device))
    return out


def chain(pack: Pack) -> list[dict]:
    return [{
        "type": e.type,
        "label": EVENT_LABEL.get(e.type, e.type),
        "participant": e.participant.name if e.participant else "",
        "participant_kind": e.participant.kind if e.participant else "",
        "region": e.participant.region if e.participant else "",
        "at": e.at,
        "document": e.document,
    } for e in pack.events]


# ---------------------------------------------------------------- haqiqiy Asl Belgisi

REMOTE_EVENT_LABEL = {
    "EMISSION": "Kod yaratildi", "APPLICATION": "Qadoqqa tushirildi", "UTILISATION": "Qadoqqa tushirildi",
    "INTRODUCTION": "Muomalaga kiritildi", "IMPORT": "Import qilindi", "CUSTOMS": "Bojxonadan rasmiylashtirildi",
    "ACCEPTANCE": "Qabul qilindi", "SHIPMENT": "Joʻnatildi", "TRANSFER": "Boshqa ishtirokchiga oʻtkazildi",
    "WITHDRAWAL": "Muomaladan chiqarildi", "RETAIL": "Sotildi (kassa)", "RETURN": "Qaytarildi",
}


def _remote_label(e) -> str:
    t = e.type.upper()
    if e.is_sale:
        return "Sotildi (kassa)"
    if e.is_customs:
        return "Bojxona / import"
    for k, v in REMOTE_EVENT_LABEL.items():
        if k in t:
            return v
    return e.type.replace("_", " ").capitalize() or "Hodisa"


def _tin_name(db: Session, tin: str) -> tuple[str, str, str]:
    if not tin:
        return "", "", ""
    p = db.query(Participant).filter(Participant.tin == tin).first()
    return (p.name, p.region, p.kind) if p else (f"STIR {tin}", "", "")


def _verify_remote(db, res: VerifyResult, parsed, raw_code, mode, pharmacy, now):
    """Asl Belgisi javobidan xulosa. Aloqa boʻlmasa None qaytaradi (lokal bazaga qaytamiz)."""
    code = raw_code or codes.build(parsed.gtin, parsed.serial, key91=parsed.key91 or "")
    try:
        info = aslbelgisi.get_client().code_info(code, history=True)
    except aslbelgisi.AslBelgisiError as e:
        log.warning("Asl Belgisi: %s", e)
        res.add("remote_unavailable", "info", "Asl Belgisi bilan aloqa yoʻq",
                f"{e}. Natija ichki bazadan olindi.")
        return None

    res.source = "asl_belgisi"
    drug = find_by_gtin(db, parsed.gtin)
    res.drug = drug
    if info is None:
        res.add("serial_unknown", "danger", "Kod rasmiy bazada yoʻq",
                "Bu kod rasmiy markirovka tizimida topilmadi. Soxta kod boʻlishi mumkin.")
        res.advice += ["Bu qutini sotib olmang.", "Xabar berish tugmasi orqali inspektorga yuboring."]
        return _finish(res)

    who = info.issuer_name or (f"STIR {info.issuer_tin}" if info.issuer_tin else "nomaʼlum")
    res.add("registered", "ok", "Rasmiy markirovka bazasida bor",
            f"Kod rasmiy tizimda roʻyxatda. Kodni olgan tashkilot: {who}.")

    for e in info.history:
        name, region, kind = _tin_name(db, e.receiver_tin or e.sender_tin)
        res.remote_chain.append({
            "type": "sold" if e.is_sale else ("customs_cleared" if e.is_customs else e.type.lower()),
            "label": _remote_label(e), "participant": name, "participant_kind": kind, "region": region,
            "at": e.at or now, "document": " ".join(filter(None, [e.document_type, e.document_id]))[:80],
        })

    if info.expiration_date and info.expiration_date.date() < now.date():
        res.add("expired", "danger", "Yaroqlilik muddati oʻtgan", f"Muddati {_fmt(info.expiration_date.date())} da tugagan.")
        res.advice.append("Muddati oʻtgan dorini ishlatmang.")
    elif info.expiration_date:
        res.add("expiry", "ok", "Yaroqlilik muddati", f"{_fmt(info.expiration_date.date())} gacha.")

    if drug and info.series:
        alert = db.query(QualityAlert).filter(QualityAlert.drug_id == drug.id, QualityAlert.batch == info.series).first()
        if alert:
            res.add("batch_alert", "danger", f"Seriya boʻyicha ogohlantirish: {alert.type}", alert.description)

    sale = info.sale_event
    st = info.internal_status
    if st == "emitted":
        res.add("not_introduced", "warning", "Sotuvga rasmiy chiqarilmagan",
                f"Kod mavjud, lekin rasmiy muomalaga kiritilmagan (status: {info.status}). Bunday quti sotuvda boʻlmasligi kerak.")
    elif st == "withdrawn" and sale:
        where = _tin_name(db, sale.sender_tin or sale.receiver_tin)[0] or "nomaʼlum joyda"
        when = sale.at
        age = (now - when) if when else None
        if mode == "after" and age is not None and age <= RECENT_SALE:
            res.add("sale_registered", "ok", "Sotuv qayd etilgan", f"Sotuv {where} kassasi orqali {_ago(when, now)} rasmiylashtirilgan.")
        elif mode == "before" and age is not None and age <= timedelta(hours=2):
            res.add("just_sold", "warning", "Hozirgina sotilgan",
                    f"Quti {_ago(when, now)} sotilgan. Oʻzingiz sotib olgan boʻlsangiz, \"Sotib oldim\" rejimida tekshiring.")
        else:
            when_txt = f"{_fmt(when)} da ({_ago(when, now)})" if when else "oldin"
            res.add("already_sold", "danger", "Bu quti oldin sotilgan",
                    f"Quti {when_txt} {where} da sotilgan. Qutisi qayta ishlatilgan, ichidagi dori soxta boʻlishi mumkin.")
            res.advice += ["Bu qutini sotib olmang.", "Xabar berish tugmasi orqali inspektorga yuboring."]
    elif st == "withdrawn":
        reason = info.extended_status or "koʻrsatilmagan"
        res.add("withdrawn", "danger", "Sotuvdan olib tashlangan", f"Kod muomaladan chiqarilgan (sabab: {reason}). Bu quti sotilmasligi kerak.")
    elif st == "in_circulation":
        if mode == "after":
            res.add("sale_not_registered", "warning", "Sotuv qaydi topilmadi",
                    "Rasmiy tizimda quti hali muomalada. Sotuv holati yangilanmagan boʻlishi mumkin; chekni tekshiring.")
            res.advice += ["Dorixonadan kassa chekini soʻrang.", "Chek berilmasa, xabar bering."]
        else:
            last_owner = next((e.receiver_tin for e in reversed(info.history) if e.receiver_tin), "")
            if pharmacy and pharmacy.tin and last_owner and last_owner != pharmacy.tin:
                res.add("other_owner", "warning", "Quti boshqa tashkilotga tegishli",
                        f"Rasmiy tizimda quti {_tin_name(db, last_owner)[0]} da, siz esa {_where(pharmacy)} dasiz.")
            else:
                res.add("in_stock", "ok", "Hali sotilmagan", "Quti rasmiy muomalada va hali sotilmagan.")
    else:
        res.add("remote_status", "info", "Kod holati", f"Asl Belgisi statusi: {info.status} {info.extended_status}".strip())

    ce = info.customs_event
    if ce:
        res.add("customs", "ok", "Bojxonadan oʻtgan",
                f"{_fmt(ce.at) if ce.at else ''} {ce.document_type} {ce.document_id}".strip())
    elif drug and not drug.manufacturer.is_local:
        res.add("customs_unknown", "info", "Bojxona maʼlumoti topilmadi",
                "Kod tarixida import hodisasi koʻrinmadi (tarix toʻliq boʻlmasligi mumkin).")

    # Nusxa kod: shu seriya boshqa viloyatlarda yaqinda skanerlanganmi
    recent = (db.query(ConsumerScan)
              .filter(ConsumerScan.raw_code.contains(parsed.serial), ConsumerScan.at >= now - CLONE_WINDOW).all())
    regions = {s.region for s in recent if s.region} | ({pharmacy.region} if pharmacy else set())
    if len(regions) >= CLONE_REGIONS:
        res.add("clone", "warning", "Kod nusxalangan boʻlishi mumkin",
                f"Bu kod oxirgi 3 kunda {len(regions)} ta viloyatda skanerlangan: {', '.join(sorted(regions))}.")

    if drug:
        _dispense(res, drug)
    return _finish(res)


# ---------------------------------------------------------------- DoriIshonch zanjiri va "olomon" rejimi

def _ledger_checks(db: Session, res: VerifyResult, lf, mode: str, pharmacy: Participant | None, now: datetime,
                   device: str):
    fp = lf.foreign_purchase(device, now, pharmacy.id if pharmacy else None)
    if fp:
        where = _where(fp.pharmacy) if fp.pharmacy else (fp.region or "nomaʼlum joy")
        when = f"{_fmt(fp.created_at)} da ({_ago(fp.created_at, now)})"
        if mode == "before":
            res.add("already_claimed", "danger", "Bu quti allaqachon sotib olingan",
                    f"Boshqa xaridor bu qutini {when} {where} da sotib olgan. U qayta sotuvda boʻlmasligi "
                    "kerak: qutisi qayta ishlatilgan boʻlishi mumkin.")
            res.advice += ["Bu qutini sotib olmang.", "Xabar berish tugmasi orqali inspektorga yuboring."]
        else:
            res.add("double_claim", "danger", "Bu qutini boshqa xaridor sotib olgan",
                    f"Bu quti {when} {where} da boshqa xaridor tomonidan sotib olingan. "
                    "Sizga qayta ishlatilgan quti berilgan boʻlishi mumkin.")
            res.advice += ["Dorini ishlatmang.", "Dorixonadan izoh soʻrang va xabar bering."]
    mine = [b for b in lf.purchases if device and b.device_hash == device]
    if mine and not fp:
        b = mine[-1]
        where = _where(b.pharmacy) if b.pharmacy else (b.region or "nomaʼlum joy")
        res.add("own_purchase", "info", "Bu qutini siz sotib olgansiz",
                f"Siz uni {_fmt(b.created_at)} da ({_ago(b.created_at, now)}) {where} da sotib olgansiz — quti sizga "
                "bogʻlangan. Boshqa odam uni skanerlasa, \"oldin sotilgan\" degan ogohlantirish koʻradi.")
    others = [b for b in lf.scans if not (device and b.device_hash == device)]
    if others:
        first = others[0]
        where = _where(first.pharmacy) if first.pharmacy else (first.region or "nomaʼlum joy")
        res.add("prior_scans", "info", "Bu quti avval ham tekshirilgan",
                f"Bu qutini oldin {len(others)} marta tekshirishgan. Birinchi marta: {_fmt(first.created_at)}, {where}.")
    else:
        res.add("first_scan", "info", "Birinchi marta tekshirilmoqda",
                "Bu qutini hali hech kim tekshirmagan. Tekshiruvingiz saqlandi.")


def gtin_check_digit_ok(gtin: str) -> bool:
    """GS1 nazorat raqami (GTIN-8/12/13/14)."""
    d = gtin.strip()
    if not d.isdigit() or len(d) not in (8, 12, 13, 14):
        return False
    body, check = d[:-1], int(d[-1])
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def _coarse(lat: float | None, lon: float | None) -> tuple[float | None, float | None]:
    """Joylashuv ~100 m gacha yaxlitlanadi; Oʻzbekistondan tashqari yoki notoʻgʻri qiymat saqlanmaydi."""
    if lat is None or lon is None or not (36 <= lat <= 46 and 55 <= lon <= 74):
        return None, None
    return round(lat, 3), round(lon, 3)


def _remember_product(db: Session, res: VerifyResult, parsed, pharmacy: Participant | None, now: datetime):
    """Reestrda yoʻq mahsulotni bazaga yozadi (yoki hisoblagichini oshiradi) — keyin inspektor koʻrib chiqadi."""
    gtin = parsed.gtin.zfill(14)
    p = db.query(CrowdProduct).filter(CrowdProduct.gtin == gtin).first()
    is_new = p is None
    if is_new:
        p = CrowdProduct(gtin=gtin, first_seen=now, scans=0, gtin_valid=gtin_check_digit_ok(gtin))
        db.add(p)
    p.scans += 1
    p.last_seen = now
    lat, lon = res.lat, res.lon
    if lat is None and pharmacy is not None and pharmacy.lat is not None:
        lat, lon = pharmacy.lat, pharmacy.lon
    if lat is not None:
        p.last_lat, p.last_lon = lat, lon
    if pharmacy is not None:
        p.last_pharmacy_id, p.last_region = pharmacy.id, pharmacy.region
    db.flush()
    res.new_product = {"gtin": gtin, "name": p.name, "scans": p.scans, "is_new": is_new,
                       "has_location": p.last_lat is not None}
    res.add("new_product", "info", "Bazaga qoʻshildi" if is_new else "Bazada bor",
            ("Bu mahsulot bizning bazamizda yoʻq edi — endi qoʻshildi" if is_new else
             f"Bu mahsulot xaridorlar tomonidan {p.scans} marta skanerlangan") +
            (" va xaritaga belgilandi." if p.last_lat is not None else ".") +
            " Inspektor uni rasmiy reestr bilan solishtiradi.")


def _crowd_checks(res: VerifyResult, parsed, now: datetime):
    """Dori bizning reestrimizda yoʻq va Asl Belgisi ulanmagan: kod tuzilishi + zanjir."""
    res.source = "crowd"
    res.add("official_unavailable", "info", "Rasmiy bazaga ulanmagan",
            "Bu dori bizning maʼlumotlar bazamizda yoʻq va Asl Belgisi ulanmagan. Faqat kod tuzilishi va "
            "DoriIshonch skanerlashlar zanjiri tekshirildi. Haqiqiyligini Asl Belgisi ilovasida ham tekshiring.")
    if gtin_check_digit_ok(parsed.gtin):
        res.add("gtin_ok", "ok", "Kod toʻgʻri tuzilgan", "Koddagi tekshiruv raqami toʻgʻri.")
    else:
        res.add("bad_gtin", "warning", "Kod tuzilishi xato",
                "Koddagi tekshiruv raqami mos emas. Kod notoʻgʻri oʻqilgan yoki soxta boʻlishi mumkin.")
    if parsed.key91 and parsed.crypto92:
        res.add("crypto_present", "ok", "Himoya kodi bor", "Kodda Asl Belgisi kriptografik himoya qismi (91, 92) bor.")
    if parsed.expiry:
        if parsed.expiry < now.date():
            res.add("expired", "danger", "Yaroqlilik muddati oʻtgan", f"Kod boʻyicha muddati {_fmt(parsed.expiry)} da tugagan.")
            res.advice.append("Muddati oʻtgan dorini ishlatmang.")
        else:
            res.add("expiry", "ok", "Yaroqlilik muddati", f"{_fmt(parsed.expiry)} gacha.")
