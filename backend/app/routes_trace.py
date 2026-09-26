"""Quti tekshirish, bojxona va inspektor endpointlari."""

from collections import Counter

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .auth import require_role
from .config import settings
from .db import get_db
from .models import ConsumerScan, CustomsDeclaration, CustomsLine, Drug, LedgerBlock, Pack, Participant
from .schemas import (
    AlertOut, ChainEventOut, NearbyPharmacy, ChainStatus, CheckOut, LedgerEntryOut, LedgerInfo, CustomsDeclarationOut, CustomsLineOut, DemoCode, DispenseOut, PackOut,
    ParticipantOut, PharmacyRiskDetail, PharmacyRiskOut, PriceRequest, PriceSummary, ReportRequest, VerifyRequest, VerifyResponse,
)
from .seed_trace import SCENARIO_KEY91, UNREGISTERED_GTIN, scenario_codes
from .ml import learning as ml_learning
from .services import ai, catalog, codes, coverage, customs, ledger, places, prices, rewards, risk, trace

router = APIRouter()

ML_ALERT = 50  # AI bahosi shundan yuqori boʻlsa, qoidalar "ok" desa ham inspektor roʻyxatiga tushadi
REASON_LABEL = {k: v for k, v in trace.HEADLINES.items()}
REPORT_REASONS = {"fake": "Qalbaki deb gumon", "reused": "Qayta ishlatilgan quti", "no_effect": "Dori taʼsir qilmadi",
                  "packaging": "Qadoq shubhali", "price": "Narx gʻalati", "other": "Boshqa"}


def _p(p: Participant | None) -> ParticipantOut | None:
    if not p:
        return None
    return ParticipantOut(id=p.id, kind=p.kind, name=p.name, region=p.region, address=p.address,
                          license_ok=p.license_ok, is_demo=p.is_demo, lat=p.lat, lon=p.lon)


def _entry(b: LedgerBlock) -> LedgerEntryOut:
    return LedgerEntryOut(index=b.id, hash=b.hash, prev_hash=b.prev_hash, created_at=b.created_at, kind=b.kind,
                          gtin=b.gtin, serial=b.serial, pharmacy=b.pharmacy.name if b.pharmacy else "",
                          region=b.region, verdict=b.verdict, is_demo=b.is_demo)


def _ledger_info(db: Session, res: trace.VerifyResult) -> LedgerInfo | None:
    p = res.parsed
    if not (p and p.gtin and p.serial):
        return None
    hist = ledger.history(db, p.gtin, p.serial)
    return LedgerInfo(block=_entry(res.ledger_block) if res.ledger_block else None,
                      history=[_entry(b) for b in hist[-20:]])


def _response(res: trace.VerifyResult, db: Session | None = None) -> VerifyResponse:
    explanation, ai_used = ai.explain_verdict(res)
    parsed = res.parsed
    dispense = None
    if res.drug:
        label, note = trace.DISPENSE.get(res.drug.dispense_category, trace.DISPENSE["rx"])
        dispense = DispenseOut(category=res.drug.dispense_category, label=label, note=note)
    pack = None
    if res.pack:
        pk = res.pack
        pack = PackOut(gtin=pk.gtin, serial=pk.serial, batch=pk.batch, expiry=pk.expiry, status=pk.status,
                       status_label=trace.STATUS_LABEL.get(pk.status, pk.status), owner=_p(pk.owner))
    return VerifyResponse(
        verdict=res.verdict, headline=res.headline, explanation=explanation, ai_used=ai_used,
        checks=[CheckOut(key=c.key, status=c.status, title=c.title, text=c.text) for c in res.checks],
        advice=res.advice,
        parsed={"gtin": parsed.gtin, "serial": parsed.serial, "batch": parsed.batch,
                "expiry": parsed.expiry.isoformat() if parsed.expiry else None} if parsed else {},
        drug=catalog.to_brief(res.drug) if res.drug else None,
        pack=pack,
        chain=[ChainEventOut(**e) for e in (res.remote_chain or (trace.chain(res.pack) if res.pack else []))],
        dispense=dispense, scan_id=res.scan_id, source=res.source,
        is_demo=res.source == "local" and bool((res.pack and res.pack.is_demo) or (res.drug and res.drug.is_demo)),
        ledger=_ledger_info(db, res) if db is not None else None,
        ai_risk=res.ai_risk, new_product=res.new_product,
        places=trace.places(db, res) if db is not None else [],
    )


