"""Demo quti suratlari (veb, iPhone, testlar uchun) va ogʻirliklarni ilovalarga nusxalash.

    python ml/packnet/make_samples.py

Suratlar oʻqitish toʻplamidan boshqa seedlarda yaratiladi (model ularni koʻrmagan). Har bir namuna
serverdagi numpy model bilan tekshiriladi; kutilgan natija chiqmasa, keyingi seed sinaladi —
namoyish uchun aniq misollar. Umumiy sifat koʻrsatkichlari model kartasida (alohida validatsiya toʻplami).
"""

from __future__ import annotations

import io
import json
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import boxes  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml import packnet  # noqa: E402

WEIGHTS = ROOT / "backend/app/ml/weights/packnet-v1.json"
OUT_DIRS = [ROOT / "backend/app/ml/samples", ROOT / "frontend/public/demo-qutilar", ROOT / "mobile/assets/demo-boxes"]
MODEL_DIRS = [ROOT / "frontend/public/models", ROOT / "mobile/assets/models"]

# fayl, mahsulot indeksi (boxes.PRODUCTS), haqiqat, qalbaki turlari
SAMPLES = [
    ("norvadin-asl", 0, "asl", None),
    ("norvadin-qalbaki", 0, "qalbaki", ["hue", "font"]),
    ("amoxibos-asl", 7, "asl", None),
    ("amoxibos-qalbaki", 7, "qalbaki", ["hologram", "tone"]),
    ("metgan-asl", 4, "asl", None),
    ("metgan-qalbaki", 4, "qalbaki", ["logo", "print"]),
    ("zartramol-asl", 9, "asl", None),
    ("boshqa", None, "boshqa", None),
]
EXPECT = {"asl": "asl", "qalbaki": "farq", "boshqa": "tanilmadi"}


def render(idx, truth, kinds, seed):
    r = random.Random(seed)
    if truth == "boshqa":
        face = boxes.render_face(boxes.random_other(r), r)
    elif truth == "asl":
        face = boxes.render_face(boxes.genuine_jitter(boxes.design_for(idx), r), r)
    else:
        ds, o = boxes.counterfeit(boxes.design_for(idx), r, kinds)
        face = boxes.render_face(ds, r, print_quality=o.get("print_quality", 1.0), typo=o.get("typo"),
                                 offset=o.get("offset", (0, 0)), logo_rot=o.get("logo_rot", 0.0))
    img = boxes.photograph(face, r, out=256, hard=False)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def main():
    for d in OUT_DIRS + MODEL_DIRS:
        d.mkdir(parents=True, exist_ok=True)
    for d in MODEL_DIRS:
        shutil.copy(WEIGHTS, d / WEIGHTS.name)
    packnet._net = None
    manifest = []
    for name, idx, truth, kinds in SAMPLES:
        gtin = boxes.PRODUCTS[idx][0] if idx is not None else ""
        for seed in range(900000, 900060):
            data = render(idx, truth, kinds, seed)
            res = packnet.predict(data, gtin or None)
            if res["verdict"] == EXPECT[truth]:
                break
        else:
            print(f"  ! {name}: kutilgan natija chiqmadi, oxirgisi saqlandi ({res['verdict']})")
        for d in OUT_DIRS:
            (d / f"{name}.jpg").write_bytes(data)
        label = {"asl": "asl", "qalbaki": "qalbaki", "boshqa": "notanish"}[truth]
        manifest.append({"file": f"{name}.jpg", "gtin": gtin,
                         "name": boxes.PRODUCTS[idx][1] if idx is not None else "Notanish quti",
                         "label": f"{boxes.PRODUCTS[idx][1]} · {label}" if idx is not None else "Notanish quti",
                         "truth": truth})
        print(f"  {name}: seed {seed} → {res['verdict']} (farq {res['fake_prob']}, {res['product']['name']} {res['product']['prob']})")
    (ROOT / "frontend/public/demo-qutilar/samples.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print("Tayyor.")


if __name__ == "__main__":
    main()
