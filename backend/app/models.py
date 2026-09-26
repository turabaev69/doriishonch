from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(80))
    is_local: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    drugs: Mapped[list["Drug"]] = relationship(back_populates="manufacturer")
    certificates: Mapped[list["Certificate"]] = relationship(back_populates="manufacturer")


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_name: Mapped[str] = mapped_column(String(200), index=True)
    inn: Mapped[str] = mapped_column(String(200), index=True)  # XNN / taʼsir qiluvchi modda
    strength: Mapped[str] = mapped_column(String(60))  # doza, masalan "5 mg"
    form: Mapped[str] = mapped_column(String(60))  # tabletka, kapsula ...
    atc_group: Mapped[str] = mapped_column(String(120), default="")
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"))
    prescription_only: Mapped[bool] = mapped_column(Boolean, default=True)
    narrow_therapeutic_index: Mapped[bool] = mapped_column(Boolean, default=False)
    price_uzs: Mapped[int] = mapped_column(Integer, default=0)
    pack_size: Mapped[str] = mapped_column(String(60), default="")
    gtin: Mapped[str] = mapped_column(String(20), default="", index=True)
    has_marking: Mapped[bool] = mapped_column(Boolean, default=False)  # Asl Belgisi
    # Berilish tartibi: otc = retseptsiz, rx = retsept bilan, controlled = maxsus (elektron QR retsept)
    dispense_category: Mapped[str] = mapped_column(String(20), default="rx")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="drugs")
    registry_entries: Mapped[list["RegistryEntry"]] = relationship(back_populates="drug")
    quality_alerts: Mapped[list["QualityAlert"]] = relationship(back_populates="drug")
    evidence_docs: Mapped[list["EvidenceDoc"]] = relationship(back_populates="drug")


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"))
    type: Mapped[str] = mapped_column(String(60))  # GMP (milliy), GMP (xorijiy), JSST PQ
    number: Mapped[str] = mapped_column(String(80))
    valid_until: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[date] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="certificates")


class RegistryEntry(Base):
    __tablename__ = "registry_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    registry_number: Mapped[str] = mapped_column(String(80))
    registered_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40))  # amalda, bekor qilingan
    source_url: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[date] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    drug: Mapped[Drug] = relationship(back_populates="registry_entries")


class QualityAlert(Base):
    __tablename__ = "quality_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    batch: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(60))  # sifat nuqsoni, qalbaki
    reported_on: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(500))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    drug: Mapped[Drug] = relationship(back_populates="quality_alerts")