# ---------------------------------------------------------------- xaridor

@router.get("/pharmacies", response_model=list[ParticipantOut])
def pharmacies(db: Session = Depends(get_db)):
    # Demo dorixonalar va foydalanuvchilar tanlagan haqiqiy (OSM) dorixonalar
    ps = coverage.pharmacies(db.query(Participant).filter(Participant.kind == "pharmacy")).order_by(Participant.is_demo, Participant.region, Participant.name)
    return [_p(p) for p in ps]


@router.get("/pharmacies/nearby", response_model=list[NearbyPharmacy])
def pharmacies_nearby(lat: float, lon: float, radius: int = 1500, db: Session = Depends(get_db)):
    """OpenStreetMap dan atrofdagi haqiqiy dorixonalar."""
    if not (37 <= lat <= 46 and 55 <= lon <= 74):
        raise HTTPException(400, "Joylashuv Oʻzbekiston hududidan tashqarida")
    stored = coverage.pharmacies(db.query(Participant).filter(Participant.kind == "pharmacy", Participant.is_demo.is_(False), Participant.lat.isnot(None), Participant.lon.isnot(None))).all()
    close = sorted(((pharmacy, places.distance_m(lat, lon, pharmacy.lat, pharmacy.lon)) for pharmacy in stored), key=lambda item: item[1])
    close = [(pharmacy, distance) for pharmacy, distance in close if distance <= max(200, min(radius, 5000))]
    if settings.pharmacy_region and close:
        return [NearbyPharmacy(pharmacy=_p(pharmacy), distance_m=int(distance)) for pharmacy, distance in close[:25]]
    try:
        found = places.nearby(db, lat, lon, max(200, min(radius, 5000)))
    except places.PlacesError as e:
        raise HTTPException(502, str(e))
    return [NearbyPharmacy(pharmacy=_p(p), distance_m=int(d)) for p, d in found]


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, db: Session = Depends(get_db)):
    if not (req.code or req.gtin):
        raise HTTPException(400, "Kod yoki GTIN kiriting")
    _check_pharmacy(db, req.pharmacy_id)
    res = trace.verify(db, raw_code=req.code, gtin=req.gtin, serial=req.serial, key91=req.key91,
                       mode=req.mode, pharmacy_id=req.pharmacy_id, device_id=req.device_id, price_paid=req.price_paid,
                       lat=req.lat, lon=req.lon)
    return _with_reward(res, db)


@router.get("/verify/{scan_id}/price", response_model=PriceSummary)
def price_summary(scan_id: int, device_id: str = Header(alias="X-Device-Id", min_length=8, max_length=200), db: Session = Depends(get_db)):
    scan = prices.owned_scan(db, scan_id, device_id)
    return prices.summary(db, scan)


@router.post("/verify/{scan_id}/price", response_model=PriceSummary)
def save_price(scan_id: int, req: PriceRequest, db: Session = Depends(get_db)):
    scan = prices.owned_scan(db, scan_id, req.device_id)
    return prices.save(db, scan, req.price_paid)


def _check_pharmacy(db: Session, pharmacy_id: int | None) -> None:
    if pharmacy_id is None:
        return
    pharmacy = db.get(Participant, pharmacy_id)
    if not pharmacy or pharmacy.kind != "pharmacy":
        raise HTTPException(422, "Dorixona topilmadi")
    if not coverage.in_scope(pharmacy.region):
        raise HTTPException(422, "Hozir faqat Namangan dorixonalarini tanlash mumkin")


def _with_reward(res: trace.VerifyResult, db: Session) -> VerifyResponse:
    out = _response(res, db)
    if res.device:
        out.reward = rewards.award(db, res)
    return out


