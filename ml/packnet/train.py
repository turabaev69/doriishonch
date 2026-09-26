"""PackNet: qadoq suratidan (1) qaysi dori qutisi ekanini va (2) asl dizayndan farqini baholovchi kichik CNN.

Ishga tushirish (repo ildizidan):
    pip install torch pillow numpy
    python ml/packnet/train.py                 # sintetik maʼlumot bilan
    python ml/packnet/train.py --real dataset  # + haqiqiy suratlar: dataset/<gtin>/{asl,qalbaki}/*.jpg

Natija: backend/app/ml/weights/packnet-v1.json (int8 ogʻirliklar). Ayni fayl brauzer va iPhone ilovasiga
nusxalanadi (frontend/public/models, mobile/assets/models) — bitta model uchta joyda bir xil ishlaydi.
Arxitektura MobileNet uslubida (depthwise separable), ~16M MAC: telefonda JS da ~0.1–0.5 s.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import random
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import boxes  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend/app/ml/weights/packnet-v1.json"
CACHE = Path(__file__).parent / ".cache"
SIZE = 128
MEAN, STD = 0.5, 0.25
# (tur, chiqish kanallari, qadam)
ARCH = [("conv", 16, 2), ("dw", 32, 1), ("dw", 48, 2), ("dw", 48, 1), ("dw", 96, 2), ("dw", 96, 1),
        ("dw", 160, 2), ("dw", 160, 1)]


class PackNet(nn.Module):
    def __init__(self, n_products: int):
        super().__init__()
        layers, cin = [], 3
        for kind, cout, s in ARCH:
            if kind == "conv":
                layers += [nn.Conv2d(cin, cout, 3, s, 1, bias=False), nn.BatchNorm2d(cout), nn.ReLU()]
            else:
                layers += [nn.Conv2d(cin, cin, 3, s, 1, groups=cin, bias=False), nn.BatchNorm2d(cin), nn.ReLU(),
                           nn.Conv2d(cin, cout, 1, 1, 0, bias=False), nn.BatchNorm2d(cout), nn.ReLU()]
            cin = cout
        self.features = nn.Sequential(*layers)
        self.drop = nn.Dropout(0.2)
        self.product = nn.Linear(cin, n_products)
        self.fake = nn.Linear(cin, 1)

    def forward(self, x):
        h = self.features(x).mean(dim=(2, 3))
        h = self.drop(h)
        return self.product(h), self.fake(h).squeeze(1)


# ------------------------------------------------------------------ maʼlumot

def _gen(args):
    seed, n = args
    r = random.Random(seed)
    xs, ps, fs, kinds = [], [], [], []
    for _ in range(n):
        a, p, f, info = boxes.sample(r, SIZE)
        xs.append(a)
        ps.append(p)
        fs.append(f)
        kinds.append(info["kind"])
    return np.stack(xs), np.array(ps), np.array(fs), kinds


def dataset(n: int, seed: int, workers: int = 2):
    path = CACHE / f"ds_{n}_{seed}.npz"
    if path.exists():
        z = np.load(path, allow_pickle=True)
        return z["x"], z["p"], z["f"], list(z["k"])
    CACHE.mkdir(exist_ok=True)
    chunk = 500
    jobs = [(seed * 100000 + i, min(chunk, n - i * chunk)) for i in range(math.ceil(n / chunk))]
    t = time.time()
    with Pool(workers) as pool:
        parts = pool.map(_gen, jobs)
    x = np.concatenate([p[0] for p in parts])
    p = np.concatenate([p[1] for p in parts])
    f = np.concatenate([p[2] for p in parts])
    k = sum((p[3] for p in parts), [])
    np.savez(path, x=x, p=p, f=f, k=np.array(k, dtype=object))
    print(f"  {n} ta surat yaratildi ({time.time() - t:.0f} s)", flush=True)
    return x, p, f, k


def real_images(root: Path):
    """dataset/<gtin>/{asl,qalbaki}/*.jpg — haqiqiy suratlar (boʻlsa)."""
    gt = {g: i for i, (g, *_rest) in enumerate(boxes.PRODUCTS)}
    xs, ps, fs = [], [], []
    for gdir in sorted(root.glob("*")):
        idx = gt.get(gdir.name, boxes.OTHER)
        for label, sub in ((0, "asl"), (1, "qalbaki")):
            for img in sorted((gdir / sub).glob("*.jp*g")):
                im = Image.open(img).convert("RGB")
                s = min(im.size)
                im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
                xs.append(np.asarray(im.resize((SIZE, SIZE), Image.Resampling.BILINEAR)))
                ps.append(idx)
                fs.append(label if idx != boxes.OTHER else -1)
    if not xs:
        return None
    return np.stack(xs), np.array(ps), np.array(fs)


def to_tensor(x: np.ndarray) -> torch.Tensor:
    return (torch.from_numpy(x).permute(0, 3, 1, 2).float() / 255 - MEAN) / STD


# ------------------------------------------------------------------ eksport

def fold(conv: nn.Conv2d, bn: nn.BatchNorm2d):
    w = conv.weight.detach().numpy().astype(np.float64)
    g = bn.weight.detach().numpy() / np.sqrt(bn.running_var.detach().numpy() + bn.eps)
    b = bn.bias.detach().numpy() - bn.running_mean.detach().numpy() * g
    return (w * g[:, None, None, None]).astype(np.float32), b.astype(np.float32)


def q8(w: np.ndarray):
    """Chiqish kanali boʻyicha simmetrik int8."""
    flat = w.reshape(w.shape[0], -1)
    scale = np.maximum(np.abs(flat).max(axis=1), 1e-8) / 127.0
    q = np.clip(np.round(flat / scale[:, None]), -127, 127).astype(np.int8)
    return q, scale.astype(np.float32)


def b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def export(model: PackNet) -> dict:
    model.eval()
    mods = list(model.features)
    layers, i = [], 0
    while i < len(mods):
        conv, bn = mods[i], mods[i + 1]
        w, b = fold(conv, bn)
        q, s = q8(w)
        layers.append({"type": "dw" if conv.groups > 1 else "conv", "k": conv.kernel_size[0], "stride": conv.stride[0],
                       "pad": conv.padding[0], "cin": conv.in_channels, "cout": conv.out_channels, "relu": True,
                       "w": b64(q), "scale": b64(s), "bias": b64(b)})
        i += 3
    heads = {}
    for name, lin in (("product", model.product), ("fake", model.fake)):
        w = lin.weight.detach().numpy().astype(np.float32)
        q, s = q8(w)
        heads[name] = {"cin": w.shape[1], "cout": w.shape[0], "w": b64(q), "scale": b64(s),
                       "bias": b64(lin.bias.detach().numpy().astype(np.float32))}
    return {"layers": layers, "heads": heads}


# ------------------------------------------------------------------ numpy inference (eksport tekshiruvi)

def _dq(layer):
    q = np.frombuffer(base64.b64decode(layer["w"]), dtype=np.int8).astype(np.float32)
    s = np.frombuffer(base64.b64decode(layer["scale"]), dtype=np.float32).copy()
    b = np.frombuffer(base64.b64decode(layer["bias"]), dtype=np.float32).copy()
    return q.reshape(len(s), -1) * s[:, None], b


def np_forward(spec: dict, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """x: (N, 3, H, W) normallashtirilgan. Backenddagi app/ml/packnet.py bilan bir xil hisob."""
    h = torch.from_numpy(x)
    for L in spec["layers"]:
        w, b = _dq(L)
        if L["type"] == "dw":
            wt = torch.from_numpy(w.reshape(L["cout"], 1, L["k"], L["k"]))
            h = F.conv2d(h, wt, torch.from_numpy(b), L["stride"], L["pad"], groups=L["cin"])
        else:
            wt = torch.from_numpy(w.reshape(L["cout"], L["cin"], L["k"], L["k"]))
            h = F.conv2d(h, wt, torch.from_numpy(b), L["stride"], L["pad"])
        h = F.relu(h)
    g = h.mean(dim=(2, 3)).numpy()
    wp, bp = _dq(spec["heads"]["product"])
    wf, bf = _dq(spec["heads"]["fake"])
    return g @ wp.T + bp, (g @ wf.T + bf)[:, 0]


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def evaluate(spec, x, p, f, kinds, known_min=0.6):
    logits, fz = [], []
    for i in range(0, len(x), 256):
        a, b = np_forward(spec, to_tensor(x[i:i + 256]).numpy())
        logits.append(a)
        fz.append(b)
    pr = softmax(np.concatenate(logits))
    pf = 1 / (1 + np.exp(-np.concatenate(fz)))
    pred = pr.argmax(1)
    known = p != boxes.OTHER
    res = {"product_acc": float((pred == p).mean()),
           "product_acc_known": float((pred[known] == p[known]).mean()),
           "other_recall": float((pred[~known] == boxes.OTHER).mean())}
    m = known & (f >= 0)
    from sklearn.metrics import roc_auc_score
    res["fake_auc"] = float(roc_auc_score(f[m], pf[m]))
    return res, pr, pf


def pick_threshold(pf, f, mask, max_fpr=0.05):
    """Asl qutilarning koʻpi bilan 5% i "farq bor" deb belgilanadigan chegara."""
    g = np.sort(pf[mask & (f == 0)])
    return float(g[int(len(g) * (1 - max_fpr))]) if len(g) else 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--real", type=str, default="")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    torch.manual_seed(0)
    torch.set_num_threads(max(1, a.workers))
    print("Maʼlumot…", flush=True)
    x, p, f, _ = dataset(a.n, 1, a.workers)
    xv, pv, fv, kv = dataset(3000, 2, a.workers)
    n_real = 0
    if a.real:
        rr = real_images(Path(a.real))
        if rr:
            n_real = len(rr[0])
            rep = max(1, 2000 // max(1, n_real))  # haqiqiy suratlar kam — takrorlab vazn beramiz
            x = np.concatenate([x] + [rr[0]] * rep)
            p = np.concatenate([p] + [rr[1]] * rep)
            f = np.concatenate([f] + [rr[2]] * rep)
            print(f"  + {n_real} ta haqiqiy surat (x{rep})", flush=True)

    n_products = len(boxes.PRODUCTS) + 1
    model = PackNet(n_products)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    bs = 128
    steps = a.epochs * math.ceil(len(x) / bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=4e-3, total_steps=steps, pct_start=0.15)
    pt, ft = torch.from_numpy(p).long(), torch.from_numpy(f).float()
    t0 = time.time()
    for ep in range(a.epochs):
        model.train()
        perm = torch.randperm(len(x))
        tot = 0.0
        for bi in range(0, len(x), bs):
            idx = perm[bi:bi + bs]
            xb = to_tensor(x[idx.numpy()])
            # kichik siljish (ramkaga turlicha tushish)
            dx, dy = random.randint(-6, 6), random.randint(-6, 6)
            xb = torch.roll(xb, shifts=(dy, dx), dims=(2, 3))
            lp, lf = model(xb)
            loss = F.cross_entropy(lp, pt[idx], label_smoothing=0.05)
            m = ft[idx] >= 0
            if m.any():
                loss = loss + F.binary_cross_entropy_with_logits(lf[m], ft[idx][m])
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            tot += loss.item() * len(idx)
        if (ep + 1) % 3 and ep + 1 != a.epochs:
            print(f"epoch {ep + 1}/{a.epochs} loss {tot / len(x):.3f} | {time.time() - t0:.0f}s", flush=True)
            continue
        spec = export(model)
        res, _, _ = evaluate(spec, xv, pv, fv, kv)
        print(f"epoch {ep + 1}/{a.epochs} loss {tot / len(x):.3f} | val {json.dumps({k: round(v, 3) for k, v in res.items()})}"
              f" | {time.time() - t0:.0f}s", flush=True)

    spec = export(model)
    res, pr, pf = evaluate(spec, xv, pv, fv, kv)
    known = pv != boxes.OTHER
    thr = pick_threshold(pf, fv, known)
    # Farq turlari boʻyicha aniqlash darajasi (chegara bilan)
    by_kind: dict[str, list] = {}
    for k, prob, lab, kn in zip(kv, pf, fv, known):
        if kn and lab == 1:
            for part in k.split("+"):
                by_kind.setdefault(part, []).append(prob >= thr)
    res["fake_recall_at_threshold"] = float(np.mean(pf[known & (fv == 1)] >= thr))
    res["genuine_flagged_at_threshold"] = float(np.mean(pf[known & (fv == 0)] >= thr))
    res["recall_by_kind"] = {k: round(float(np.mean(v)), 3) for k, v in sorted(by_kind.items())}
    card = {
        "name": "PackNet", "version": "packnet-v1",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": {"size": SIZE, "mean": MEAN, "std": STD, "layout": "RGB, 0..255 → (x/255-mean)/std"},
        "classes": [{"gtin": g, "name": n} for g, n, *_ in boxes.PRODUCTS] + [{"gtin": "", "name": "boshqa"}],
        "other_index": boxes.OTHER,
        "thresholds": {"known_min": 0.6, "fake": round(thr, 4)},
        "train": {"synthetic": int(a.n), "real": n_real, "epochs": a.epochs},
        "metrics_val_synthetic": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items()},
        "notes": "Sintetik demo qutilarda oʻqitilgan. Haqiqiy qadoqlar uchun haqiqiy suratlar bilan qayta oʻqitish kerak.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"card": card, **spec}, separators=(",", ":")))
    print(json.dumps(card["metrics_val_synthetic"], indent=1))
    print(f"Saqlandi: {OUT} ({OUT.stat().st_size // 1024} KB), fake chegara {thr:.3f}")


if __name__ == "__main__":
    main()
