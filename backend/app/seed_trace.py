"""Kuzatuv tizimi uchun demo maʼlumotlar: ishtirokchilar, qutilar, hodisalar,
bojxona deklaratsiyalari va xaridor skanerlashlari.

Hammasi sunʼiy (is_demo=True) va har safar bir xil chiqadi (random seed). Sanalar
bazani yaratgan paytga nisbatan hisoblanadi, shuning uchun "47 kun oldin sotilgan"
kabi holatlar doim dolzarb koʻrinadi.

DEMO_SCENARIOS — hakamlar oldida skanerlash uchun tayyor kodlar (/demo/codes).
"""

import random
import string
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    ConsumerScan, CustomsDeclaration, CustomsLine, Drug, Manufacturer, Pack, PackEvent, Participant,
    QualityAlert,
)

# ---------------------------------------------------------------- ishtirokchilar

PARTICIPANTS = [
    # id, kind, name, tin, region, address, license_ok
    (101, "importer", "Farm Import Demo MChJ", "300000101", "Toshkent", "Mirobod tumani", True),
    (102, "importer", "Ipak Yoʻli Demo Pharm", "300000102", "Toshkent", "Yakkasaroy tumani", True),
    (103, "importer", "Tezkor Demo Savdo", "300000103", "Toshkent viloyati", "Zangiota tumani", False),
    (201, "distributor", "Markaz Demo Distribyutsiya", "300000201", "Toshkent", "Sergeli tumani", True),
    (202, "distributor", "Vodiy Demo Logistika", "300000202", "Fargʻona", "Fargʻona shahri", True),
    (301, "pharmacy", "Shifo Demo Dorixona", "300000301", "Toshkent", "Yunusobod, Amir Temur 12", True),
    (302, "pharmacy", "Sogʻlom Demo Apteka", "300000302", "Toshkent", "Chilonzor, Bunyodkor 5", True),
    (303, "pharmacy", "Bahor Demo Dorixona", "300000303", "Samarqand", "Samarqand shahri, Registon koʻch. 8", True),
    (304, "pharmacy", "Najot Demo Dorixona", "300000304", "Fargʻona", "Fargʻona shahri, Mustaqillik 21", True),
    (305, "pharmacy", "Buxoro Demo Farm", "300000305", "Buxoro", "Buxoro shahri, Navoiy 3", True),
    (306, "pharmacy", "Andijon Demo Apteka", "300000306", "Andijon", "Andijon shahri, Bobur 14", True),
    (307, "pharmacy", "Nukus Demo Dorixona", "300000307", "Qoraqalpogʻiston", "Nukus shahri, Doʻstlik 7", True),
    (308, "pharmacy", "Qarshi Demo Dorixona", "300000308", "Qashqadaryo", "Qarshi shahri, Nasaf 19", True),
    (309, "pharmacy", "Namangan Demo Dorixona", "300000309", "Namangan", "Namangan shahri, Navoiy 25", True),
    (310, "pharmacy", "Guliston Demo Apteka", "300000310", "Sirdaryo", "Guliston shahri, Oʻzbekiston 4", True),
    (311, "pharmacy", "Jizzax Demo Dorixona", "300000311", "Jizzax", "Jizzax shahri, Sh. Rashidov 11", True),
    (312, "pharmacy", "Navoiy Demo Farm", "300000312", "Navoiy", "Navoiy shahri, Galaba 9", True),
    (313, "pharmacy", "Urganch Demo Dorixona", "300000313", "Xorazm", "Urganch shahri, Al-Xorazmiy 17", True),
    (314, "pharmacy", "Termiz Demo Apteka", "300000314", "Surxondaryo", "Termiz shahri, At-Termiziy 6", True),
    (315, "pharmacy", "Nurafshon Demo Dorixona", "300000315", "Toshkent viloyati", "Nurafshon shahri, Toshkent yoʻli 2", True),
    (316, "pharmacy", "Ulugʻbek Demo Apteka", "300000316", "Toshkent", "Mirzo Ulugʻbek, Buyuk Ipak yoʻli 40", True),
    (317, "pharmacy", "Siyob Demo Dorixona", "300000317", "Samarqand", "Samarqand shahri, Siyob bozori yoni", True),
    (318, "pharmacy", "Qoʻqon Demo Farm", "300000318", "Fargʻona", "Qoʻqon shahri, Turkiston 13", True),
]
# Xarita uchun koordinatalar (demo: shahar markaziga yaqin, haqiqiy dorixona emas)
COORDS = {
    101: (41.2995, 69.2826), 102: (41.2873, 69.2502), 103: (41.1920, 69.1440), 201: (41.2260, 69.2220),
    202: (40.3790, 71.7920),
    301: (41.3650, 69.2850), 302: (41.2750, 69.2040), 303: (39.6548, 66.9757), 304: (40.3890, 71.7830),
    305: (39.7740, 64.4200), 306: (40.7830, 72.3500), 307: (42.4610, 59.6030), 308: (38.8600, 65.7980),
    309: (40.9990, 71.6680), 310: (40.4900, 68.7810), 311: (40.1170, 67.8400), 312: (40.1030, 65.3740),
    313: (41.5520, 60.6300), 314: (37.2260, 67.2780), 315: (41.0420, 69.3560), 316: (41.3380, 69.3340),
    317: (39.6620, 66.9450), 318: (40.5286, 70.9425),
}
PHARMACIES = [p[0] for p in PARTICIPANTS if p[1] == "pharmacy"]
BAD_PHARMACY = 303  # qayta ishlatilgan qutilar koʻp aniqlangan dorixona
SLOPPY_PHARMACY = 308  # sotuvni kassadan oʻtkazmaydigan holatlar