@router.post("/verify/image", response_model=VerifyResponse)
async def verify_image(file: UploadFile = File(...), mode: str = Form("before"),
                       pharmacy_id: int | None = Form(None), device_id: str | None = Form(None),
                       lat: float | None = Form(None), lon: float | None = Form(None),
                       db: Session = Depends(get_db)):
    """Qadoq surati: avval DataMatrix dekoder, boʻlmasa Claude qutidagi yozuvlardan GTIN/seriyani oʻqiydi."""
    _check_pharmacy(db, pharmacy_id)
    image = await file.read()
    raw = ai.decode_datamatrix(image)
    if raw:
        return _with_reward(trace.verify(db, raw_code=raw, mode=mode, pharmacy_id=pharmacy_id, device_id=device_id,
                                         lat=lat, lon=lon), db)
    data = ai.read_code_from_image(image, file.content_type or "image/jpeg")
    if not data or not data.get("gtin"):
        msg = ("Suratdan kod oʻqilmadi. Kodni yaqinroqdan, yorugʻda suratga oling yoki qoʻlda kiriting."
               if data is not None else
               "Suratdan oʻqish uchun ANTHROPIC_API_KEY kerak. Kamera skaneri yoki qoʻlda kiritishdan foydalaning.")
        raise HTTPException(422, msg)
    return _with_reward(trace.verify(db, gtin=str(data["gtin"]), serial=data.get("serial") or None,
                                     mode=mode, pharmacy_id=pharmacy_id, device_id=device_id, lat=lat, lon=lon), db)


@router.post("/reports")
def report(req: ReportRequest, db: Session = Depends(get_db)):
    scan = db.get(ConsumerScan, req.scan_id)
    if not scan:
        raise HTTPException(404, "Skanerlash topilmadi")
    scan.reported = True
    scan.report_note = req.note[:1000]
    scan.report_reason = req.reason if req.reason in REPORT_REASONS else "other"
    scan.report_status = scan.report_status or "yangi"
    pending = rewards.on_report(db, scan)
    if scan.pack or scan.raw_code:
        p = codes.parse(scan.raw_code) if not scan.pack else None
        gtin, serial = (scan.pack.gtin, scan.pack.serial) if scan.pack else (p.gtin, p.serial)
        if gtin and serial:
            ledger.append(db, kind="report", gtin=gtin, serial=serial, pharmacy_id=scan.pharmacy_id,
                          region=scan.region, verdict=scan.verdict, scan_id=scan.id, commit=False)
    db.commit()
    msg = "Xabaringiz inspektorga yuborildi. Rahmat!"
    if pending:
        msg += f" Inspektor tasdiqlasa, +{pending} ball va +{rewards.POINTS['bounty']} mukofot ball olasiz."
    return {"ok": True, "message": msg, "pending_points": pending}


@router.get("/demo/codes", response_model=list[DemoCode])
def demo_codes(db: Session = Depends(get_db)):
    out = []
    for s in scenario_codes():
        if s["trade_name"]:
            d = db.query(Drug).filter(Drug.trade_name == s["trade_name"]).first()
            gtin = d.gtin
            pack = trace.load_pack(db, gtin, s["serial"])
            expiry, batch = (pack.expiry, pack.batch) if pack else (None, "")
        else:
            gtin, expiry, batch = UNREGISTERED_GTIN, None, ""
        key = "ZZ99" if s["key"] == "bad_key" else SCENARIO_KEY91
        code = codes.build(gtin, s["serial"], expiry=expiry, batch=batch, key91=key)
        display = f"(01){gtin}" + (f"(17){expiry:%y%m%d}" if expiry else "") + (f"(10){batch}" if batch else "") \
            + f"(21){s['serial']}(91){key}"
        ph = db.get(Participant, s["pharmacy_id"]) if s["pharmacy_id"] else None
        if ph and not coverage.in_scope(ph.region):
            ph = None
        out.append(DemoCode(key=s["key"], title=s["title"], expected=s["expected"], mode=s["mode"],
                            pharmacy_id=ph.id if ph else None, pharmacy_name=ph.name if ph else "",
                            trade_name=s["trade_name"] or "Nomaʼlum dori", code=code, code_display=display))
    return out


# ---------------------------------------------------------------- bojxona

def _decl_out(d: CustomsDeclaration) -> CustomsDeclarationOut:
    lines = [CustomsLineOut(id=l.id, description=l.description, gtin=l.gtin, batch=l.batch, quantity=l.quantity,
                            registered_packs=l.registered_packs, match_method=l.match_method,
                            drug=catalog.to_brief(l.matched_drug) if l.matched_drug else None,
                            flags=[f for f in l.flags.split("|") if f]) for l in d.lines]
    return CustomsDeclarationOut(id=d.id, number=d.number, cleared_at=d.cleared_at, customs_post=d.customs_post,
                                 importer=_p(d.importer), origin_country=d.origin_country, source=d.source,
                                 is_demo=d.is_demo, lines=lines, flag_count=sum(len(l.flags) for l in lines))


