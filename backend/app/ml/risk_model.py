"""Skan xavf modeli: HistGradientBoosting + monotonlik cheklovlari + tushuntirish.

- Oʻqitish: simulyatsiya (risk_synth) + inspektor tasdiqlagan haqiqiy holatlar (vazn REAL_WEIGHT).
- Natija: 0–100 ball, daraja (past / oʻrta / yuqori) va oddiy tildagi sabablar.
- Tushuntirish: har bir belgi guruhini "neytral" qiymatga almashtirib, ehtimol qanchaga tushishini
  oʻlchaymiz (occlusion). Sabab sifatida faqat xavfni sezilarli oshirgan belgilar koʻrsatiladi.
- Xulosani qoidalar chiqaradi; bu model faqat qoʻshimcha signal beradi va inspektor navbatini tartiblaydi.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from ..config import settings
from . import risk_synth
from .risk_features import FEATURES, FLAG_GROUPS, MONOTONIC, NAN, to_row

log = logging.getLogger(__name__)

VERSION = "risk-v1"
REAL_WEIGHT = 25.0  # bitta tasdiqlangan haqiqiy holat ~25 ta simulyatsiya qatoriga teng
MIN_REAL_FOR_EVAL = 20
LEVELS = [(50, "yuqori"), (20, "oʻrta"), (0, "past")]
MIN_DELTA = 0.03  # sabab sifatida koʻrsatish uchun ehtimolga minimal taʼsir

# Neytral qiymat — "bu belgi boʻlmaganida" holati
NEUTRAL = {**{k: 0.0 for k in FLAG_GROUPS}, "box_scans_30d": 0.0, "box_devices_30d": 0.0, "box_regions_3d": 1.0,
           "price_ratio": 1.0, "ph_bad_rate": 0.04, "ph_confirmed": 0.0, "ph_license_bad": 0.0,
           "batch_bad_rate": 0.035, "batch_reports": 0.0, "days_on_shelf": 30.0, "night": 0.0}

# Kod topilmasa, qutiga bogʻliq belgilar NaN boʻladi — "kod toʻgʻri boʻlganida" ular neytral qiymat oladi
PACK_DERIVED = ["box_scans_30d", "box_devices_30d", "box_regions_3d", "batch_bad_rate", "batch_reports",
                "days_on_shelf", "days_to_expiry"]
FILL_NAN = {**NEUTRAL, "days_to_expiry": 500.0}

# Tushuntirish guruhlari → oddiy tildagi sabab (xaridor uchun)
REASONS = [
    (["f_reused"], "Quti oldin sotilgan deb qayd etilgan"),
    (["f_code_fake", *PACK_DERIVED], "Kod rasmiy yozuvga mos emas"),
    (["f_clone", "box_regions_3d"], "Bir xil kod turli joylarda skanerlangan"),
    (["box_scans_30d", "box_devices_30d"], "Bu quti oxirgi oyda koʻp marta tekshirilgan"),
    (["f_no_customs"], "Bojxonadan oʻtgani koʻrinmaydi"),
    (["f_unreg_sale"], "Sotuv qaydi topilmadi"),
    (["f_chain_gap"], "Qutining rasmiy yoʻlida uzilish bor"),
    (["f_recall"], "Partiya yoki muddat boʻyicha ogohlantirish bor"),
    (["price_ratio"], "Narx odatdagidan ancha arzon"),
    (["ph_bad_rate", "ph_confirmed", "ph_license_bad"], "Shu dorixonadagi oldingi tekshiruvlarda muammolar koʻproq uchragan"),
    (["batch_bad_rate", "batch_reports"], "Shu partiya boʻyicha shubhali tekshiruvlar koʻp"),
    (["days_on_shelf"], "Quti dorixonada juda uzoq turgan"),
    (["night"], "Tungi vaqtdagi xarid"),
]


def _path() -> Path:
    p = Path(settings.ml_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class RiskModel:
    clf: HistGradientBoostingClassifier
    card: dict = field(default_factory=dict)

    def proba(self, rows: np.ndarray) -> np.ndarray:
        return self.clf.predict_proba(rows)[:, 1]

    def scores(self, many: list[dict]) -> list[int]:
        """Koʻp skan uchun faqat ball (tushuntirishsiz) — bitta hisob bilan."""
        if not many:
            return []
        return [round(float(p) * 100) for p in self.proba(np.array([to_row(f) for f in many], dtype=float))]

    def score(self, features: dict) -> dict:
        x = np.array([to_row(features)], dtype=float)
        p = float(self.proba(x)[0])
        # Occlusion: har bir guruhni neytrallab koʻramiz (bitta batch bilan)
        variants, groups = [], []
        for cols, text in REASONS:
            v = x[0].copy()
            changed = False
            fill = cols[0] == "f_code_fake"
            if fill and not x[0][FEATURES.index("f_code_fake")]:
                continue
            for c in cols:
                i = FEATURES.index(c)
                cur, neu = v[i], FILL_NAN[c]
                if math.isnan(cur):
                    if fill:
                        v[i] = neu
                    continue
                if cur != neu and (c in NEUTRAL):
                    v[i] = neu
                    changed = True
            if changed:
                variants.append(v)
                groups.append(text)
        reasons = []
        if variants:
            ps = self.proba(np.array(variants))
            deltas = sorted(((p - q, t) for q, t in zip(ps, groups)), reverse=True)
            reasons = [{"text": t, "impact": round(d * 100)} for d, t in deltas if d >= MIN_DELTA][:3]
        score = round(p * 100)
        level = next(name for cut, name in LEVELS if score >= cut)
        return {"score": score, "level": level, "reasons": reasons, "model": self.card.get("version", VERSION)}


_lock = threading.Lock()
_model: RiskModel | None = None


def real_labeled(db) -> tuple[np.ndarray, np.ndarray]:
    """Inspektor hal qilgan xabarlar: tasdiqlandi = 1, rad etildi = 0 (skan paytidagi belgilar bilan)."""
    from ..models import ConsumerScan

    rows, ys = [], []
    for s in db.query(ConsumerScan).filter(ConsumerScan.report_status.in_(["tasdiqlandi", "rad_etildi"]),
                                           ConsumerScan.ml_features != "").all():
        try:
            f = json.loads(s.ml_features)
        except ValueError:
            continue
        rows.append(to_row(f))
        ys.append(int(s.report_status == "tasdiqlandi"))
    if not rows:
        return np.empty((0, len(FEATURES))), np.empty(0, dtype=int)
    return np.array(rows, dtype=float), np.array(ys, dtype=int)


def _rules_baseline(X: np.ndarray) -> np.ndarray:
    """Taqqoslash uchun: faqat qoidalar (bayroqlar soni)."""
    idx = [FEATURES.index(k) for k in FLAG_GROUPS]
    return np.nansum(X[:, idx], axis=1)


def train(db=None, n_synth: int = 24000, seed: int = 7, save: bool = True) -> RiskModel:
    Xs, ys = risk_synth.generate(n_synth, seed)
    Xr, yr = real_labeled(db) if db is not None else (np.empty((0, len(FEATURES))), np.empty(0, dtype=int))
    Xtr, Xte, ytr, yte = train_test_split(Xs, ys, test_size=0.2, random_state=seed, stratify=ys)
    X = np.vstack([Xtr, Xr]) if len(Xr) else Xtr
    y = np.concatenate([ytr, yr]) if len(yr) else ytr
    w = np.concatenate([np.ones(len(ytr)), np.full(len(yr), REAL_WEIGHT)]) if len(yr) else np.ones(len(ytr))
    clf = HistGradientBoostingClassifier(
        max_iter=250, learning_rate=0.07, max_leaf_nodes=24, min_samples_leaf=30, l2_regularization=1.0,
        monotonic_cst=[MONOTONIC.get(f, 0) for f in FEATURES], random_state=seed)
    clf.fit(X, y, sample_weight=w)
    p = clf.predict_proba(Xte)[:, 1]
    metrics = {
        "synthetic_holdout": {
            "n": int(len(yte)), "positives": int(yte.sum()),
            "roc_auc": round(float(roc_auc_score(yte, p)), 3),
            "pr_auc": round(float(average_precision_score(yte, p)), 3),
            "brier": round(float(brier_score_loss(yte, p)), 4),
            "rules_only_roc_auc": round(float(roc_auc_score(yte, _rules_baseline(Xte))), 3),
            "rules_only_pr_auc": round(float(average_precision_score(yte, _rules_baseline(Xte))), 3),
        },
        "real_labeled": {"n": int(len(yr)), "positives": int(yr.sum()) if len(yr) else 0},
    }
    if len(yr) >= MIN_REAL_FOR_EVAL and 0 < yr.sum() < len(yr):
        pr = clf.predict_proba(Xr)[:, 1]  # oʻqitishda qatnashgan — optimistik baho, faqat kuzatish uchun
        metrics["real_labeled"]["roc_auc_in_sample"] = round(float(roc_auc_score(yr, pr)), 3)
    card = {
        "version": VERSION, "trained_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "algorithm": "HistGradientBoostingClassifier (monotonlik cheklovlari bilan)",
        "features": FEATURES, "n_synthetic": int(len(ytr)), "n_real": int(len(yr)),
        "metrics": metrics,
        "notes": ("Simulyatsiyada oldindan oʻqitilgan; inspektor tasdiqlagan har bir haqiqiy holat qayta "
                  "oʻqitishda katta vazn bilan qoʻshiladi. Xulosani qoidalar chiqaradi, model — signal."),
    }
    model = RiskModel(clf, card)
    if save:
        d = _path()
        joblib.dump(clf, d / f"{VERSION}.joblib")
        (d / f"{VERSION}.card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2))
    global _model
    with _lock:
        _model = model
    log.info("Skan xavf modeli oʻqitildi: AUC %.3f (faqat qoidalar %.3f), haqiqiy yorliqlar: %d",
             metrics["synthetic_holdout"]["roc_auc"], metrics["synthetic_holdout"]["rules_only_roc_auc"], len(yr))
    return model


def load() -> RiskModel | None:
    d = _path()
    try:
        clf = joblib.load(d / f"{VERSION}.joblib")
        card = json.loads((d / f"{VERSION}.card.json").read_text())
        if card.get("features") != FEATURES:
            return None
        return RiskModel(clf, card)
    except Exception:  # noqa: BLE001 — fayl yoʻq yoki sklearn versiyasi oʻzgargan: qayta oʻqitiladi
        return None


def get(db=None) -> RiskModel:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = load()
        if _model is None:
            train(db)
    return _model  # type: ignore[return-value]


def score(features: dict, db=None) -> dict | None:
    try:
        return get(db).score(features)
    except Exception:  # noqa: BLE001 — model ishlamasa ham tekshiruv davom etadi
        log.exception("Xavf modeli xatosi")
        return None


def reset() -> None:
    global _model
    with _lock:
        _model = None


__all__ = ["RiskModel", "train", "load", "get", "score", "reset", "VERSION", "NAN"]
