"""Demo dori qutilarining dizayni va sintetik "surat"lari (PackNet uchun maʼlumot).

Har bir demo dori (toʻqima brendlar, backend/seed/drugs.csv) uchun bitta "asl" dizayn bor: rang, logotip,
shrift, joylashuv. Qalbaki variantlar — haqiqiy qalbaki qutilarda uchraydigan farqlar:
rang tusi siljigan, boshqa shrift, matn surilgan, harf xatosi, logotip boshqacha, gologramma yoʻq,
past sifatli bosma. Keyin quti "suratga olinadi": perspektiva, burilish, fon, yorugʻlik, shovqin, JPEG.

Bu haqiqiy qutilar suratlari oʻrnini bosmaydi — faqat modelni boshlash va demo uchun.
Haqiqiy suratlar (dataset/<gtin>/{asl,qalbaki}/*.jpg) train.py ga qoʻshiladi.
"""

from __future__ import annotations

import colorsys
import io
import math
import random
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

FONT_DIR = Path("/usr/share/fonts/truetype")
FONTS = {
    "sans": "dejavu/DejaVuSans-Bold.ttf",
    "serif": "dejavu/DejaVuSerif-Bold.ttf",
    "cond": "dejavu/DejaVuSansCondensed-Bold.ttf",
    "carlito": "crosextra/Carlito-Bold.ttf",
    "caladea": "crosextra/Caladea-Bold.ttf",
}
REGULAR = "dejavu/DejaVuSans.ttf"
_font_cache: dict = {}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key not in _font_cache:
        path = FONTS.get(name, name)
        _font_cache[key] = ImageFont.truetype(str(FONT_DIR / path), size)
    return _font_cache[key]


# PackNet sinflari: demo stsenariylaridagi dorilar (GTIN — backend/seed/drugs.csv)
PRODUCTS = [
    ("04780000007919", "Norvadin", "5 mg", "tabletka N30", False),
    ("04780000015838", "Amlotens", "5 mg", "tabletka N30", True),
    ("04780000023757", "Amlozar", "5 mg", "tabletka N30", False),
    ("04780000031676", "Tumlodip", "5 mg", "tabletka N30", False),
    ("04780000047514", "Metgan", "850 mg", "tabletka N60", True),
    ("04780000063352", "Diaform-O", "850 mg", "tabletka N60", False),
    ("04780000087109", "Registan-Losartan", "50 mg", "tabletka N30", False),
    ("04780000190056", "Amoxibos", "500 mg", "kapsula N16", True),
    ("04780000205894", "Paralpina", "500 mg", "tabletka N20", True),
    ("04780000253408", "Zartramol", "50 mg", "kapsula N20", False),
]
OTHER = len(PRODUCTS)  # "boshqa / tanilmagan qadoq" sinfi
LOGOS = ["circle", "hex", "wave", "tri", "diamond", "ring", "bars", "leaf"]
W, H = 320, 200


@dataclass(frozen=True)
class Design:
    name: str
    strength: str
    form: str
    maker: str
    hue: float        # asosiy rang tusi 0..1
    sat: float
    val: float
    accent_hue: float
    bg_tint: float    # fon oqligi (0.9..1)
    band_h: int       # rangli tasma balandligi
    band_top: bool
    logo: str
    logo_x: int
    logo_size: int
    font: str
    name_size: int
    name_x: int
    name_y: int
    stripes: int      # dekorativ chiziqlar soni
    hologram: bool
    dm_right: bool    # DataMatrix oʻngda/chapda


def _hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0, min(1, s)), max(0, min(1, v)))
    return int(r * 255), int(g * 255), int(b * 255)


def design_for(idx: int) -> Design:
    gtin, name, strength, form, imported = PRODUCTS[idx]
    r = random.Random(int(gtin))
    return _random_design(r, name, strength, form, imported, idx)


