"""AI endpointlari: xaridor yordamchisi, inspektor copiloti, qadoq ekspertizasi."""

import re
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import require_role
from .config import settings
from .db import get_db
from .ml import packnet
from .services import agent, ai, catalog, codes, trace

router = APIRouter(prefix="/ai")


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    pharmacy_id: int | None = None
    device_id: str | None = None
    lat: float | None = None
    lon: float | None = None


class ChatStep(BaseModel):
    tool: str
    input: dict
    summary: str


class ChatResponse(BaseModel):
    answer: str
    steps: list[ChatStep]
    ai_used: bool
    blocked: bool = False


def _msgs(req: ChatRequest) -> list[dict]:
    msgs = [m.model_dump() for m in req.messages if m.role in ("user", "assistant") and m.content.strip()][-12:]
    if not msgs or msgs[-1]["role"] != "user":
        raise HTTPException(400, "Oxirgi xabar foydalanuvchidan boʻlishi kerak")
    return msgs


@router.get("/status")
def status():
    return {"ai_enabled": settings.ai_enabled, "model": settings.anthropic_model if settings.ai_enabled else None,
            "features": ["assistant", "inspector_copilot", "box_inspection", "verdict_explanation",
                         "code_from_photo", "customs_matching", "trust_card_qa", "pharmacy_anomaly_ml"]}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    ctx = {"pharmacy_id": req.pharmacy_id, "device_id": req.device_id, "lat": req.lat, "lon": req.lon}
    return agent.consumer_chat(db, _msgs(req), ctx)


@router.post("/inspector", response_model=ChatResponse, dependencies=[Depends(require_role("inspector"))])
def inspector(req: ChatRequest, db: Session = Depends(get_db)):
    return agent.inspector_chat(db, _msgs(req))


class BoxCheck(BaseModel):
    key: str
    status: str
    title: str
    text: str


class BoxInspection(BaseModel):
    ai_used: bool
    overall: str  # ok, warning, unknown
    summary: str
    checks: list[BoxCheck]
    observed: dict
    model: dict | None = None  # oʻz modelimiz (PackNet) natijasi


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _month(s) -> str:
    m = re.search(r"(\d{4})[-./](\d{1,2})", str(s or ""))
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})[-./](\d{4})", str(s or ""))
    return f"{m.group(2)}-{int(m.group(1)):02d}" if m else ""


@router.post("/inspect-box", response_model=BoxInspection)
async def inspect_box(file: UploadFile = File(...), code: str | None = Form(None), gtin: str | None = Form(None),
                      serial: str | None = Form(None), db: Session = Depends(get_db)):
    """Qadoq suratini AI koʻzdan kechiradi va qutiga bosilgan yozuvlarni kod maʼlumotlari bilan solishtiradi.
    Natija — signal, yakuniy xulosa emas."""
    image = await file.read()
    p = codes.parse(code) if code else codes.ParsedCode(gtin=(gtin or "").zfill(14) if gtin else "", serial=serial or "")
    # 1. Oʻz modelimiz (PackNet): har doim, kalitsiz ishlaydi
    own = None
    if packnet.available():
        try:
            own = packnet.predict(image, p.gtin or None)
        except Exception:  # noqa: BLE001 — surat oʻqilmasa, Claude qismi davom etadi
            own = None
    # 2. Claude: qutidagi yozuvlarni oʻqish (seriya, muddat, nom) — kalit boʻlsa
    if not settings.ai_enabled:
        if own is None:
            raise HTTPException(422, "Surat oʻqilmadi yoki qadoq modeli oʻrnatilmagan.")
        return _own_only(own)
    try:
        obs = ai.inspect_box(image, file.content_type or "image/jpeg") or {}
    except Exception as e:
        if own is not None:
            return _own_only(own)
        raise HTTPException(502, f"AI xizmatida xato: {e}")

    expected: dict = {}
    if p.gtin:
        drug = catalog.find_by_gtin(db, p.gtin)
        pack = trace.load_pack(db, p.gtin, p.serial) if p.serial else None
        expected = {"trade_name": drug.trade_name if drug else None,
                    "batch": (pack.batch if pack else p.batch) or None,
                    "expiry": (pack.expiry if pack else p.expiry)}

    checks: list[BoxCheck] = []
    for sign in obs.get("tamper_signs") or []:
        checks.append(BoxCheck(key="tamper", status="warning", title="Ochilganlik belgisi", text=str(sign)))
    for issue in obs.get("print_issues") or []:
        checks.append(BoxCheck(key="print", status="warning", title="Bosma sifati", text=str(issue)))
    if expected.get("batch") and obs.get("printed_batch"):
        same = _norm(expected["batch"]) == _norm(obs["printed_batch"])
        checks.append(BoxCheck(key="batch", status="ok" if same else "warning", title="Seriya (partiya)",
                               text=(f"Qutidagi seriya {obs['printed_batch']} kod maʼlumotiga mos." if same else
                                     f"Qutiga {obs['printed_batch']} bosilgan, kod boʻyicha esa {expected['batch']}. "
                                     "Quti boshqa partiyadan boʻlishi yoki qayta ishlatilgan boʻlishi mumkin.")))
    if expected.get("expiry") and obs.get("printed_expiry"):
        exp: date = expected["expiry"]
        same = _month(obs["printed_expiry"]) == f"{exp:%Y-%m}"
        checks.append(BoxCheck(key="expiry", status="ok" if same else "warning", title="Yaroqlilik muddati",
                               text=(f"Qutidagi muddat ({obs['printed_expiry']}) kod bilan mos." if same else
                                     f"Qutida {obs['printed_expiry']}, kod boʻyicha {exp:%m.%Y}. Mos emas.")))
    if expected.get("trade_name") and obs.get("printed_trade_name"):
        same = _norm(expected["trade_name"]) in _norm(obs["printed_trade_name"]) or \
            _norm(obs["printed_trade_name"]) in _norm(expected["trade_name"])
        checks.append(BoxCheck(key="name", status="ok" if same else "warning", title="Savdo nomi",
                               text=(f"Qutidagi nom kod boʻyicha dori ({expected['trade_name']}) bilan mos." if same else
                                     f"Qutida \"{obs['printed_trade_name']}\", kod esa {expected['trade_name']} ga tegishli.")))
    if own and own["verdict"] in ("farq", "boshqa"):
        checks.insert(0, BoxCheck(key="packnet", status="warning", title=own["title"], text=own["text"]))
    elif own and own["verdict"] == "asl":
        checks.insert(0, BoxCheck(key="packnet", status="ok", title=own["title"], text=own["text"]))
    quality = str(obs.get("image_quality", "")).lower()
    if quality.startswith("yomon"):
        overall = "unknown"
    else:
        overall = "warning" if any(c.status == "warning" for c in checks) else "ok"
    summary = obs.get("summary_uz") or ("Shubhali belgi topilmadi." if overall == "ok" else "Shubhali belgilar bor.")
    return BoxInspection(ai_used=True, overall=overall, summary=summary, checks=checks, observed=obs, model=own)


def _own_only(own: dict) -> BoxInspection:
    status = {"asl": "ok", "farq": "warning", "boshqa": "warning"}.get(own["verdict"], "unknown")
    return BoxInspection(ai_used=False, overall=status, summary=own["text"],
                         checks=[BoxCheck(key="packnet", status=status, title=own["title"], text=own["text"])],
                         observed={}, model=own)