def _decl_query(db: Session):
    return db.query(CustomsDeclaration).options(
        joinedload(CustomsDeclaration.importer),
        joinedload(CustomsDeclaration.lines).joinedload(CustomsLine.matched_drug).joinedload(Drug.manufacturer))


STAFF_CUSTOMS = [Depends(require_role("customs", "inspector"))]
STAFF_INSPECTOR = [Depends(require_role("inspector"))]


@router.get("/customs/declarations", response_model=list[CustomsDeclarationOut], dependencies=STAFF_CUSTOMS)
def declarations(db: Session = Depends(get_db)):
    ds = _decl_query(db).order_by(CustomsDeclaration.cleared_at.desc()).all()
    return [_decl_out(d) for d in ds]


@router.post("/customs/declarations", response_model=CustomsDeclarationOut,
             dependencies=[Depends(require_role("customs"))])
def ingest_declaration(data: dict, db: Session = Depends(get_db)):
    """Bojxona tizimidan (yoki qoʻlda) deklaratsiya qabul qilish. Format: seed/customs_feed.json."""
    for f in ("number", "importer_tin"):
        if not data.get(f):
            raise HTTPException(400, f"'{f}' maydoni kerak")
    try:
        d = customs.ingest(db, data)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return _decl_out(_decl_query(db).filter(CustomsDeclaration.id == d.id).one())


@router.post("/customs/sync", response_model=list[CustomsDeclarationOut], dependencies=[Depends(require_role("customs"))])
def customs_sync(db: Session = Depends(get_db)):
    """Bojxona manbasidan yangi deklaratsiyalarni olib keladi (demo: seed/customs_feed.json)."""
    try:
        new = customs.sync(db)
    except Exception as e:
        raise HTTPException(502, f"Bojxona manbasiga ulanib boʻlmadi: {e}")
    return [_decl_out(_decl_query(db).filter(CustomsDeclaration.id == d.id).one()) for d in new]


# ---------------------------------------------------------------- inspektor

def _risk_out(r: risk.PharmacyRisk, cls=PharmacyRiskOut, **extra):
    return cls(pharmacy=_p(r.pharmacy), level=r.level, anomaly=r.anomaly, ml_outlier=r.ml_outlier,
               received=r.received, sold=r.sold, sell_through=round(r.sell_through, 3), in_stock=r.in_stock,
               stale=r.stale, scans=r.scans, reuse=r.reuse, unregistered=r.unregistered, clone=r.clone,
               reports=r.reports, signals=r.signals, **extra)


@router.get("/inspector/pharmacies", response_model=list[PharmacyRiskOut], dependencies=STAFF_INSPECTOR)
def inspector_pharmacies(db: Session = Depends(get_db)):
    return [_risk_out(r) for r in risk.compute(db)]


@router.get("/inspector/pharmacies/{pid}", response_model=PharmacyRiskDetail, dependencies=STAFF_INSPECTOR)
def inspector_pharmacy(pid: int, db: Session = Depends(get_db)):
    r = next((x for x in risk.compute(db) if x.pharmacy.id == pid), None)
    if not r:
        raise HTTPException(404, "Dorixona topilmadi")
    summary, used = ai.summarize_pharmacy(risk.facts_text(r), risk.fallback_summary(r))
    return _risk_out(r, PharmacyRiskDetail, summary=summary, ai_used=used)


def _unknown_drug(raw: str) -> str:
    p = codes.parse(raw)
    return f"GTIN {p.gtin}" if p.gtin else "kod oʻqilmadi"


