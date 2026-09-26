"""Skan xavf modeli uchun belgilar (features).

Belgilar skanerlash paytida hisoblanadi va ConsumerScan.ml_features da saqlanadi — keyin inspektor tasdigʻi
bilan birga oʻqitish maʼlumotiga aylanadi (kelajakdagi maʼlumot "oqib kirmaydi").
Nomaʼlum qiymat = NaN (gradient boosting uni oʻzi qayta ishlaydi).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import ConsumerScan, Pack, Participant

NAN = float("nan")

# Qoidalar natijasidan olinadigan bayroqlar: check key → guruh
FLAG_GROUPS = {
    "f_reused": {"already_sold", "already_claimed", "double_claim"},
    "f_code_fake": {"serial_unknown", "key_mismatch", "bad_gtin", "unregistered"},
    "f_clone": {"clone"},
    "f_no_customs": {"no_customs", "importer_license"},
    "f_unreg_sale": {"sale_not_registered"},
    "f_chain_gap": {"other_owner", "not_delivered", "sold_elsewhere", "not_introduced"},
    "f_recall": {"withdrawn", "batch_alert", "expired"},
}

FEATURES = [
    *FLAG_GROUPS,
    "box_scans_30d",     # shu quti oldin necha marta skanerlangan
    "box_devices_30d",   # nechta turli qurilma
    "box_regions_3d",    # oxirgi 3 kunda nechta viloyat
    "price_ratio",       # toʻlangan narx / reestr narxi
    "ph_bad_rate",       # dorixonadagi shubhali skanlar ulushi (silliqlangan)
    "ph_confirmed",      # dorixona boʻyicha inspektor tasdiqlagan xabarlar
    "ph_license_bad",
    "batch_bad_rate",    # shu partiyadagi shubhali skanlar ulushi (silliqlangan)
    "batch_reports",     # shu partiya boʻyicha xaridor xabarlari
    "drug_price_log",    # log10(reestr narxi) — qimmat dorilar koʻproq qalbakilashtiriladi
    "drug_import",
    "days_on_shelf",     # dorixonaga kelganidan beri kun
    "days_to_expiry",
    "night",             # mahalliy vaqt 22:00–06:00
    "mode_after",
]

# Monotonlik: bu belgi oshsa, xavf kamaymasligi kerak (+1) / oshmasligi kerak (-1)
MONOTONIC = {**{f: 1 for f in FLAG_GROUPS}, "box_scans_30d": 1, "box_devices_30d": 1, "box_regions_3d": 1,
             "price_ratio": -1, "ph_bad_rate": 1, "ph_confirmed": 1, "ph_license_bad": 1,
             "batch_bad_rate": 1, "batch_reports": 1}

# Dorixona/partiya boʻyicha silliqlash (Bayes): kam maʼlumotda umumiy oʻrtachaga yaqin
PH_PRIOR, PH_WEIGHT = 0.05, 10
BATCH_PRIOR, BATCH_WEIGHT = 0.04, 8
BAD_VERDICTS = ("warning", "danger")


def smoothed(bad: int, n: int, prior: float, weight: int) -> float:
    return (bad + prior * weight) / (n + weight)


def compute(db: Session, check_keys: set[str], pack: Pack | None, pharmacy: Participant | None,
            price_paid: int | None, drug_price: int | None, drug_import: bool | None, mode: str,
            now: datetime, exclude_id: int | None = None) -> dict[str, float]:
    """Joriy skanerlash uchun belgilar. Joriy skan hali bazaga yozilmagan boʻlishi kerak."""
    f: dict[str, float] = {k: float(bool(check_keys & keys)) for k, keys in FLAG_GROUPS.items()}

    if pack is not None:
        prior = [s for s in db.query(ConsumerScan).filter(ConsumerScan.pack_id == pack.id,
                                                          ConsumerScan.at >= now - timedelta(days=30),
                                                          ConsumerScan.at <= now).all() if s.id != exclude_id]
        f["box_scans_30d"] = float(len(prior))
        f["box_devices_30d"] = float(len({s.device_hash for s in prior if s.device_hash}))
        regions = {s.region for s in prior if s.region and s.at >= now - timedelta(days=3)}
        if pharmacy and pharmacy.region:
            regions.add(pharmacy.region)
        f["box_regions_3d"] = float(len(regions))
        received = next((e for e in reversed(pack.events) if e.type == "received"), None)
        f["days_on_shelf"] = float((now - received.at).days) if received else NAN
        f["days_to_expiry"] = float(max(-365, min(1500, (pack.expiry - now.date()).days)))
        # Partiya
        q = (db.query(ConsumerScan.verdict, func.count())
             .join(Pack, Pack.id == ConsumerScan.pack_id)
             .filter(Pack.drug_id == pack.drug_id, Pack.batch == pack.batch, ConsumerScan.at <= now)
             .group_by(ConsumerScan.verdict).all())
        n = sum(c for _, c in q)
        bad = sum(c for v, c in q if v in BAD_VERDICTS)
        f["batch_bad_rate"] = smoothed(bad, n, BATCH_PRIOR, BATCH_WEIGHT)
        f["batch_reports"] = float(db.query(func.count(ConsumerScan.id)).join(Pack, Pack.id == ConsumerScan.pack_id)
                                   .filter(Pack.drug_id == pack.drug_id, Pack.batch == pack.batch,
                                           ConsumerScan.reported.is_(True)).scalar() or 0)
    else:
        for k in ("box_scans_30d", "box_devices_30d", "box_regions_3d", "days_on_shelf", "days_to_expiry",
                  "batch_bad_rate", "batch_reports"):
            f[k] = NAN

    if pharmacy is not None:
        since = now - timedelta(days=90)
        q = (db.query(ConsumerScan.verdict, func.count())
             .filter(ConsumerScan.pharmacy_id == pharmacy.id, ConsumerScan.at >= since, ConsumerScan.at <= now)
             .group_by(ConsumerScan.verdict).all())
        n = sum(c for _, c in q)
        bad = sum(c for v, c in q if v in BAD_VERDICTS)
        f["ph_bad_rate"] = smoothed(bad, n, PH_PRIOR, PH_WEIGHT)
        f["ph_confirmed"] = float(db.query(func.count(ConsumerScan.id))
                                  .filter(ConsumerScan.pharmacy_id == pharmacy.id,
                                          ConsumerScan.report_status == "tasdiqlandi").scalar() or 0)
        f["ph_license_bad"] = float(not pharmacy.license_ok)
    else:
        f["ph_bad_rate"] = f["ph_confirmed"] = f["ph_license_bad"] = NAN

    f["price_ratio"] = (price_paid / drug_price) if price_paid and drug_price else NAN
    f["drug_price_log"] = math.log10(drug_price) if drug_price else NAN
    f["drug_import"] = NAN if drug_import is None else float(drug_import)
    hour = (now.hour + 5) % 24  # Toshkent vaqti
    f["night"] = float(hour >= 22 or hour < 6)
    f["mode_after"] = float(mode == "after")
    return {k: f[k] for k in FEATURES}


def to_row(f: dict) -> list[float]:
    return [NAN if f.get(k) is None else float(f[k]) for k in FEATURES]