CUSTOMS_POSTS = ["Toshkent-AERO bojxona posti", "Yallama bojxona posti", "Oybek bojxona posti"]


def _mfr_participant_id(manufacturer_id: int) -> int:
    return 400 + manufacturer_id


# ---------------------------------------------------------------- demo stsenariylar

DEMO_SCENARIOS = [
    # key, drug trade_name, serial, title, expected verdict, mode, pharmacy_id (skaner qilinadigan joy)
    ("ok", "Amlozar", "DEMOOK0000001", "Hammasi joyida: mahalliy dori, dorixonada, hali sotilmagan", "ok", "before", 301),
    ("reused", "Norvadin", "DEMOREUSE0001", "Qayta ishlatilgan quti: shu dorixonada 47 kun oldin sotilgan", "danger", "before", 303),
    ("fake", "Norvadin", "DEMOFAKE00001", "Qalbaki: bunday seriya raqami tizimda yoʻq", "danger", "before", None),
    ("unregistered", None, "UNKNOWN000001", "Roʻyxatdan oʻtmagan dori (GTIN reestrda yoʻq)", "danger", "before", None),
    ("clone", "Metgan", "DEMOCLONE0001", "Nusxalangan kod: 2 kunda 3 ta viloyatda skanerlangan", "warning", "before", None),
    ("grey_import", "Amoxibos", "DEMOGREY00001", "Bojxona yozuvi yoʻq import (kulrang import)", "warning", "before", 304),
    ("recall", "Diaform-O", "DEMORECALL001", "Muomaladan chiqarilgan seriya hali sotuvda", "danger", "before", 305),
    ("controlled", "Zartramol", "DEMOQRRX00001", "Nazoratdagi dori: faqat elektron QR retsept bilan", "ok", "before", 301),
    ("not_registered_sale", "Tumlodip", "DEMONOCHECK01", "Sotib olindi, lekin sotuv kassadan oʻtkazilmagan", "warning", "after", 303),
    ("diverted", "Registan-Losartan", "DEMOOTHER0001", "Quti boshqa dorixonaga tegishli (Nukus)", "warning", "before", 301),
    ("claimed", "Amlotens", "DEMOCLAIM0001",
     "Kassadan oʻtmagan, lekin xaridor 20 kun oldin sotib olgan quti yana sotuvda (DoriIshonch zanjiri)",
     "danger", "before", 303),
    ("expired", "Paralpina", "DEMOEXPIRED01", "Yaroqlilik muddati oʻtgan", "danger", "before", None),
    ("bad_key", "Amlozar", "DEMOOK0000001", "Seriya toʻgʻri, lekin tekshiruv kaliti mos emas (soxta nusxa)", "danger", "before", None),
]
UNREGISTERED_GTIN = "04789999999997"
SCENARIO_KEY91 = "EE07"


def _serial(rnd: random.Random) -> str:
    return "".join(rnd.choices(string.ascii_uppercase + string.digits, k=13))


def _key(rnd: random.Random) -> str:
    return "".join(rnd.choices(string.ascii_uppercase + string.digits, k=4))