def _random_design(r: random.Random, name, strength, form, imported, idx=None) -> Design:
    hue = (idx * 0.1 + r.uniform(-0.03, 0.03)) % 1 if idx is not None else r.random()
    return Design(
        name=name, strength=strength, form=form,
        maker=r.choice(["Demo Farm", "Registan Pharm", "Tuma Med", "Zar Pharma", "Orol Lab", "Bos Pharma"]),
        hue=hue, sat=r.uniform(0.55, 0.9), val=r.uniform(0.55, 0.85), accent_hue=(hue + r.uniform(0.25, 0.6)) % 1,
        bg_tint=r.uniform(0.93, 1.0), band_h=r.randint(38, 70), band_top=r.random() < 0.5,
        logo=r.choice(LOGOS), logo_x=r.choice([22, 250]), logo_size=r.randint(30, 44),
        font=r.choice(list(FONTS)), name_size=r.randint(24, 34), name_x=r.randint(18, 40),
        name_y=r.randint(78, 100), stripes=r.randint(0, 3), hologram=bool(imported), dm_right=r.random() < 0.6,
    )


def random_other(r: random.Random) -> Design:
    letters = "abdefgijklmnoprstuvxyz"
    name = "".join(r.choice(letters) for _ in range(r.randint(5, 10))).capitalize()
    return _random_design(r, name, f"{r.choice([5, 10, 20, 50, 100, 250, 500])} mg",
                          r.choice(["tabletka N30", "kapsula N20", "sirop 100 ml"]), r.random() < 0.4)


