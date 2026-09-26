"""GS1 DataMatrix (Asl Belgisi) kodini tahlil qilish.

Dori qutisidagi kod tuzilmasi:
  (01) GTIN, 14 raqam
  (21) seriya raqami, Asl Belgisida 13 belgi
  (91) tekshiruv kaliti, 4 belgi
  (92) kriptografik tekshiruv kodi, 44 belgi
Ixtiyoriy: (17) yaroqlilik muddati YYMMDD, (10) seriya/partiya.

Skanerlar kodni turlicha qaytaradi: "]d2" prefiksi bilan, GS (\\x1d) ajratgich bilan,
qavsli "(01)..." koʻrinishda yoki ajratgichsiz. Parser hammasini qabul qiladi.
"""

import re
from dataclasses import dataclass
from datetime import date

GS = "\x1d"
_FIXED = {"01": 14, "17": 6}
_VAR_MAX = {"10": 20, "21": 20, "91": 4, "92": 44}
ASL_SERIAL_LEN = 13


@dataclass
class ParsedCode:
    gtin: str = ""
    serial: str = ""
    batch: str = ""
    expiry: date | None = None
    key91: str = ""
    crypto92: str = ""
    url: str = ""  # dori kodi emas, oddiy havola (reklama QR, sayt, Telegram)

    @property
    def ok(self) -> bool:
        return bool(self.gtin and self.serial)


def _expiry(yymmdd: str) -> date | None:
    try:
        y, m, d = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
        if d == 0:  # GS1: kun 00 = oy oxiri; oyning 28-kunini olamiz
            d = 28
        return date(2000 + y, m, d)
    except (ValueError, IndexError):
        return None


_DL_AI = re.compile(r"/(01|21|10|17)/([^/?#]+)")


def _digital_link(s: str, out: ParsedCode) -> bool:
    """GS1 Digital Link: https://.../01/04780000007919/21/SERIAL — qutidagi QR ham dori kodi boʻlishi mumkin."""
    from urllib.parse import unquote

    found = False
    for ai, val in _DL_AI.findall(s):
        if ai == "01" and not re.fullmatch(r"\d{8,14}", val):
            continue
        _assign(out, ai, unquote(val))
        found = found or ai == "01"
    return found


def is_url(s: str) -> bool:
    return bool(re.match(r"^(https?://|www\.|t\.me/|tg://)", (s or "").strip(), re.I))


def parse(raw: str) -> ParsedCode:
    s = (raw or "").strip()
    if is_url(s):
        out = ParsedCode()
        if not _digital_link(s, out):
            out.url = s[:200]
        return out
    for prefix in ("]d2", "]Q3", "]C1", "]e0"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    # Ayrim skanerlar GS ni boshqa belgi bilan beradi
    s = s.replace("␝", GS).replace("<GS>", GS).replace("{GS}", GS)
    out = ParsedCode()

    # Qavsli koʻrinish: (01)...(21)...
    if s.startswith("("):
        for ai, val in re.findall(r"\((\d{2})\)([^()]*)", s):
            _assign(out, ai, val.strip())
        return out

    s = s.replace(" ", "")
    i = 0
    while i < len(s) - 1:
        if s[i] == GS:
            i += 1
            continue
        ai = s[i:i + 2]
        i += 2
        if ai in _FIXED:
            n = _FIXED[ai]
            _assign(out, ai, s[i:i + n])
            i += n
        elif ai in _VAR_MAX:
            end = s.find(GS, i)
            if end == -1:
                end = len(s)
                # Ajratgich yoʻq: Asl Belgisi seriyasi 13 belgidan iborat
                if ai == "21" and end - i > ASL_SERIAL_LEN:
                    end = i + ASL_SERIAL_LEN
                elif ai == "91" and end - i > 4:
                    end = i + 4
            _assign(out, ai, s[i:min(end, i + _VAR_MAX[ai])])
            i = end
        else:
            break  # nomaʼlum AI: toʻxtaymiz

    # Faqat raqam kiritilgan boʻlsa (masalan, shtrix-kod), GTIN deb qabul qilamiz
    if not out.gtin:
        digits = re.sub(r"\D", "", raw or "")
        if 8 <= len(digits) <= 14 and digits == (raw or "").strip():
            out.gtin = digits.zfill(14)
    return out


def _assign(out: ParsedCode, ai: str, val: str) -> None:
    if ai == "01":
        out.gtin = val.zfill(14)
    elif ai == "21":
        out.serial = val
    elif ai == "10":
        out.batch = val
    elif ai == "17":
        out.expiry = _expiry(val)
    elif ai == "91":
        out.key91 = val
    elif ai == "92":
        out.crypto92 = val


def build(gtin: str, serial: str, expiry: date | None = None, batch: str = "", key91: str = "EE07",
          crypto92: str = "") -> str:
    """Demo uchun GS ajratgichli kod matnini yasaydi."""
    # Oʻzgarmas uzunlikdagi maydonlar oldin, oʻzgaruvchan maydonlardan keyin GS qoʻyiladi.
    head = f"01{gtin}" + (f"17{expiry:%y%m%d}" if expiry else "")
    parts = []
    if batch:
        parts.append(f"{head}10{batch}")
        parts.append(f"21{serial}")
    else:
        parts.append(f"{head}21{serial}")
    parts.append(f"91{key91}")
    if crypto92:
        parts.append(f"92{crypto92}")
    return GS.join(parts)