def seed_trace(db: Session) -> None:
    rnd = random.Random(2026)
    now = datetime.utcnow().replace(microsecond=0)
    today = now.date()

    # --- ishtirokchilar
    for pid, kind, name, tin, region, addr, lic in PARTICIPANTS:
        lat, lon = COORDS.get(pid, (None, None))
        db.add(Participant(id=pid, kind=kind, name=name, tin=tin, region=region, address=addr, license_ok=lic,
                           lat=lat, lon=lon))
    for m in db.query(Manufacturer).filter(Manufacturer.is_local.is_(True)).all():
        db.add(Participant(id=_mfr_participant_id(m.id), kind="manufacturer", name=m.name,
                           region="Oʻzbekiston", license_ok=True))
    db.flush()

    drugs = db.query(Drug).all()
    by_name = {d.trade_name: d for d in drugs}
    importers_ok = [101, 102]

    # --- bojxona deklaratsiyalari: har bir import dori partiyasi uchun qator
    decl_seq = [0]

    def new_decl(importer: int, days_ago: int, origin: str) -> CustomsDeclaration:
        decl_seq[0] += 1
        d = CustomsDeclaration(
            number=f"26001/{(now - timedelta(days=days_ago)):%d%m%y}/{3000 + decl_seq[0]:07d}",
            cleared_at=now - timedelta(days=days_ago), customs_post=rnd.choice(CUSTOMS_POSTS),
            importer_id=importer, origin_country=origin, source="demo")
        db.add(d)
        return d

    import_batches: dict[tuple[int, str], CustomsLine] = {}
    decl_by_origin: dict[str, CustomsDeclaration] = {}
    for d in drugs:
        if d.manufacturer.is_local:
            continue
        origin = d.manufacturer.country
        if origin not in decl_by_origin:
            decl_by_origin[origin] = new_decl(importers_ok[len(decl_by_origin) % 2], rnd.randint(70, 160), origin)
        decl = decl_by_origin[origin]
        for b in range(2):
            batch = f"{d.trade_name[:2].upper()}-{rnd.randint(1000, 9999)}"
            line = CustomsLine(declaration=decl, description=f"{d.inn.upper()} {d.strength.upper()} {d.form.upper()} N{d.pack_size.split()[0]}, {d.trade_name}",
                               gtin=d.gtin, batch=batch, quantity=12, matched_drug_id=d.id, match_method="gtin")
            db.add(line)
            import_batches[(d.id, batch)] = line

    # Muammoli deklaratsiyalar (bojxona panelida AI/qoidalar belgilashi uchun)
    bad = new_decl(103, 12, "Hindiston")  # litsenziyasi yoʻq importyor
    db.add(CustomsLine(declaration=bad, description="CARDIOMAX 10MG TAB N30 (amlodipine besylate)",
                       gtin=UNREGISTERED_GTIN, batch="CX-771", quantity=5000))
    db.add(CustomsLine(declaration=bad, description="METFORMIN HCL 850 MG TABLETS, 30'S, GANGA",
                       gtin="", batch="MG-5521", quantity=2400))
    mismatch = new_decl(101, 9, "Xitoy")
    db.add(CustomsLine(declaration=mismatch, description="ATORVASTATIN 20MG FILM-COATED TABLETS N30 ATORHEIM",
                       gtin=by_name["Atorheim"].gtin, batch="AT-4410", quantity=3600))
    db.flush()

    # --- qutilar va hodisalar
    def add_pack(d: Drug, serial: str, key91: str, batch: str, expiry: date, chain: list, status: str,
                 owner: int | None, customs_line: CustomsLine | None) -> Pack:
        p = Pack(drug_id=d.id, gtin=d.gtin, serial=serial, crypto_tail=key91, batch=batch, expiry=expiry,
                 status=status, owner_id=owner, customs_line_id=customs_line.id if customs_line else None)
        db.add(p)
        db.flush()
        for etype, part, at, doc in chain:
            db.add(PackEvent(pack_id=p.id, type=etype, participant_id=part, at=at, document=doc))
        return p

    def origin_chain(d: Drug, t0: datetime, line: CustomsLine | None, skip_customs: bool = False):
        if d.manufacturer.is_local:
            return [("produced", _mfr_participant_id(d.manufacturer_id), t0, f"ISH-{rnd.randint(10000, 99999)}")]
        if skip_customs:
            return []
        return [("customs_cleared", line.declaration.importer_id, line.declaration.cleared_at, line.declaration.number)]

    def standard_pack(d: Drug, batch: str, line: CustomsLine | None, t0: datetime, expiry: date):
        dist = 202 if rnd.random() < 0.3 else 201
        pharmacy = rnd.choice(PHARMACIES)
        chain = origin_chain(d, t0, line)
        t_dist = t0 + timedelta(days=rnd.randint(2, 6))
        chain.append(("received", dist, t_dist, f"TTN-{rnd.randint(100000, 999999)}"))
        roll = rnd.random()
        if roll < 0.06:
            return add_pack(d, _serial(rnd), _key(rnd), batch, expiry, chain, "in_transit", dist, line)
        t_ph = t_dist + timedelta(days=rnd.randint(2, 8))
        chain.append(("received", pharmacy, t_ph, f"TTN-{rnd.randint(100000, 999999)}"))
        sell_p = 0.2 if pharmacy == BAD_PHARMACY else 0.5
        if roll < 0.06 + sell_p:
            t_sold = min(now - timedelta(hours=3), t_ph + timedelta(days=rnd.randint(1, 50)))
            chain.append(("sold", pharmacy, t_sold, f"CHEK-{rnd.randint(1000000, 9999999)}"))
            return add_pack(d, _serial(rnd), _key(rnd), batch, expiry, chain, "sold", pharmacy, line)
        return add_pack(d, _serial(rnd), _key(rnd), batch, expiry, chain, "at_pharmacy", pharmacy, line)

    for d in drugs:
        lines = [l for (did, _), l in import_batches.items() if did == d.id]
        batches = [(l.batch, l) for l in lines] or [(f"{d.trade_name[:2].upper()}-{rnd.randint(1000, 9999)}", None)
                                                     for _ in range(2)]
        for batch, line in batches:
            t0 = line.declaration.cleared_at if line else now - timedelta(days=rnd.randint(60, 150))
            expiry = today + timedelta(days=rnd.randint(300, 900))
            for _ in range(12):
                standard_pack(d, batch, line, t0, expiry)
            if line:
                line.registered_packs = 12

    # Muomaladan chiqarilgan seriya (sifat ogohlantirishi bor partiya)
    diaform = by_name["Diaform-O"]
    alert = db.query(QualityAlert).filter(QualityAlert.drug_id == diaform.id).first()
    recall_batch = alert.batch if alert else "DF-0423"
    t0 = now - timedelta(days=150)
    for i in range(6):
        chain = origin_chain(diaform, t0, None) + [
            ("received", 201, t0 + timedelta(days=3), "TTN-500100"),
            ("received", 305, t0 + timedelta(days=8), "TTN-500101"),
            ("withdrawn", 305, now - timedelta(days=120), "QAYTARISH-77"),
        ]
        add_pack(diaform, _serial(rnd), _key(rnd), recall_batch, today + timedelta(days=400), chain, "withdrawn", 305, None)

    # --- hakamlar uchun stsenariy qutilari
    def line_for(d: Drug) -> CustomsLine | None:
        return next((l for (did, _), l in import_batches.items() if did == d.id), None)

    def scenario(name, serial, pharmacy, status, sold_days_ago=None, skip_customs=False, batch=None,
                 expiry=None, t0_days=90):
        d = by_name[name]
        line = None if (d.manufacturer.is_local or skip_customs) else line_for(d)
        t0 = line.declaration.cleared_at if line else now - timedelta(days=t0_days)
        chain = origin_chain(d, t0, line, skip_customs=skip_customs)
        t_dist = t0 + timedelta(days=4)
        chain.append(("received", 201, t_dist, "TTN-700001"))
        t_ph = t_dist + timedelta(days=5)
        chain.append(("received", pharmacy, t_ph, "TTN-700002"))
        if status == "sold":
            chain.append(("sold", pharmacy, now - timedelta(days=sold_days_ago), "CHEK-8800123"))
        return add_pack(d, serial, SCENARIO_KEY91, batch or (line.batch if line else "DM-2026"),
                        expiry or today + timedelta(days=500), chain, status, pharmacy, line)

    scenario("Amlozar", "DEMOOK0000001", 301, "at_pharmacy")
    scenario("Norvadin", "DEMOREUSE0001", BAD_PHARMACY, "sold", sold_days_ago=47, t0_days=120)
    clone = scenario("Metgan", "DEMOCLONE0001", 302, "at_pharmacy")
    scenario("Amoxibos", "DEMOGREY00001", 304, "at_pharmacy", skip_customs=True)
    scenario("Diaform-O", "DEMORECALL001", 305, "at_pharmacy", batch=recall_batch)
    scenario("Zartramol", "DEMOQRRX00001", 301, "at_pharmacy")
    scenario("Tumlodip", "DEMONOCHECK01", BAD_PHARMACY, "at_pharmacy")
    reuse_pack = db.query(Pack).filter(Pack.serial == "DEMOREUSE0001").one()
    claimed = scenario("Amlotens", "DEMOCLAIM0001", BAD_PHARMACY, "at_pharmacy")
    scenario("Registan-Losartan", "DEMOOTHER0001", 307, "at_pharmacy")
    scenario("Paralpina", "DEMOEXPIRED01", 305, "at_pharmacy", expiry=today - timedelta(days=62), t0_days=700)
    db.flush()

    # --- xaridor skanerlashlari tarixi
    # Xaridorlar "Sotib oldim" rejimida qayd etgan qutilar (DoriIshonch zanjiri uchun)
    sold_at = next(e.at for e in reuse_pack.events if e.type == "sold")
    db.add(ConsumerScan(pack_id=reuse_pack.id, mode="after", pharmacy_id=BAD_PHARMACY, region="Samarqand",
                        verdict="ok", reasons="", at=sold_at + timedelta(minutes=12), is_demo=True))
    db.add(ConsumerScan(pack_id=claimed.id, mode="after", pharmacy_id=BAD_PHARMACY, region="Samarqand",
                        verdict="warning", reasons="sale_not_registered", at=now - timedelta(days=20), is_demo=True))
    for region, hours in [("Samarqand", 40), ("Fargʻona", 22), ("Andijon", 5)]:
        db.add(ConsumerScan(pack_id=clone.id, raw_code="", mode="before", region=region, verdict="ok",
                            reasons="", at=now - timedelta(hours=hours), is_demo=True))

    # Stsenariy qutilari (DEMO...) tasodifiy tarixga aralashmasin
    all_packs = [p for p in db.query(Pack).all() if not p.serial.startswith("DEMO")]
    sold_bad = [p for p in all_packs if p.status == "sold" and p.owner_id == BAD_PHARMACY]
    regions = {p[0]: p[4] for p in PARTICIPANTS}
    # Bahor dorixonasida qayta ishlatilgan qutilar koʻp aniqlangan
    for p in sold_bad[:9]:
        db.add(ConsumerScan(pack_id=p.id, mode="before", pharmacy_id=BAD_PHARMACY, region="Samarqand",
                            verdict="danger", reasons="already_sold",
                            at=now - timedelta(days=rnd.randint(0, 25), hours=rnd.randint(0, 23)), is_demo=True))
    # Sotuv kassadan oʻtkazilmagan holatlar
    for ph, n in [(BAD_PHARMACY, 6), (SLOPPY_PHARMACY, 5), (304, 1)]:
        stock = [p for p in all_packs if p.status == "at_pharmacy" and p.owner_id == ph]
        for p in stock[:n]:
            db.add(ConsumerScan(pack_id=p.id, mode="after", pharmacy_id=ph, region=regions[ph],
                                verdict="warning", reasons="sale_not_registered",
                                at=now - timedelta(days=rnd.randint(0, 20)), is_demo=True))
    # Oddiy, muammosiz skanerlashlar
    for _ in range(260):
        p = rnd.choice(all_packs)
        ph = p.owner_id if p.owner_id in PHARMACIES else rnd.choice(PHARMACIES)
        if p.status not in ("at_pharmacy", "sold"):
            continue
        db.add(ConsumerScan(pack_id=p.id, mode="before" if p.status == "at_pharmacy" else "after",
                            pharmacy_id=ph, region=regions[ph], verdict="ok", reasons="",
                            at=now - timedelta(days=rnd.randint(0, 29), hours=rnd.randint(0, 23)), is_demo=True))
    db.commit()

    # DoriIshonch zanjiri: barcha demo skanerlashlar vaqt tartibida bloklarga yoziladi
    from .services import ledger

    for sc in db.query(ConsumerScan).order_by(ConsumerScan.at).all():
        p = db.get(Pack, sc.pack_id) if sc.pack_id else None
        if not p:
            continue
        kind = "scan" if sc.mode == "before" else ("disputed" if sc.verdict == "danger" else "purchase")
        ledger.append(db, kind=kind, gtin=p.gtin, serial=p.serial, pharmacy_id=sc.pharmacy_id, region=sc.region,
                      verdict=sc.verdict, device=ledger.device_hash(f"demo-{rnd.random()}"), scan_id=sc.id,
                      at=sc.at, is_demo=True, commit=False)
    db.commit()

    # Bojxona qatorlarini reestrga moslash va tekshirish
    from .services.customs import match_line, revalidate_all

    for line in db.query(CustomsLine).filter(CustomsLine.match_method == "").all():
        d, method, _ = match_line(db, line.description, line.gtin)
        line.matched_drug_id = d.id if d else None
        line.match_method = method
    db.flush()
    revalidate_all(db)


def scenario_codes() -> list[dict]:
    """Demo sahifasi uchun: har bir stsenariyning toʻliq GS1 kodi."""
    return [
        {"key": key, "trade_name": name, "serial": serial, "title": title, "expected": expected,
         "mode": mode, "pharmacy_id": pharmacy}
        for key, name, serial, title, expected, mode, pharmacy in DEMO_SCENARIOS
    ]
