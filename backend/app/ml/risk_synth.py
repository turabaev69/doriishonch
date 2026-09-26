"""Skan xavf modeli uchun sintetik (simulyatsiya) maʼlumot.

Nima uchun: haqiqiy tasdiqlangan qalbaki holatlar hali kam. Model avval taʼminot zanjirining
simulyatsiyasida oldindan oʻqitiladi, keyin inspektor tasdiqlagan haqiqiy holatlar bilan (katta vazn)
qayta oʻqitiladi. Simulyatsiya farazlari shu faylda ochiq yozilgan — ularni haqiqiy statistikaga
qarab oʻzgartirish mumkin.

Yashirin omillar:
- dorixona insofsiz (12%): qayta ishlatilgan qutilar, kassadan oʻtmagan sotuvlar koʻp;
- partiya buzilgan (6%): shu partiyada qalbaki qutilar aralashgan;
- dori qimmat va import: qalbakilashtirish uchun jozibador.
Qalbaki quti kuzatiladigan belgilarni (bayroqlar, narx, skan tarixi) oshiradi, lekin hammasini emas —
aynan shu "zaif signallar yigʻindisi"ni model oʻrganadi.
"""

from __future__ import annotations

import numpy as np

from .risk_features import BATCH_PRIOR, BATCH_WEIGHT, FEATURES, PH_PRIOR, PH_WEIGHT


def _sig(x):
    return 1 / (1 + np.exp(-x))


def generate(n: int = 24000, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    r = np.random.default_rng(seed)
    ph_bad = r.random(n) < 0.12
    batch_bad = r.random(n) < 0.06
    price_log = r.uniform(3.6, 5.2, n)
    imported = r.random(n) < 0.45
    logit = -3.6 + 2.2 * ph_bad + 2.4 * batch_bad + 0.9 * (price_log - 4.4) + 0.5 * imported
    y = r.random(n) < _sig(logit)

    def p(fake_p, real_p):
        return r.random(n) < np.where(y, fake_p, real_p)

    mode_after = r.random(n) < 0.3
    f = {}
    f["f_reused"] = p(0.30, 0.008)
    f["f_code_fake"] = p(0.20, 0.003)
    f["f_clone"] = p(0.10, 0.004)
    f["f_no_customs"] = imported & p(0.25, 0.03)
    f["f_unreg_sale"] = mode_after & p(0.35, 0.05 + 0.25 * ph_bad)
    f["f_chain_gap"] = p(0.14, 0.03)
    f["f_recall"] = p(0.05, 0.015)

    # Seriya topilmasa (70%) quti tarixi yoʻq; kalit mos kelmasa (30%) — seriya haqiqiy qutiniki, tarix bor
    known_pack = ~(f["f_code_fake"] & (r.random(n) < 0.7))
    f["box_scans_30d"] = np.where(known_pack, r.poisson(np.where(y, 1.8, 0.8)) + 2 * f["f_clone"], np.nan)
    devices = np.minimum(f["box_scans_30d"], r.poisson(np.where(y, 1.4, 0.7)) + f["f_clone"] * 2)
    f["box_devices_30d"] = np.where(known_pack, devices, np.nan)
    f["box_regions_3d"] = np.where(known_pack, 1 + f["f_clone"] * r.integers(2, 4, n) + (r.random(n) < 0.02), np.nan)

    has_price = r.random(n) < 0.3
    ratio = np.exp(r.normal(np.where(y, np.log(0.68), 0.0), np.where(y, 0.22, 0.18)))
    # Haqiqiy dorilarda ham chegirma/aksiya boʻladi (5%): arzonlik yolgʻiz oʻzi isbot emas
    promo = ~y & (r.random(n) < 0.05)
    ratio = np.where(promo, r.uniform(0.4, 0.85, n), ratio)
    f["price_ratio"] = np.where(has_price, ratio, np.nan)

    has_ph = r.random(n) < 0.85
    n_ph = r.integers(3, 120, n)
    bad_ph = r.binomial(n_ph, np.where(ph_bad, 0.16, 0.035))
    f["ph_bad_rate"] = np.where(has_ph, (bad_ph + PH_PRIOR * PH_WEIGHT) / (n_ph + PH_WEIGHT), np.nan)
    f["ph_confirmed"] = np.where(has_ph, r.poisson(np.where(ph_bad, 1.3, 0.08)), np.nan)
    f["ph_license_bad"] = np.where(has_ph, r.random(n) < np.where(ph_bad, 0.12, 0.02), np.nan)

    n_b = r.integers(1, 60, n)
    bad_b = r.binomial(n_b, np.where(batch_bad, 0.22, 0.03))
    f["batch_bad_rate"] = np.where(known_pack, (bad_b + BATCH_PRIOR * BATCH_WEIGHT) / (n_b + BATCH_WEIGHT), np.nan)
    f["batch_reports"] = np.where(known_pack, r.poisson(np.where(batch_bad, 1.0, 0.04)), np.nan)

    f["drug_price_log"] = price_log
    f["drug_import"] = imported.astype(float)
    shelf = r.exponential(np.where(y, 85, 40))
    f["days_on_shelf"] = np.where(known_pack & (r.random(n) < 0.9), shelf, np.nan)
    f["days_to_expiry"] = np.where(known_pack, np.where(y, r.uniform(-30, 700, n), r.uniform(40, 1000, n)), np.nan)
    f["night"] = p(0.14, 0.08)
    f["mode_after"] = mode_after

    X = np.column_stack([np.asarray(f[k], dtype=float) for k in FEATURES])
    # Belgi shovqini: 2% yorliq xato (inspektor ham xato qilishi mumkin)
    flip = r.random(n) < 0.02
    y = np.where(flip, ~y, y).astype(int)
    return X, y
