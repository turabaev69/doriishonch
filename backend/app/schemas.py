from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ManufacturerOut(BaseModel):
    id: int
    name: str
    country: str
    is_local: bool
    is_demo: bool


class DrugBrief(BaseModel):
    id: int
    trade_name: str
    inn: str
    strength: str
    form: str
    atc_group: str
    price_uzs: int
    pack_size: str
    prescription_only: bool
    is_demo: bool
    manufacturer: ManufacturerOut


FactStatus = Literal["ok", "warn", "missing", "info"]


class Fact(BaseModel):
    key: str
    label: str
    status: FactStatus
    text: str
    source_url: str | None = None
    updated_at: date | None = None
    provided_by_manufacturer: bool = False
    is_demo: bool = False


class TrustCard(BaseModel):
    drug: DrugBrief
    facts: list[Fact]
    disclaimer: str


class AnalogOut(BaseModel):
    drug: DrugBrief
    price_diff_uzs: int  # manfiy = arzonroq
    price_diff_pct: int
    has_valid_gmp: bool
    quality_alert_count: int
    evidence_count: int


class AnalogsResponse(BaseModel):
    base: DrugBrief
    analogs: list[AnalogOut]
    note: str


class SearchResponse(BaseModel):
    query: str
    results: list[DrugBrief]


class ExplainRequest(BaseModel):
    drug_id: int
    question: str


class ExplainResponse(BaseModel):
    answer: str
    sources: list[Fact]
    blocked: bool = False
    ai_used: bool = False


class ScanResponse(BaseModel):
    extracted: dict
    matches: list[DrugBrief]
    method: str
    note: str = ""


class TopicCount(BaseModel):
    topic: str
    label: str
    count: int


class DrugStat(BaseModel):
    drug: DrugBrief
    views: int
    questions: int


class InsightsResponse(BaseModel):
    manufacturer: ManufacturerOut
    total_views: int
    total_questions: int
    drugs: list[DrugStat]
    topics: list[TopicCount]
    competing_imports: list[AnalogOut]


# ------------------------------------------------------------------ kuzatuv


class ParticipantOut(BaseModel):
    id: int
    kind: str
    name: str
    region: str
    address: str
    license_ok: bool
    is_demo: bool
    lat: float | None = None
    lon: float | None = None


class NearbyPharmacy(BaseModel):
    pharmacy: ParticipantOut
    distance_m: int


class VerifyRequest(BaseModel):
    code: str | None = None
    gtin: str | None = None
    serial: str | None = None
    key91: str | None = None
    mode: Literal["before", "after"] = "before"
    pharmacy_id: int | None = None
    device_id: str | None = None  # brauzerdagi anonim ID (ism/telefon emas)
    price_paid: int | None = Field(default=None, gt=0, le=100_000_000, strict=True)
    lat: float | None = None  # ixtiyoriy: skanerlangan joy (xarita uchun)
    lon: float | None = None


class CheckOut(BaseModel):
    key: str
    status: str
    title: str
    text: str


class ChainEventOut(BaseModel):
    type: str
    label: str
    participant: str
    participant_kind: str
    region: str
    at: datetime
    document: str


class PackOut(BaseModel):
    gtin: str
    serial: str
    batch: str
    expiry: date
    status: str
    status_label: str
    owner: ParticipantOut | None


class DispenseOut(BaseModel):
    category: str
    label: str
    note: str


class VerifyResponse(BaseModel):
    is_demo: bool = False
    verdict: str  # ok, warning, danger, unknown
    headline: str
    explanation: str
    ai_used: bool
    checks: list[CheckOut]
    advice: list[str]
    parsed: dict
    drug: DrugBrief | None
    pack: PackOut | None
    chain: list[ChainEventOut]
    dispense: DispenseOut | None
    scan_id: int | None
    source: str = "local"  # local (demo baza), asl_belgisi yoki crowd
    ledger: "LedgerInfo | None" = None
    reward: dict | None = None  # {earned, pending, messages, total, level}
    places: list[dict] = []  # xarita: sotilgan / tekshirilgan joylar
    new_product: dict | None = None  # reestrda yoʻq mahsulot bazaga qoʻshildi: {gtin, name, scans, is_new}
    ai_risk: dict | None = None  # oʻz modelimiz: {score 0–100, level, reasons[{text, impact}], model}


class PriceRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=200)
    price_paid: int = Field(gt=0, le=100_000_000, strict=True)


class PriceSummary(BaseModel):
    saved_price: int | None
    sample_count: int
    median_price: int | None
    min_price: int | None
    max_price: int | None
    difference_percent: float | None
    period_days: int
    is_demo: bool
    region: str


class ReportRequest(BaseModel):
    scan_id: int
    note: str = ""
    reason: str = ""  # fake, reused, no_effect, packaging, price, other


class DemoCode(BaseModel):
    key: str
    title: str
    expected: str
    mode: str
    pharmacy_id: int | None
    pharmacy_name: str
    trade_name: str
    code: str  # GS ajratgichli toʻliq kod
    code_display: str  # (01)...(21)... koʻrinishi


class CustomsLineOut(BaseModel):
    id: int
    description: str
    gtin: str
    batch: str
    quantity: int
    registered_packs: int
    match_method: str
    drug: DrugBrief | None
    flags: list[str]


class CustomsDeclarationOut(BaseModel):
    id: int
    number: str
    cleared_at: datetime
    customs_post: str
    importer: ParticipantOut
    origin_country: str
    source: str
    is_demo: bool
    lines: list[CustomsLineOut]
    flag_count: int


class PharmacyRiskOut(BaseModel):
    pharmacy: ParticipantOut
    level: str
    anomaly: float
    ml_outlier: bool
    received: int
    sold: int
    sell_through: float
    in_stock: int
    stale: int
    scans: int
    reuse: int
    unregistered: int
    clone: int
    reports: int
    signals: list[str]


class PharmacyRiskDetail(PharmacyRiskOut):
    summary: str
    ai_used: bool


class AlertOut(BaseModel):
    scan_id: int
    at: datetime
    verdict: str
    reasons: list[str]
    mode: str
    region: str
    pharmacy: str
    drug: str
    serial: str
    reported: bool
    report_note: str
    report_reason: str = ""
    report_status: str = ""
    price_paid: int | None = None
    ml_score: int | None = None  # oʻz modelimiz: qalbaki boʻlish ehtimoli 0–100


class LedgerEntryOut(BaseModel):
    index: int
    hash: str
    prev_hash: str
    created_at: datetime
    kind: str
    gtin: str
    serial: str
    pharmacy: str
    region: str
    verdict: str
    is_demo: bool


class LedgerInfo(BaseModel):
    block: LedgerEntryOut | None
    history: list[LedgerEntryOut]  # shu quti boʻyicha (joriy skanerlash bilan)


class ChainStatus(BaseModel):
    ok: bool
    blocks: int
    broken_at: int | None
    reason: str
    last_hash: str


VerifyResponse.model_rebuild()