def _logo(d: ImageDraw.ImageDraw, kind: str, cx: int, cy: int, s: int, color, rot: float = 0):
    h = s / 2
    if kind == "circle":
        d.ellipse([cx - h, cy - h, cx + h, cy + h], fill=color)
    elif kind == "ring":
        d.ellipse([cx - h, cy - h, cx + h, cy + h], outline=color, width=max(3, s // 7))
    elif kind in ("hex", "tri", "diamond"):
        n = {"hex": 6, "tri": 3, "diamond": 4}[kind]
        pts = [(cx + h * math.cos(rot + 2 * math.pi * i / n - math.pi / 2),
                cy + h * math.sin(rot + 2 * math.pi * i / n - math.pi / 2)) for i in range(n)]
        d.polygon(pts, fill=color)
    elif kind == "wave":
        for k in range(3):
            y = cy - h + k * h * 0.7
            d.arc([cx - h, y, cx + h, y + h], 200, 340, fill=color, width=max(3, s // 8))
    elif kind == "bars":
        bw = s / 5
        for k in range(3):
            x = cx - h + k * bw * 1.8
            d.rectangle([x, cy - h + k * s * 0.15, x + bw, cy + h], fill=color)
    elif kind == "leaf":
        d.chord([cx - h, cy - h, cx + h, cy + h], 30, 240, fill=color)
        d.chord([cx - h * 0.6, cy - h * 0.6, cx + h * 0.9, cy + h * 0.9], 210, 60, fill=color)


def render_face(ds: Design, r: random.Random, print_quality: float = 1.0, typo: str | None = None,
                offset: tuple[int, int] = (0, 0), logo_rot: float = 0.0) -> Image.Image:
    bg = _hsv(ds.hue, 0.06 * (1 - ds.bg_tint) * 10, ds.bg_tint)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    main = _hsv(ds.hue, ds.sat, ds.val)
    acc = _hsv(ds.accent_hue, 0.7, 0.8)
    y0 = 0 if ds.band_top else H - ds.band_h
    d.rectangle([0, y0, W, y0 + ds.band_h], fill=main)
    for k in range(ds.stripes):
        yy = (y0 + ds.band_h + 6 + k * 7) if ds.band_top else (y0 - 10 - k * 7)
        d.rectangle([0, yy, W, yy + 3], fill=acc)
    ly = y0 + ds.band_h // 2
    _logo(d, ds.logo, ds.logo_x + ds.logo_size // 2, ly, ds.logo_size, (255, 255, 255), logo_rot)
    mx = 14 if ds.logo_x > W // 2 else W - 104
    d.text((mx, ly - 6), ds.maker, fill=(255, 255, 255), font=font(REGULAR, 11))
    name = typo or ds.name
    top = (ds.band_h + 10 + ds.stripes * 7) if ds.band_top else 14
    nx, ny = ds.name_x + offset[0], top + (ds.name_y - 78) // 3 + offset[1]
    size = ds.name_size
    f = font(ds.font, size)
    # Uzun nom ajratilgan joyga sigʻishi uchun kichraytiriladi (asl va qalbakida bir xil qoida)
    while f.getlength(name) > 200 and size > 12:
        size -= 1
        f = font(ds.font, size)
    d.text((nx, ny), name, fill=main, font=f)
    d.text((nx, ny + size + 6), ds.strength, fill=(40, 40, 40), font=font(ds.font, max(12, size // 2 + 4)))
    d.text((nx, ny + size + 28), ds.form, fill=(90, 90, 90), font=font(REGULAR, 12))
    # DataMatrix: har doim oʻngda, tasmadan uzoqda
    dm, cell = 12, 3
    dx = W - 52
    dy = H - 52 if ds.band_top else 12
    d.rectangle([dx - 2, dy - 2, dx + dm * cell + 2, dy + dm * cell + 2], fill=(255, 255, 255))
    for i in range(dm):
        for j in range(dm):
            on = (i == 0 or j == dm - 1) or (r.random() < 0.5 and 0 < i and j < dm - 1)
            if on:
                d.rectangle([dx + j * cell, dy + i * cell, dx + j * cell + cell - 1, dy + i * cell + cell - 1], fill=(0, 0, 0))
    d.text((dx, dy + dm * cell + 4), f"S{r.randint(10000, 99999)}", fill=(60, 60, 60), font=font(REGULAR, 8))
    if ds.hologram:
        hx, hy = (W - 96, 14) if not ds.band_top else (W - 50, ds.band_h + 12 + ds.stripes * 7)
        holo = Image.new("RGB", (34, 34))
        hd = ImageDraw.Draw(holo)
        for k in range(34):
            hd.line([(k, 0), (k, 34)], fill=_hsv(k / 34, 0.35, 0.95))
        m = Image.new("L", (34, 34), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 33, 33], fill=255)
        img.paste(holo, (hx, hy), m)
    if print_quality < 1.0:
        # Past sifatli bosma: rang pogʻonalari kamayadi, siyoh yoyiladi
        bits = max(3, int(round(8 * print_quality)))
        img = ImageOps.posterize(img, bits)
        img = img.filter(ImageFilter.GaussianBlur(0.4 + (1 - print_quality) * 1.4))
    return img


def typo_of(name: str, r: random.Random) -> str:
    s = list(name)
    i = r.randrange(1, len(s))
    kind = r.random()
    swaps = {"o": "a", "a": "o", "i": "l", "l": "i", "n": "m", "m": "n", "e": "c", "r": "n", "d": "b", "t": "f"}
    if kind < 0.4 and s[i].lower() in swaps:
        s[i] = swaps[s[i].lower()]
    elif kind < 0.7 and i < len(s) - 1:
        s[i], s[i + 1] = s[i + 1], s[i]
    elif kind < 0.85:
        s.insert(i, s[i])
    else:
        del s[i]
    out = "".join(s)
    return out if out != name else name + "e"


FAKE_KINDS = ["hue", "tone", "font", "offset", "typo", "logo", "hologram", "print", "band"]


def counterfeit(ds: Design, r: random.Random, kinds: list[str] | None = None) -> tuple[Design, dict]:
    """1–3 ta farq qoʻllangan qalbaki dizayn."""
    kinds = kinds or r.sample(FAKE_KINDS, r.choice([1, 1, 2, 2, 3]))
    opts: dict = {"kinds": kinds}
    nd = ds
    for k in kinds:
        if k == "hue":
            nd = replace(nd, hue=(nd.hue + r.choice([-1, 1]) * r.uniform(0.035, 0.1)) % 1)
        elif k == "tone":
            nd = replace(nd, sat=nd.sat * r.choice([0.6, 0.7, 1.3]), val=min(0.97, nd.val * r.choice([0.7, 0.8, 1.2, 1.3])))
        elif k == "font":
            nd = replace(nd, font=r.choice([f for f in FONTS if f != ds.font]))
        elif k == "offset":
            opts["offset"] = (r.choice([-1, 1]) * r.randint(6, 16), r.choice([-1, 1]) * r.randint(4, 10))
            nd = replace(nd, name_size=max(16, nd.name_size + r.choice([-5, -4, 4, 5])))
        elif k == "typo":
            opts["typo"] = typo_of(ds.name, r)
        elif k == "logo":
            if r.random() < 0.5:
                nd = replace(nd, logo=r.choice([l for l in LOGOS if l != ds.logo]))
            else:
                nd = replace(nd, logo_size=int(nd.logo_size * r.choice([0.65, 1.35])))
                opts["logo_rot"] = r.uniform(0.3, 0.8)
        elif k == "hologram":
            nd = replace(nd, hologram=not ds.hologram) if ds.hologram else replace(nd, stripes=(nd.stripes + 2) % 4)
        elif k == "print":
            opts["print_quality"] = r.uniform(0.35, 0.6)
        elif k == "band":
            nd = replace(nd, band_h=int(nd.band_h * r.choice([0.6, 1.45])))
    return nd, opts


def genuine_jitter(ds: Design, r: random.Random) -> Design:
    """Asl qutilar orasidagi tabiiy farq (turli partiya, bosmaxona)."""
    return replace(ds, hue=(ds.hue + r.uniform(-0.008, 0.008)) % 1, sat=ds.sat * r.uniform(0.96, 1.04),
                   val=ds.val * r.uniform(0.96, 1.04))


# ------------------------------------------------------------------ "surat"

def _background(r: random.Random, size: int) -> Image.Image:
    kind = r.random()
    base = tuple(r.randint(30, 230) for _ in range(3))
    img = Image.new("RGB", (size, size), base)
    d = ImageDraw.Draw(img)
    if kind < 0.35:  # gradient
        other = tuple(r.randint(30, 230) for _ in range(3))
        for y in range(size):
            t = y / size
            d.line([(0, y), (size, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(base, other)))
    elif kind < 0.65:  # yogʻoch/mato teksturasi
        arr = np.array(img, dtype=np.float32)
        noise = np.random.default_rng(r.randint(0, 10**9)).normal(0, r.uniform(6, 22), (size, size, 1))
        stripes = np.sin(np.linspace(0, r.uniform(8, 40), size))[None, :, None] * r.uniform(0, 18)
        img = Image.fromarray(np.clip(arr + noise + stripes, 0, 255).astype(np.uint8))
    elif kind < 0.85:  # boshqa narsalar (qogʻoz, boshqa qutilar)
        for _ in range(r.randint(2, 6)):
            x, y = r.randint(-40, size), r.randint(-40, size)
            w, h = r.randint(30, 160), r.randint(20, 120)
            d.rectangle([x, y, x + w, y + h], fill=tuple(r.randint(0, 255) for _ in range(3)))
    return img


def _perspective(img: Image.Image, r: random.Random, strength: float) -> Image.Image:
    w, h = img.size
    m = strength * min(w, h)
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = [(r.uniform(0, m), r.uniform(0, m)), (w - r.uniform(0, m), r.uniform(0, m)),
           (w - r.uniform(0, m), h - r.uniform(0, m)), (r.uniform(0, m), h - r.uniform(0, m))]
    coeffs = _find_coeffs(dst, src)
    return img.transform((w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC, fillcolor=None)


def _find_coeffs(pa, pb):
    A = []
    for p1, p2 in zip(pa, pb):
        A.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
        A.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])
    A = np.array(A, dtype=np.float64)
    B = np.array(pb, dtype=np.float64).reshape(8)
    return np.linalg.solve(A, B).tolist()


def photograph(face: Image.Image, r: random.Random, out: int = 128, hard: bool = True) -> Image.Image:
    """Qutini telefon bilan suratga olishni taqlid qiladi."""
    canvas = 256
    bg = _background(r, canvas)
    f = face.convert("RGBA")
    f = _perspective(f, r, r.uniform(0.0, 0.14 if hard else 0.05))
    scale = r.uniform(0.62, 0.95) if hard else r.uniform(0.8, 0.92)
    fw = int(canvas * scale)
    fh = int(fw * face.height / face.width)
    f = f.resize((fw, fh), Image.Resampling.BILINEAR)
    f = f.rotate(r.uniform(-14, 14) if hard else r.uniform(-4, 4), expand=True, resample=Image.Resampling.BICUBIC)
    x = (canvas - f.width) // 2 + int(r.uniform(-0.08, 0.08) * canvas)
    y = (canvas - f.height) // 2 + int(r.uniform(-0.08, 0.08) * canvas)
    # soya
    shadow = Image.new("RGBA", f.size, (0, 0, 0, 0))
    shadow.putalpha(f.getchannel("A").point(lambda a: int(a * 0.35)))
    bg.paste(shadow, (x + 5, y + 6), shadow)
    bg.paste(f, (x, y), f)
    img = bg
    # yorugʻlik: gradient va oq balans
    arr = np.asarray(img, dtype=np.float32)
    yy, xx = np.mgrid[0:canvas, 0:canvas] / canvas
    ang = r.uniform(0, 2 * math.pi)
    light = 1 + r.uniform(-0.22, 0.22) * ((xx - 0.5) * math.cos(ang) + (yy - 0.5) * math.sin(ang)) * 2
    wb = np.array([r.uniform(0.94, 1.06), 1.0, r.uniform(0.94, 1.06)]) * r.uniform(0.8, 1.12)
    arr = arr * light[..., None] * wb
    if r.random() < 0.25:  # yaltirash
        gx, gy, gr = r.uniform(0.2, 0.8), r.uniform(0.2, 0.8), r.uniform(0.05, 0.15)
        glare = np.exp(-(((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * gr ** 2))) * r.uniform(40, 110)
        arr = arr + glare[..., None]
    arr = arr + np.random.default_rng(r.randint(0, 10**9)).normal(0, r.uniform(1, 7), arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if r.random() < 0.4:
        img = img.filter(ImageFilter.GaussianBlur(r.uniform(0.3, 1.2)))
    # kesish (kamera ramkasi) va kichraytirish — turli algoritmlar (brauzer/telefon farqi)
    c = int(canvas * r.uniform(0.0, 0.06))
    img = img.crop((c, c, canvas - c, canvas - c))
    img = img.resize((out, out), r.choice([Image.Resampling.BILINEAR, Image.Resampling.BICUBIC,
                                            Image.Resampling.LANCZOS, Image.Resampling.BOX]))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=r.randint(45, 95))
    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    if hard and r.random() < 0.2:
        img = ImageEnhance.Contrast(img).enhance(r.uniform(0.75, 1.25))
    return img


def sample(r: random.Random, out: int = 128) -> tuple[np.ndarray, int, int, dict]:
    """Bitta oʻqitish namunasi: (surat, mahsulot sinfi, qalbaki 0/1/-1, izoh)."""
    u = r.random()
    if u < 0.14:
        ds = random_other(r)
        face = render_face(ds, r)
        return np.asarray(photograph(face, r, out)), OTHER, -1, {"kind": "other"}
    if u < 0.17:  # quti yoʻq — faqat fon
        return np.asarray(_background(r, 256).resize((out, out))), OTHER, -1, {"kind": "background"}
    idx = r.randrange(len(PRODUCTS))
    base = design_for(idx)
    if r.random() < 0.5:
        face = render_face(genuine_jitter(base, r), r)
        return np.asarray(photograph(face, r, out)), idx, 0, {"kind": "genuine"}
    ds, opts = counterfeit(base, r)
    face = render_face(ds, r, print_quality=opts.get("print_quality", 1.0), typo=opts.get("typo"),
                       offset=opts.get("offset", (0, 0)), logo_rot=opts.get("logo_rot", 0.0))
    return np.asarray(photograph(face, r, out)), idx, 1, {"kind": "+".join(opts["kinds"])}
