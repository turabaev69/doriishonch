"""Xavfsizlik filtri.

Platforma tibbiy maslahat bermaydi: doza, qabul qilish tartibi, tashxis yoki davolash
haqidagi savollar AI ga yuborilmaydi, AI javobidagi bunday jumlalar esa olib tashlanadi.
Shuningdek, reklama qonuniga zid boʻlgan "eng yaxshi / eng samarali" kabi
taqqoslovchi iboralar ham olib tashlanadi.
"""

import re

REFERRAL = (
    "Bu savol doza, qabul qilish tartibi yoki davolash haqida. Bunday maslahatni faqat shifokor "
    "yoki farmatsevt bera oladi, iltimos, ular bilan maslahatlashing. Men esa dorining roʻyxatdan "
    "oʻtgani, sertifikatlari va sifat maʼlumotlari haqida aytib bera olaman."
)

_APOS = re.compile(r"[ʻʼ'`‘’]")

# Savoldagi tibbiy maslahat soʻrovlari (oʻzbek lotin + rus)
_MEDICAL_Q = [
    r"\bdoza", r"\bdozirovka", r"necha\s*(ta|marta|mahal|kun|dona)", r"qancha\s*(ich|ber|qabul|vaqt)",
    r"\bkuniga\b", r"qanday\s*(ich|qabul|ist)", r"\bich(sam|ay|ish kerak|aymi|sa bo'ladimi)",
    r"qabul\s*qil(sam|ay|ish)", r"\bdavola", r"\btashxis", r"kasalligim", r"menga\s*qaysi",
    r"(bola|chaqaloq|go'dak)ga\s*(ber|mumkin)", r"homilador", r"emiz(ish|uvchi)",
    r"alkogol\s*bilan", r"birga\s*ich", r"o'rniga\s*ich",
    r"сколько", r"дозиров", r"как\s*принимать", r"можно\s*ли\s*(пить|принимать)", r"лечени",
]
_MEDICAL_Q_RE = re.compile("|".join(_MEDICAL_Q), re.IGNORECASE)

# Javobdagi doza koʻrsatmalari
_DOSE_OUT_RE = re.compile(
    r"(kuniga\s*\d|\d+\s*(marta|mahal)\b|\d+\s*(ta\s*)?(tabletka|kapsula)\s*(ich|qabul)"
    r"|(ichish|qabul qilish)\s*kerak|ichib\s*turing|dozani\s*(oshir|kamaytir))",
    re.IGNORECASE,
)

# Reklama qonuniga zid taqqoslash
_SUPERLATIVE_RE = re.compile(
    r"eng\s*(yaxshi|samarali|xavfsiz|ishonchli|sifatli|zo'r)|(\b100\s*%|to'liq)\s*kafolat",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    return _APOS.sub("'", text)


def is_medical_question(question: str) -> bool:
    return bool(_MEDICAL_Q_RE.search(_norm(question)))


def filter_answer(answer: str) -> tuple[str, bool]:
    """Javobdan xavfli jumlalarni olib tashlaydi. (toza_matn, oʻzgartirildimi) qaytaradi."""
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    kept, dose_removed, changed = [], False, False
    for s in sentences:
        n = _norm(s)
        if _DOSE_OUT_RE.search(n):
            dose_removed = changed = True
            continue
        if _SUPERLATIVE_RE.search(n):
            changed = True
            continue
        kept.append(s)
    text = " ".join(kept).strip()
    if dose_removed:
        text = (text + " " if text else "") + "Doza va qabul qilish tartibi boʻyicha shifokor yoki farmatsevt bilan maslahatlashing."
    if not text:
        text = REFERRAL
    return text, changed
