"""PackNet — qadoq surati modeli (serverdagi inference, faqat numpy).

Ogʻirliklar: app/ml/weights/packnet-v1.json (ml/packnet/train.py yaratadi, int8).
Ayni hisob brauzer va iPhone da TypeScript da takrorlanadi (frontend/lib/packnet.ts, mobile/src/lib/packnet.ts),
shuning uchun natija uchala joyda bir xil. Oldindan ishlov: markaziy kvadrat kesish → 128×128 → (x/255−0.5)/0.25.
"""

from __future__ import annotations

import base64
import io
import json
import threading
from pathlib import Path

import numpy as np

WEIGHTS = Path(__file__).parent / "weights" / "packnet-v1.json"
_lock = threading.Lock()
_net: "Net | None" = None


class Net:
    def __init__(self, spec: dict):
        self.card = spec["card"]
        self.size = self.card["input"]["size"]
        self.mean, self.std = self.card["input"]["mean"], self.card["input"]["std"]
        self.layers = [dict(L, W=_dq(L)[0], B=_dq(L)[1]) for L in spec["layers"]]
        self.heads = {k: _dq(v) for k, v in spec["heads"].items()}

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, float]:
        """x: (H, W, 3) float32, normallashtirilgan. Qaytaradi: mahsulot logitlari, qalbaki logit."""
        h = x
        for L in self.layers:
            if L["type"] == "dw":
                h = _depthwise(h, L["W"].reshape(L["cout"], L["k"], L["k"]), L["B"], L["stride"], L["pad"])
            elif L["k"] == 1:
                h = h @ L["W"].reshape(L["cout"], L["cin"]).T + L["B"]
            else:
                h = _conv(h, L["W"].reshape(L["cout"], L["cin"], L["k"], L["k"]), L["B"], L["stride"], L["pad"])
            if L["relu"]:
                np.maximum(h, 0, out=h)
            # depthwise dan keyin pointwise keladi — eksportda ular alohida qatlam
        g = h.mean(axis=(0, 1))
        wp, bp = self.heads["product"]
        wf, bf = self.heads["fake"]
        return g @ wp.T + bp, float((g @ wf.T + bf)[0])


def _dq(L: dict) -> tuple[np.ndarray, np.ndarray]:
    q = np.frombuffer(base64.b64decode(L["w"]), dtype=np.int8).astype(np.float32)
    s = np.frombuffer(base64.b64decode(L["scale"]), dtype=np.float32)
    b = np.frombuffer(base64.b64decode(L["bias"]), dtype=np.float32).copy()
    return (q.reshape(len(s), -1) * s[:, None]).astype(np.float32), b


def _pad(x: np.ndarray, p: int) -> np.ndarray:
    return np.pad(x, ((p, p), (p, p), (0, 0))) if p else x


def _conv(x, w, b, stride, pad):
    """Oddiy konvolyutsiya (HWC). w: (cout, cin, k, k)."""
    x = _pad(x, pad)
    k = w.shape[2]
    H = (x.shape[0] - k) // stride + 1
    W = (x.shape[1] - k) // stride + 1
    cols = np.empty((H, W, k, k, x.shape[2]), dtype=np.float32)
    for i in range(k):
        for j in range(k):
            cols[:, :, i, j, :] = x[i:i + stride * H:stride, j:j + stride * W:stride, :]
    wm = w.transpose(2, 3, 1, 0).reshape(-1, w.shape[0])  # (k*k*cin, cout)
    return cols.reshape(H, W, -1) @ wm + b


def _depthwise(x, w, b, stride, pad):
    """w: (c, k, k)."""
    x = _pad(x, pad)
    k = w.shape[1]
    H = (x.shape[0] - k) // stride + 1
    W = (x.shape[1] - k) // stride + 1
    out = np.zeros((H, W, x.shape[2]), dtype=np.float32)
    for i in range(k):
        for j in range(k):
            out += x[i:i + stride * H:stride, j:j + stride * W:stride, :] * w[:, i, j]
    return out + b


def available() -> bool:
    return WEIGHTS.exists()


def get() -> Net:
    global _net
    if _net is None:
        with _lock:
            if _net is None:
                _net = Net(json.loads(WEIGHTS.read_text()))
    return _net


def preprocess(image_bytes: bytes, size: int) -> np.ndarray:
    from PIL import Image, ImageOps

    im = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width - s) // 2 + s, (im.height - s) // 2 + s))
    return np.asarray(im.resize((size, size), Image.Resampling.BILINEAR), dtype=np.float32)


def _softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max())
    return e / e.sum()


def interpret(card: dict, probs: np.ndarray, fake_p: float, expected_gtin: str | None) -> dict:
    """Natijani oddiy tilga oʻgirish. Bu mantiq TypeScript versiyasida ham aynan shunday."""
    classes, other = card["classes"], card["other_index"]
    thr = card["thresholds"]
    top = int(probs.argmax())
    conf = float(probs[top])
    exp = (expected_gtin or "").lstrip("0")
    exp_idx = next((i for i, c in enumerate(classes) if c["gtin"] and c["gtin"].lstrip("0") == exp), None)
    out = {"product": {"gtin": classes[top]["gtin"], "name": classes[top]["name"], "prob": round(conf, 3)},
           "fake_prob": round(fake_p, 3), "model": card["version"], "on_device": False}
    if top == other or conf < thr["known_min"]:
        out.update(verdict="tanilmadi", title="Model bu qadoqni tanimadi",
                   text="Model hozircha faqat demo dori qutilarini taniydi. Qutini toʻliq, yorugʻda suratga oling "
                        "yoki boshqa tekshiruvlarga tayaning.")
    elif exp_idx is not None and top != exp_idx:
        out.update(verdict="boshqa", title="Qadoq boshqa dori qutisiga oʻxshaydi",
                   text=f"Kod {classes[exp_idx]['name']} ga tegishli, surat esa {classes[top]['name']} qutisiga oʻxshaydi.")
    elif fake_p >= thr["fake"]:
        out.update(verdict="farq", title="Qadoq asl dizayndan farq qiladi",
                   text="Rang, shrift, yozuv yoki bosma sifati asl qutidan farq qilishi mumkin. Diqqat bilan solishtiring.")
    else:
        out.update(verdict="asl", title="Qadoq asl dizaynga mos",
                   text=f"Surat {classes[top]['name']} ning asl qadogʻiga oʻxshaydi.")
    return out


def predict(image_bytes: bytes, expected_gtin: str | None = None) -> dict:
    net = get()
    x = (preprocess(image_bytes, net.size) / 255.0 - net.mean) / net.std
    logits, fz = net.forward(x.astype(np.float32))
    return interpret(net.card, _softmax(logits), float(1 / (1 + np.exp(-fz))), expected_gtin)


def card() -> dict | None:
    return get().card if available() else None
