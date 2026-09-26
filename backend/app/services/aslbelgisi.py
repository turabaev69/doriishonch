"""Asl Belgisi (xTrace Open API) ulagichi.

Manba: CRPT Turon, "xTrace: Open API Description", OPEN API v1.45.0 (2026-09-14)
https://help.crpt-turon.uz/hc/en-us/articles/36078638174481-xTrace-Open-API-Description

  Production: https://xtrace.aslbelgisi.uz
  Test:       https://xtrace.stage.aslbelgisi.uz
  Kod maʼlumoti: POST /public/api/cod/public/codes
      {"codes": ["<toʻliq kod, GS = \\u001d>"], "addCodeHistory": true}
  Avtorizatsiya: Authorization: Bearer <API kalit>
      (shaxsiy kabinet → Profil → Tashkilot → Foydalanuvchilar → API kalitlar; 90 kungacha amal qiladi)
  Cheklov: foydalanuvchiga 100 soʻrov (10 gacha kamaytirilishi rejalashtirilgan), bir soʻrovda 1000 tagacha kod.

Diqqat: statuslar va hodisa turlarining toʻliq roʻyxati spetsifikatsiyaning 13.15–13.21 boʻlimlarida.
Quyidagi moslash (STATUS_MAP va SALE_HINTS) ochiq manbadagi qismga asoslangan va haqiqiy API bilan
birinchi ulanishda tekshirilishi kerak. Nomaʼlum status "info" sifatida xom holda koʻrsatiladi.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from ..config import settings

log = logging.getLogger(__name__)

PUBLIC_CODES_PATH = "/public/api/cod/public/codes"

# xTrace status → ichki holat
STATUS_MAP = {
    "EMITTED": "emitted",
    "RECEIVED": "emitted",  # kod olingan, hali qadoqqa/muomalaga kiritilmagan
    "UTILIZED": "emitted",  # qadoqqa tushirilgan, muomalaga kiritilmagan
    "APPLIED": "emitted",
    "INTRODUCED": "in_circulation",
    "WITHDRAWN": "withdrawn",  # muomaladan chiqarilgan: chakana sotuv yoki boshqa sabab
    "RETIRED": "withdrawn",
    "WRITTEN_OFF": "withdrawn",
}
# Muomaladan chiqarish sababi chakana sotuv ekanini bildiruvchi belgilar
SALE_HINTS = ("RETAIL", "SALE", "SOLD", "CASH", "RECEIPT", "FISCAL", "CHEK")
CUSTOMS_HINTS = ("CUSTOMS", "IMPORT", "AIC", "TNVED", "BOJXONA")


@dataclass
class RemoteEvent:
    type: str
    at: datetime | None
    sender_tin: str = ""
    receiver_tin: str = ""
    document_type: str = ""
    document_id: str = ""
    status_after: str = ""
    description: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return " ".join([self.type, self.document_type, self.status_after, str(self.description)]).upper()

    @property
    def is_sale(self) -> bool:
        return any(h in self.text for h in SALE_HINTS)

    @property
    def is_customs(self) -> bool:
        return any(h in self.text for h in CUSTOMS_HINTS)


@dataclass
class RemoteCode:
    code: str
    status: str
    extended_status: str
    internal_status: str
    gtin: str
    series: str
    issuer_tin: str
    issuer_name: str
    emission_date: datetime | None
    issue_date: datetime | None
    production_date: datetime | None
    expiration_date: datetime | None
    history: list[RemoteEvent]
    raw: dict

    @property
    def sale_event(self) -> RemoteEvent | None:
        if self.internal_status != "withdrawn":
            return None
        for e in reversed(self.history):
            if e.is_sale:
                return e
        if any(h in (self.extended_status or "").upper() for h in SALE_HINTS):
            return self.history[-1] if self.history else RemoteEvent(type="WITHDRAWN", at=None)
        return None

    @property
    def customs_event(self) -> RemoteEvent | None:
        return next((e for e in self.history if e.is_customs), None)


def _dt(v) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def parse_code(item: dict) -> RemoteCode:
    issuer = item.get("issuerShortInfo") or {}
    name = issuer.get("issuerName")
    if isinstance(name, dict):  # lokalizatsiyalangan nom: {"uz": ..., "ru": ...}
        name = name.get("uz") or name.get("ru") or next(iter(name.values()), "")
    history = []
    for h in item.get("codeHistory") or []:
        history.append(RemoteEvent(
            type=str(h.get("eventType", "")),
            at=_dt(h.get("eventBusinessDate") or h.get("eventDate")),
            sender_tin=str(h.get("senderTin") or ""),
            receiver_tin=str(h.get("receiverTin") or ""),
            document_type=str(h.get("documentType") or ""),
            document_id=str(h.get("eventSourceId") or ""),
            status_after=str(h.get("eventChangedCodeStatus") or ""),
            description=h.get("eventDescription") or {},
        ))
    history.sort(key=lambda e: e.at or datetime.min)
    status = str(item.get("status") or "").upper()
    return RemoteCode(
        code=item.get("code", ""), status=status, extended_status=str(item.get("extendedStatus") or ""),
        internal_status=STATUS_MAP.get(status, "unknown"), gtin=str(item.get("gtin") or ""),
        series=str(item.get("productSeries") or ""), issuer_tin=str(issuer.get("issuerTin") or ""),
        issuer_name=name or "", emission_date=_dt(item.get("emissionDate")), issue_date=_dt(item.get("issueDate")),
        production_date=_dt(item.get("productionDate")), expiration_date=_dt(item.get("expirationDate")),
        history=history, raw=item,
    )


class AslBelgisiError(Exception):
    pass


class AslBelgisiClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0, transport: httpx.BaseTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout, transport=transport,
                                    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})

    def code_info(self, code: str, history: bool = True) -> RemoteCode | None:
        """Bitta kod boʻyicha maʼlumot. Kod tizimda boʻlmasa None."""
        try:
            r = self._client.post(PUBLIC_CODES_PATH, json={"codes": [code], "addCodeHistory": history})
        except httpx.HTTPError as e:
            raise AslBelgisiError(f"Asl Belgisi bilan aloqa yoʻq: {e}") from e
        if r.status_code in (401, 403):
            raise AslBelgisiError("Asl Belgisi API kaliti notoʻgʻri yoki muddati tugagan")
        if r.status_code == 404:
            return None
        if r.status_code == 429:
            raise AslBelgisiError("Asl Belgisi soʻrovlar limiti tugadi")
        if r.status_code >= 400:
            raise AslBelgisiError(f"Asl Belgisi xatosi {r.status_code}: {r.text[:200]}")
        data = r.json()
        items = data if isinstance(data, list) else (data.get("codes") or data.get("items") or data.get("result") or [])
        for it in items:
            if it.get("errorCode") or it.get("error"):
                continue
            if it.get("status") or it.get("gtin"):
                return parse_code(it)
        return None


_client: AslBelgisiClient | None = None


def get_client() -> AslBelgisiClient | None:
    global _client
    if not settings.asl_belgisi_api_key:
        return None
    if _client is None:
        _client = AslBelgisiClient(settings.asl_belgisi_base_url, settings.asl_belgisi_api_key)
    return _client
