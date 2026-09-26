"""Model oʻrganish sikli: inspektor tasdiqlari → qayta oʻqitish.

Har RETRAIN_EVERY ta yangi hal qilingan xabardan keyin skan xavf modeli fonda qayta oʻqitiladi.
Ishga tushishda model diskdan yuklanadi yoki (yoʻq boʻlsa) fonda oʻqitiladi.
"""

from __future__ import annotations

import logging
import threading

from sqlalchemy.orm import Session

from ..models import ConsumerScan
from . import risk_model

log = logging.getLogger(__name__)
RETRAIN_EVERY = 10
_busy = threading.Lock()


def labeled_count(db: Session) -> int:
    return (db.query(ConsumerScan)
            .filter(ConsumerScan.report_status.in_(["tasdiqlandi", "rad_etildi"]), ConsumerScan.ml_features != "")
            .count())


def _train_bg() -> None:
    if not _busy.acquire(blocking=False):
        return
    try:
        from ..db import SessionLocal

        db = SessionLocal()
        try:
            risk_model.train(db)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        log.exception("Fonda qayta oʻqitish xatosi")
    finally:
        _busy.release()


def maybe_retrain(db: Session) -> bool:
    model = risk_model._model or risk_model.load()
    used = model.card.get("n_real", 0) if model else 0
    if labeled_count(db) - used >= RETRAIN_EVERY:
        threading.Thread(target=_train_bg, daemon=True).start()
        return True
    return False


def warmup() -> None:
    """Server ishga tushganda: modelni yuklash yoki fonda oʻqitish (soʻrovlarni kutdirmaslik uchun)."""
    m = risk_model.load()
    if m is not None:
        with risk_model._lock:
            risk_model._model = m
        return
    threading.Thread(target=_train_bg, daemon=True).start()


def is_training() -> bool:
    return _busy.locked()


def backfill(db: Session, limit: int = 2000) -> int:
    """Demo (seed) skanlar uchun belgilar va AI bahosini hisoblash — inspektor navbati birinchi kundan toʻla boʻlsin."""
    import json

    from ..models import Drug, Pack, Participant
    from .risk_features import compute

    scans = (db.query(ConsumerScan).filter(ConsumerScan.ml_features == "", ConsumerScan.pack_id.isnot(None))
             .order_by(ConsumerScan.at).limit(limit).all())
    if not scans:
        return 0
    model = risk_model.get(db)
    feats = []
    for sc in scans:
        pack = db.get(Pack, sc.pack_id)
        drug = db.get(Drug, pack.drug_id) if pack else None
        ph = db.get(Participant, sc.pharmacy_id) if sc.pharmacy_id else None
        f = compute(db, set(filter(None, sc.reasons.split("|"))), pack, ph, sc.price_paid,
                    drug.price_uzs if drug else None,
                    (not drug.manufacturer.is_local) if drug else None, sc.mode, sc.at, exclude_id=sc.id)
        sc.ml_features = json.dumps(f)
        feats.append(f)
    for sc, score in zip(scans, model.scores(feats)):
        sc.ml_score = score
    db.commit()
    log.info("AI bahosi %d ta demo skan uchun hisoblandi", len(scans))
    return len(scans)
