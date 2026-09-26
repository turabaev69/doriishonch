"""Dorixonalar boʻyicha xavf signallari (inspektor uchun).

Ikki qatlam:
1. Tushuntiriladigan qoidalar: qayta ishlatilgan qutilar, kassadan oʻtmagan sotuvlar, nusxa kodlar.
2. ML: IsolationForest dorixonalarning xatti-harakat koʻrsatkichlaridan gʻayrioddiylarini topadi
   (masalan, qabul qilingan qutilarga nisbatan rasmiy sotuv juda kam boʻlsa).
Natija — tekshiruvni rejalashtirish uchun signal, qoidabuzarlik isboti emas.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from ..models import ConsumerScan, Pack, PackEvent, Participant

STALE_DAYS = 90
FEATURES = ["sell_through", "stale_ratio", "reuse", "unregistered", "clone", "danger_rate"]


@dataclass
class PharmacyRisk:
    pharmacy: Participant
    received: int = 0
    sold: int = 0
    in_stock: int = 0
    stale: int = 0
    scans: int = 0
    danger_scans: int = 0
    reuse: int = 0
    unregistered: int = 0
    clone: int = 0
    reports: int = 0
    anomaly: float = 0.0
    ml_outlier: bool = False
    level: str = "past"
    signals: list[str] = field(default_factory=list)

    @property
    def sell_through(self) -> float:
        return self.sold / self.received if self.received else 0.0

    @property
    def stale_ratio(self) -> float:
        return self.stale / self.in_stock if self.in_stock else 0.0

    @property
    def danger_rate(self) -> float:
        return self.danger_scans / self.scans if self.scans else 0.0

    def vector(self) -> list[float]:
        return [self.sell_through, self.stale_ratio, self.reuse, self.unregistered, self.clone, self.danger_rate]


def compute(db: Session, now: datetime | None = None) -> list[PharmacyRisk]:
    now = now or datetime.utcnow()
    pharmacies = db.query(Participant).filter(Participant.kind == "pharmacy").order_by(Participant.id).all()
    stats = {p.id: PharmacyRisk(pharmacy=p) for p in pharmacies}

    received_at: dict[int, datetime] = {}
    for e in db.query(PackEvent).filter(PackEvent.type.in_(["received", "sold"])).all():
        if e.participant_id not in stats:
            continue
        if e.type == "received":
            stats[e.participant_id].received += 1
            received_at[e.pack_id] = e.at
        else:
            stats[e.participant_id].sold += 1
    for p in db.query(Pack).filter(Pack.status == "at_pharmacy").all():
        if p.owner_id in stats:
            s = stats[p.owner_id]
            s.in_stock += 1
            if p.id in received_at and now - received_at[p.id] > timedelta(days=STALE_DAYS):
                s.stale += 1

    for sc in db.query(ConsumerScan).filter(ConsumerScan.pharmacy_id.isnot(None)).all():
        s = stats.get(sc.pharmacy_id)
        if not s:
            continue
        reasons = set(filter(None, sc.reasons.split("|")))
        s.scans += 1
        s.danger_scans += sc.verdict == "danger"
        s.reuse += bool(reasons & {"already_sold", "already_claimed", "double_claim"})
        s.unregistered += "sale_not_registered" in reasons
        s.clone += "clone" in reasons
        s.reports += sc.reported

    # Faoliyati yoʻq (masalan, OSM dan endi qoʻshilgan) dorixonalar roʻyxatni toʻldirmasin
    rows = [r for r in stats.values() if r.pharmacy.is_demo or r.scans or r.received]
    if len(rows) >= 4:
        X = np.array([r.vector() for r in rows], dtype=float)
        X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
        model = IsolationForest(n_estimators=300, contamination="auto", random_state=0).fit(X)
        scores = -model.score_samples(X)
        preds = model.predict(X)
        for r, sc, pr in zip(rows, scores, preds):
            r.anomaly = round(float(sc), 3)
            r.ml_outlier = pr == -1

    med_sell = float(np.median([r.sell_through for r in rows if r.received])) if rows else 0
    med_stale = float(np.median([r.stale_ratio for r in rows if r.in_stock])) if rows else 0
    for r in rows:
        if r.reuse:
            r.signals.append(f"{r.reuse} ta skanerlashda oldin sotilgan quti qayta sotuvda aniqlangan")
        if r.unregistered:
            r.signals.append(f"{r.unregistered} ta xarid kassadan oʻtkazilmagan (xaridor xariddan keyin tekshirgan)")
        if r.clone:
            r.signals.append(f"{r.clone} ta skanerlashda nusxa kod belgisi")
        if r.received >= 10 and med_sell and r.sell_through < med_sell * 0.6:
            r.signals.append(f"Rasmiy sotuv ulushi past: {r.sell_through:.0%} (dorixonalar medianasi {med_sell:.0%})")
        if r.in_stock >= 5 and r.stale_ratio > max(0.5, med_stale + 0.15):
            r.signals.append(f"Qoldiqning {r.stale_ratio:.0%} i {STALE_DAYS} kundan beri sotilmagan "
                             f"(dorixonalar medianasi {med_stale:.0%})")
        if r.reports:
            r.signals.append(f"Xaridorlardan {r.reports} ta shikoyat")
        strong = r.reuse >= 3 or r.unregistered >= 3
        if strong or (r.ml_outlier and len(r.signals) >= 2):
            r.level = "yuqori"
        elif r.signals or r.ml_outlier:
            r.level = "oʻrta"
    order = {"yuqori": 0, "oʻrta": 1, "past": 2}
    rows.sort(key=lambda r: (order[r.level], -r.anomaly))
    return rows


def facts_text(r: PharmacyRisk) -> str:
    p = r.pharmacy
    return "\n".join([
        f"Dorixona: {p.name}, {p.region}, {p.address}. Litsenziya: {'amalda' if p.license_ok else 'amalda emas'}.",
        f"Qabul qilingan qutilar: {r.received}; rasmiy sotilgan: {r.sold} ({r.sell_through:.0%}); "
        f"hozir qoldiqda: {r.in_stock}, shundan {STALE_DAYS} kundan eski: {r.stale}.",
        f"Xaridor skanerlashlari: {r.scans}; xavfli natija: {r.danger_scans}; qayta ishlatilgan quti: {r.reuse}; "
        f"kassadan oʻtmagan xarid: {r.unregistered}; nusxa kod: {r.clone}; shikoyatlar: {r.reports}.",
        f"ML gʻayrioddiylik koʻrsatkichi: {r.anomaly} ({'gʻayrioddiy' if r.ml_outlier else 'odatiy'}).",
        "Signallar: " + ("; ".join(r.signals) if r.signals else "yoʻq"),
    ])


def fallback_summary(r: PharmacyRisk) -> str:
    if not r.signals:
        return (f"{r.pharmacy.name} boʻyicha gʻayrioddiy signal yoʻq: {r.scans} ta xaridor skanerlashi, "
                f"rasmiy sotuv ulushi {r.sell_through:.0%}.")
    first = r.signals[0]
    rest = f" Qoʻshimcha: {'; '.join(r.signals[1:])}." if len(r.signals) > 1 else ""
    return (f"{r.pharmacy.name} ({r.pharmacy.region}) xavf darajasi: {r.level}. Asosiy signal: {first}.{rest} "
            "Tekshiruvda qutilar kirim hujjatlari, kassa cheklari va qoldiqni markirovka kodlari bilan "
            "solishtirish tavsiya etiladi.")
