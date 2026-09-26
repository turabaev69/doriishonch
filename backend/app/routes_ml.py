"""Oʻz AI modellarimiz: holat, qadoq surati tekshiruvi, qayta oʻqitish."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .auth import require_role
from .db import get_db
from .ml import learning, packnet, risk_model

router = APIRouter(prefix="/ml")


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Modellar kartasi: versiya, oʻqitish maʼlumoti, sifat koʻrsatkichlari (hakamlar va inspektor uchun)."""
    model = risk_model._model or risk_model.load()
    return {
        "risk": model.card if model else None,
        "packnet": packnet.card(),
        "training": learning.is_training(),
        "labeled_reports": learning.labeled_count(db),
        "retrain_every": learning.RETRAIN_EVERY,
    }


@router.get("/packnet/weights")
def packnet_weights():
    """Qurilmadagi model uchun ogʻirliklar (ilova yangilanmasdan modelni yangilash mumkin)."""
    if not packnet.available():
        raise HTTPException(404, "Model hali oʻqitilmagan")
    return FileResponse(packnet.WEIGHTS, media_type="application/json",
                        headers={"Cache-Control": "public, max-age=3600"})


@router.post("/packnet/check")
async def packnet_check(file: UploadFile = File(...), gtin: str | None = Form(None)):
    """Qadoq suratini serverda tekshirish (Telegram bot va eski qurilmalar uchun). Natija — signal."""
    if not packnet.available():
        raise HTTPException(503, "Qadoq modeli oʻrnatilmagan")
    data = await file.read()
    try:
        return packnet.predict(data, gtin)
    except Exception:  # noqa: BLE001 — buzilgan surat
        raise HTTPException(422, "Surat oʻqilmadi. JPG yoki PNG yuboring.")


@router.post("/retrain", dependencies=[Depends(require_role("inspector"))])
def retrain(db: Session = Depends(get_db)):
    """Skan xavf modelini hozir qayta oʻqitish (simulyatsiya + inspektor tasdiqlagan holatlar)."""
    return risk_model.train(db).card
