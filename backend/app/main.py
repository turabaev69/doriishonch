from collections import Counter
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Drug, Manufacturer, SearchEvent
from .schemas import (
    AnalogsResponse, DrugStat, ExplainRequest, ExplainResponse, InsightsResponse, ManufacturerOut,
    ScanResponse, SearchResponse, TopicCount, TrustCard,
)
from .auth import require_role
from .auth import router as auth_router
from .routes_ai import router as ai_router
from .routes_map import router as map_router
from .routes_ml import router as ml_router
from .routes_rewards import router as rewards_router
from .routes_trace import router as trace_router
from .security import SecurityMiddleware, check_production_config
from .seed import init_db
from .services import ai, catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_production_config()
    init_db(seed_if_empty=settings.seed_on_startup)
    from .ml import learning

    learning.warmup()  # skan xavf modeli: diskdan yuklash yoki fonda oʻqitish
    yield


app = FastAPI(title="DoriIshonch AI", version="1.0.0", lifespan=lifespan,
              docs_url=None if settings.is_production else "/docs",
              redoc_url=None, openapi_url=None if settings.is_production else "/openapi.json")
app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(trace_router)
app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(rewards_router)
app.include_router(ml_router)
app.include_router(map_router)


def _log(db: Session, kind: str, query: str = "", drug_id: int | None = None, topic: str = ""):
    # Anonim: foydalanuvchi haqida hech qanday maʼlumot saqlanmaydi.
    db.add(SearchEvent(kind=kind, query=query[:300], drug_id=drug_id, topic=topic))
    db.commit()


def _drug_or_404(db: Session, drug_id: int) -> Drug:
    d = catalog.get_drug(db, drug_id)
    if not d:
        raise HTTPException(404, "Dori topilmadi")
    return d


@app.get("/health")
def health():
    return {"status": "ok", "ai_enabled": settings.ai_enabled,
            "asl_belgisi": bool(settings.asl_belgisi_api_key), "customs_api": bool(settings.customs_api_url)}


@app.get("/search", response_model=SearchResponse)
def search(q: str, db: Session = Depends(get_db)):
    results = catalog.search(db, q)
    _log(db, "search", q, results[0].id if results else None)
    return SearchResponse(query=q, results=[catalog.to_brief(d) for d in results])


@app.get("/drugs/{drug_id}", response_model=TrustCard)
def drug_card(drug_id: int, db: Session = Depends(get_db)):
    d = _drug_or_404(db, drug_id)
    _log(db, "view", drug_id=d.id)
    return catalog.trust_card(d)


@app.get("/drugs/{drug_id}/analogs", response_model=AnalogsResponse)
def drug_analogs(drug_id: int, db: Session = Depends(get_db)):
    d = _drug_or_404(db, drug_id)
    note = "Analog = taʼsir qiluvchi modda, doza va dori shakli toʻliq mos preparat."
    if d.narrow_therapeutic_index:
        note += " Bu dori tor terapevtik indeksli: almashtirish faqat shifokor nazoratida."
    return AnalogsResponse(base=catalog.to_brief(d), analogs=catalog.analogs(db, d), note=note)


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest, db: Session = Depends(get_db)):
    d = _drug_or_404(db, req.drug_id)
    if not req.question.strip():
        raise HTTPException(400, "Savol boʻsh")
    res = ai.explain(d, catalog.trust_facts(d), req.question)
    _log(db, "question", req.question, d.id, res["topic"])
    return ExplainResponse(answer=res["answer"], sources=res["sources"],
                           blocked=res["blocked"], ai_used=res["ai_used"])