class EvidenceDoc(Base):
    __tablename__ = "evidence_docs"

    id: Mapped[int] = mapped_column(primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    type: Mapped[str] = mapped_column(String(80))  # bioekvivalentlik, eritilish testi
    title: Mapped[str] = mapped_column(String(300))
    provided_by_manufacturer: Mapped[bool] = mapped_column(Boolean, default=True)
    source_url: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[date] = mapped_column(Date)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    drug: Mapped[Drug] = relationship(back_populates="evidence_docs")


class SearchEvent(Base):
    """Anonim foydalanish hodisalari: qidiruv, ochilgan karta, AI savoli."""

    __tablename__ = "search_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # search, view, question, scan
    query: Mapped[str] = mapped_column(Text, default="")
    drug_id: Mapped[int | None] = mapped_column(ForeignKey("drugs.id"), nullable=True)
    topic: Mapped[str] = mapped_column(String(40), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------------------ kuzatuv (track & trace)


class Participant(Base):
    """Taʼminot zanjiri ishtirokchisi: ishlab chiqaruvchi, importyor, distribyutor, dorixona."""

    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # manufacturer, importer, distributor, pharmacy
    name: Mapped[str] = mapped_column(String(200))
    tin: Mapped[str] = mapped_column(String(20), default="")  # STIR
    region: Mapped[str] = mapped_column(String(60), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    license_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    # OpenStreetMap dan olingan haqiqiy dorixonalar uchun
    osm_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lon: Mapped[float | None] = mapped_column(nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class CustomsDeclaration(Base):
    """Bojxona yuk deklaratsiyasi (BYD). Manba: bojxona tizimi adapteri."""

    __tablename__ = "customs_declarations"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(40), unique=True)
    cleared_at: Mapped[datetime] = mapped_column(DateTime)
    customs_post: Mapped[str] = mapped_column(String(120))
    importer_id: Mapped[int] = mapped_column(ForeignKey("participants.id"))
    origin_country: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(40), default="demo")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    importer: Mapped[Participant] = relationship()
    lines: Mapped[list["CustomsLine"]] = relationship(back_populates="declaration", cascade="all, delete-orphan")


class CustomsLine(Base):
    __tablename__ = "customs_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    declaration_id: Mapped[int] = mapped_column(ForeignKey("customs_declarations.id"))
    description: Mapped[str] = mapped_column(String(300))  # deklaratsiyadagi erkin matn
    gtin: Mapped[str] = mapped_column(String(20), default="")
    batch: Mapped[str] = mapped_column(String(40), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    matched_drug_id: Mapped[int | None] = mapped_column(ForeignKey("drugs.id"), nullable=True)
    match_method: Mapped[str] = mapped_column(String(20), default="")  # gtin, fuzzy, ai, none
    registered_packs: Mapped[int] = mapped_column(Integer, default=0)
    flags: Mapped[str] = mapped_column(Text, default="")  # "|" bilan ajratilgan ogohlantirishlar

    declaration: Mapped[CustomsDeclaration] = relationship(back_populates="lines")
    matched_drug: Mapped["Drug | None"] = relationship()


class Pack(Base):
    """Bitta quti: GTIN + seriya raqami (Asl Belgisi DataMatrix)."""

    __tablename__ = "packs"

    id: Mapped[int] = mapped_column(primary_key=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.id"))
    gtin: Mapped[str] = mapped_column(String(14), index=True)
    serial: Mapped[str] = mapped_column(String(20), index=True)
    crypto_tail: Mapped[str] = mapped_column(String(8), default="")  # 91-maydon (tekshiruv kaliti)
    batch: Mapped[str] = mapped_column(String(40))
    expiry: Mapped[date] = mapped_column(Date)
    # emitted, imported, in_transit, at_pharmacy, sold, withdrawn
    status: Mapped[str] = mapped_column(String(20), default="emitted")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"), nullable=True)
    customs_line_id: Mapped[int | None] = mapped_column(ForeignKey("customs_lines.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    drug: Mapped[Drug] = relationship()
    owner: Mapped[Participant | None] = relationship()
    customs_line: Mapped[CustomsLine | None] = relationship()
    events: Mapped[list["PackEvent"]] = relationship(back_populates="pack", order_by="PackEvent.at")


class PackEvent(Base):
    __tablename__ = "pack_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    pack_id: Mapped[int] = mapped_column(ForeignKey("packs.id"), index=True)
    # produced, customs_cleared, shipped, received, sold, withdrawn
    type: Mapped[str] = mapped_column(String(20))
    participant_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime)
    document: Mapped[str] = mapped_column(String(80), default="")  # BYD raqami, chek raqami ...

    pack: Mapped[Pack] = relationship(back_populates="events")
    participant: Mapped[Participant | None] = relationship()


class ConsumerScan(Base):
    """Xaridor skanerlashi. Shaxsiy maʼlumot saqlanmaydi, faqat hudud va natija."""

    __tablename__ = "consumer_scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    pack_id: Mapped[int | None] = mapped_column(ForeignKey("packs.id"), nullable=True, index=True)
    raw_code: Mapped[str] = mapped_column(String(200), default="")
    mode: Mapped[str] = mapped_column(String(10), default="before")  # before, after
    pharmacy_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"), nullable=True)
    region: Mapped[str] = mapped_column(String(60), default="")
    verdict: Mapped[str] = mapped_column(String(20))  # ok, warning, danger
    reasons: Mapped[str] = mapped_column(Text, default="")  # check key lari, "|" bilan
    reported: Mapped[bool] = mapped_column(Boolean, default=False)  # xaridor inspektorga yubordi
    report_note: Mapped[str] = mapped_column(Text, default="")
    report_reason: Mapped[str] = mapped_column(String(30), default="")  # fake, reused, no_effect, packaging, price, other
    report_status: Mapped[str] = mapped_column(String(20), default="")  # "" | yangi | tasdiqlandi | rad_etildi
    price_paid: Mapped[int | None] = mapped_column(Integer, nullable=True)  # xaridor kiritgan narx (soʻm)
    device_hash: Mapped[str] = mapped_column(String(64), default="", index=True)  # ball va bounty uchun
    # Oʻz AI modelimiz: skan paytidagi belgilar (JSON) va xavf bahosi 0–100 (ml/risk_model.py)
    ml_features: Mapped[str] = mapped_column(Text, default="")
    ml_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Skanerlangan joy (ixtiyoriy, ~100 m aniqlikkacha yaxlitlanadi — shaxsiy manzil saqlanmaydi)
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lon: Mapped[float | None] = mapped_column(nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    pack: Mapped[Pack | None] = relationship()
    pharmacy: Mapped[Participant | None] = relationship()


class LedgerBlock(Base):
    """DoriIshonch skanerlashlar zanjiri: har bir yozuv oldingisining hashini oʻz ichiga oladi.

    Bitta yozuv oʻzgartirilsa yoki oʻchirilsa, undan keyingi barcha hashlar mos kelmay qoladi
    (/ledger/verify buni aniqlaydi). Blokcheyndagi kabi, lekin bitta serverda.
    """

    __tablename__ = "ledger_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)  # blok raqami (1 dan)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    kind: Mapped[str] = mapped_column(String(20))  # scan, purchase, report
    gtin: Mapped[str] = mapped_column(String(14), index=True)
    serial: Mapped[str] = mapped_column(String(40), index=True)
    pharmacy_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"), nullable=True)
    region: Mapped[str] = mapped_column(String(60), default="")
    verdict: Mapped[str] = mapped_column(String(20), default="")
    device_hash: Mapped[str] = mapped_column(String(64), default="")  # anonim qurilma belgisi
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("consumer_scans.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    pharmacy: Mapped[Participant | None] = relationship()


class StaffUser(Base):
    """Xodimlar (inspektor, bojxona, ishlab chiqaruvchi). Xaridorlar roʻyxatdan oʻtmaydi."""

    __tablename__ = "staff_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # admin, inspector, customs, manufacturer
    display_name: Mapped[str] = mapped_column(String(120), default="")
    manufacturer_id: Mapped[int | None] = mapped_column(ForeignKey("manufacturers.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class Wallet(Base):
    """Xaridorning anonim ball hamyoni. Faqat qurilma hashi va (ixtiyoriy) taxallus."""

    __tablename__ = "wallets"

    device_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(24), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)  # gʻayrioddiy faollik: ball berilmaydi
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class PointEvent(Base):
    """Ball harakati. status: credited (hisoblangan), pending (inspektor tasdigʻini kutmoqda), rejected."""

    __tablename__ = "point_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_hash: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # scan, pharmacy, purchase, catch, report, mission, redeem, bonus
    points: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="credited")
    gtin: Mapped[str] = mapped_column(String(14), default="")
    serial: Mapped[str] = mapped_column(String(40), default="")
    scan_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    pharmacy_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ref: Mapped[str] = mapped_column(String(60), default="")  # missiya ID, mukofot kaliti va h.k.
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_hash: Mapped[str] = mapped_column(String(64), index=True)
    reward_key: Mapped[str] = mapped_column(String(40))
    points: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CrowdProduct(Base):
    """Bazada (reestrda) yoʻq, lekin xaridorlar skanerlagan mahsulot. Keyin inspektor reestr bilan solishtiradi."""

    __tablename__ = "crowd_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    gtin: Mapped[str] = mapped_column(String(14), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")  # xaridor yozgan nom (ixtiyoriy)
    scans: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_lat: Mapped[float | None] = mapped_column(nullable=True)
    last_lon: Mapped[float | None] = mapped_column(nullable=True)
    last_region: Mapped[str] = mapped_column(String(60), default="")
    last_pharmacy_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"), nullable=True)
    gtin_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    last_pharmacy: Mapped["Participant | None"] = relationship()