@router.get("/inspector/alerts", response_model=list[AlertOut], dependencies=STAFF_INSPECTOR)
def inspector_alerts(limit: int = 50, sort: str = "new", db: Session = Depends(get_db)):
    """Shubhali skanlar. Qoidalar ogohlantirgan skanlar + qoidalar "ok" degan, lekin AI modeli yuqori xavf
    bergan skanlar. sort=ai — AI bahosi boʻyicha (tekshiruvni eng ehtimolli holatlardan boshlash uchun)."""
    q = (db.query(ConsumerScan)
         .options(joinedload(ConsumerScan.pack).joinedload(Pack.drug), joinedload(ConsumerScan.pharmacy))
         .filter(or_(ConsumerScan.verdict.in_(["danger", "warning"]), ConsumerScan.ml_score >= ML_ALERT)))
    order = ([ConsumerScan.ml_score.desc().nulls_last(), ConsumerScan.at.desc()] if sort == "ai"
             else [ConsumerScan.reported.desc(), ConsumerScan.at.desc()])
    scans = q.order_by(*order).limit(min(limit, 200)).all()
    return [AlertOut(scan_id=s.id, at=s.at, verdict=s.verdict,
                     reasons=[REASON_LABEL.get(r, r) for r in s.reasons.split("|") if r],
                     mode=s.mode, region=s.region, pharmacy=s.pharmacy.name if s.pharmacy else "",
                     drug=s.pack.drug.trade_name if s.pack else _unknown_drug(s.raw_code),
                     serial=s.pack.serial if s.pack else (codes.parse(s.raw_code).serial or s.raw_code[:40]),
                     reported=s.reported, report_note=s.report_note,
                     report_reason=REPORT_REASONS.get(s.report_reason, s.report_reason),
                     report_status=s.report_status, price_paid=s.price_paid, ml_score=s.ml_score) for s in scans]


class ResolveRequest(BaseModel):
    confirmed: bool
    note: str = ""


@router.post("/inspector/reports/{scan_id}/resolve", dependencies=STAFF_INSPECTOR)
def resolve_report(scan_id: int, req: ResolveRequest, db: Session = Depends(get_db)):
    """Inspektor tekshiruv natijasi: tasdiqlansa xaridorga ball va mukofot beriladi."""
    scan = db.get(ConsumerScan, scan_id)
    if not scan:
        raise HTTPException(404, "Skanerlash topilmadi")
    out = rewards.resolve(db, scan, req.confirmed)
    ml_learning.maybe_retrain(db)
    return out


@router.get("/inspector/batch-signals", dependencies=STAFF_INSPECTOR)
def batch_signals(db: Session = Depends(get_db)):
    """Farmakonazorat: bir partiya boʻyicha "taʼsir qilmadi" / qadoq shikoyatlari toʻplansa — sifatsiz dori signali."""
    rows = (db.query(ConsumerScan).options(joinedload(ConsumerScan.pack).joinedload(Pack.drug))
            .filter(ConsumerScan.reported.is_(True), ConsumerScan.pack_id.isnot(None)).all())
    groups: dict[tuple, list[ConsumerScan]] = {}
    for s in rows:
        groups.setdefault((s.pack.drug_id, s.pack.batch), []).append(s)
    out = []
    for (_, batch), items in groups.items():
        reasons = Counter(REPORT_REASONS.get(s.report_reason, "Boshqa") for s in items)
        quality = sum(1 for s in items if s.report_reason in ("no_effect", "packaging"))
        regions = sorted({s.region for s in items if s.region})
        out.append({"drug": items[0].pack.drug.trade_name, "batch": batch, "reports": len(items),
                    "quality_reports": quality, "regions": regions, "reasons": dict(reasons),
                    "level": "yuqori" if quality >= 3 or len(regions) >= 3 else "oʻrta" if len(items) >= 2 else "past",
                    "note": "Bir partiya boʻyicha bir nechta shikoyat: laboratoriya tahlili uchun namuna olish tavsiya etiladi."
                    if len(items) >= 2 else "Yakka shikoyat."})
    order = {"yuqori": 0, "oʻrta": 1, "past": 2}
    return sorted(out, key=lambda r: (order[r["level"]], -r["reports"]))


# ---------------------------------------------------------------- zanjir

@router.get("/ledger/verify", response_model=ChainStatus)
def ledger_verify(db: Session = Depends(get_db)):
    """Butun zanjirni boshidan tekshiradi: birorta blok oʻzgartirilgan yoki oʻchirilganmi."""
    c = ledger.verify_chain(db)
    return ChainStatus(ok=c.ok, blocks=c.blocks, broken_at=c.broken_at, reason=c.reason, last_hash=c.last_hash)


@router.get("/ledger/latest", response_model=list[LedgerEntryOut])
def ledger_latest(limit: int = 30, db: Session = Depends(get_db)):
    bs = (db.query(LedgerBlock).options(joinedload(LedgerBlock.pharmacy))
          .order_by(LedgerBlock.id.desc()).limit(min(limit, 200)).all())
    return [_entry(b) for b in bs]


@router.get("/ledger/code", response_model=list[LedgerEntryOut])
def ledger_code(gtin: str, serial: str, db: Session = Depends(get_db)):
    return [_entry(b) for b in ledger.history(db, gtin, serial)]