@app.post("/scan", response_model=ScanResponse)
async def scan(
    file: UploadFile | None = File(default=None),
    code: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Qadoq surati yoki markirovka kodi matnidan dorini aniqlaydi."""
    # 1) Markirovka kodi matn sifatida kiritilgan
    raw_code = code
    image = await file.read() if file else None
    # 2) Suratdagi DataMatrix (pylibdmtx boʻlsa)
    if not raw_code and image:
        raw_code = ai.decode_datamatrix(image)
    if raw_code:
        gtin = ai.parse_marking_code(raw_code)
        hit = catalog.find_by_gtin(db, gtin) if gtin else None
        if hit:
            _log(db, "scan", raw_code, hit.id)
            return ScanResponse(extracted={"gtin": gtin}, matches=[catalog.to_brief(hit)], method="datamatrix")
        if not image:
            return ScanResponse(extracted={"gtin": gtin}, matches=[], method="datamatrix",
                                note="Bu kod bazadagi dorilarga mos kelmadi.")
    # 3) Claude vision
    if image:
        data = ai.extract_from_image(image, file.content_type or "image/jpeg")
        if data is None:
            return ScanResponse(extracted={}, matches=[], method="none",
                                note="Surat tanish uchun ANTHROPIC_API_KEY kerak. Dori nomini qoʻlda yozing.")
        q = data.get("trade_name") or data.get("inn") or ""
        matches = catalog.search(db, q) if q else []
        if not matches and data.get("inn"):
            matches = catalog.search(db, data["inn"])
        _log(db, "scan", q, matches[0].id if matches else None)
        return ScanResponse(extracted=data, matches=[catalog.to_brief(m) for m in matches], method="vision",
                            note="" if matches else "Qadoqdagi dori bazada topilmadi.")
    raise HTTPException(400, "Surat yoki markirovka kodi yuboring")


@app.get("/manufacturers", response_model=list[ManufacturerOut])
def manufacturers(db: Session = Depends(get_db)):
    ms = db.query(Manufacturer).all()
    ms.sort(key=lambda m: (not m.is_local, -len(m.drugs), m.name))
    return [ManufacturerOut(id=m.id, name=m.name, country=m.country, is_local=m.is_local, is_demo=m.is_demo)
            for m in ms]


@app.get("/manufacturers/{mid}/insights", response_model=InsightsResponse)
def insights(mid: int, db: Session = Depends(get_db),
             user: dict = Depends(require_role("manufacturer", "inspector"))):
    if user["r"] == "manufacturer" and user.get("m") != mid:
        raise HTTPException(403, "Faqat oʻz kompaniyangiz maʼlumotlari")
    """Ishlab chiqaruvchi paneli: qiziqish va shubha mavzulari (anonim, agregat)."""
    m = db.get(Manufacturer, mid)
    if not m:
        raise HTTPException(404, "Ishlab chiqaruvchi topilmadi")
    drug_ids = [d.id for d in m.drugs]
    events = db.query(SearchEvent).filter(SearchEvent.drug_id.in_(drug_ids)).all() if drug_ids else []
    views = Counter(e.drug_id for e in events if e.kind == "view")
    questions = Counter(e.drug_id for e in events if e.kind == "question")
    topics = Counter(e.topic for e in events if e.kind == "question" and e.topic)

    stats = [DrugStat(drug=catalog.to_brief(catalog.get_drug(db, i)), views=views[i], questions=questions[i])
             for i in drug_ids]
    stats.sort(key=lambda s: -s.views)

    competing = []
    seen = set()
    for i in drug_ids:
        for a in catalog.analogs(db, catalog.get_drug(db, i)):
            if not a.drug.manufacturer.is_local and a.drug.id not in seen:
                seen.add(a.drug.id)
                competing.append(a)

    return InsightsResponse(
        manufacturer=ManufacturerOut(id=m.id, name=m.name, country=m.country, is_local=m.is_local, is_demo=m.is_demo),
        total_views=sum(views.values()),
        total_questions=sum(questions.values()),
        drugs=stats,
        topics=[TopicCount(topic=t, label=ai.TOPICS.get(t, t), count=c) for t, c in topics.most_common()],
        competing_imports=competing,
    )
