"""Claude API bilan ishlaydigan AI xizmatlari.

ANTHROPIC_API_KEY boʻlmasa, tizim AI siz rejimda ishlaydi: tushuntirish faktlardan
shablon asosida yigʻiladi, surat tanish esa oʻchiriladi. Shu tufayli demo internet
yoki kalit boʻlmasa ham ishlaydi.
"""

import base64
import json
import logging
import re

from ..config import settings
from ..models import Drug
from ..schemas import Fact
from . import safety

log = logging.getLogger(__name__)

TOPICS = {
    "sifat": "Sifat va ishlab chiqarish",
    "ekvivalentlik": "Originalga tengligi",
    "haqiqiylik": "Haqiqiylik va qalbakilik",
    "narx": "Narx",
    "nojoya": "Nojoʻya taʼsirlar",
    "tibbiy": "Doza va davolash (bloklangan)",
    "boshqa": "Boshqa",
}

_TOPIC_KEYWORDS = {
    "ekvivalentlik": ["ekvivalent", "original", "bir xil", "farqi", "farq", "teng", "o'rnini", "analog", "bioekviv"],
    "haqiqiylik": ["qalbaki", "haqiqiy", "asl", "markirov", "soxta", "kontrafakt"],
    "sifat": ["sifat", "gmp", "sertifikat", "ishonchli", "ishonch", "zavod", "standart", "ishlab chiqar"],
    "narx": ["narx", "arzon", "qimmat", "so'm", "pul"],
    "nojoya": ["nojo'ya", "yon ta'sir", "zarar", "xavfli", "allergiya"],
}

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def classify_topic(question: str) -> str:
    if safety.is_medical_question(question):
        return "tibbiy"
    q = safety._norm(question).lower()
    for topic, words in _TOPIC_KEYWORDS.items():
        if any(w in q for w in words):
            return topic
    return "boshqa"


# ---------------------------------------------------------------- tushuntirish

SYSTEM_PROMPT = """Sen DoriIshonch platformasining yordamchisisan. Vazifang: foydalanuvchiga dori haqidagi \
RASMIY FAKTLARNI oddiy oʻzbek tilida (lotin yozuvida) tushuntirish.

Qatʼiy qoidalar:
1. Faqat quyida berilgan raqamlangan faktlardan foydalan. Bilmagan narsangni yozma, taxmin qilma.
2. Har bir daʼvodan keyin manba raqamini kvadrat qavsda qoʻy, masalan [2].
3. Javob 5 jumladan oshmasin.
4. Doza, qabul qilish tartibi, tashxis, davolash yoki dori almashtirish boʻyicha maslahat BERMA. \
Bunday savolga "shifokor yoki farmatsevt bilan maslahatlashing" deb javob ber.
5. Hech qachon ball, reyting yoki "eng yaxshi", "eng samarali", "eng xavfsiz" kabi soʻzlarni ishlatma. \
Dorilarni bir-biridan yaxshiroq yoki yomonroq deb baholama.
6. "Ishlab chiqaruvchi taqdim etgan" deb belgilangan faktni aytganda buni albatta eslat.
7. Fakt "yoʻq" yoki "topilmadi" boʻlsa, buni ochiq ayt: maʼlumot yoʻqligi dori yomon degani emas, \
faqat bazada tasdiq yoʻqligini bildiradi."""


def _facts_block(drug: Drug, facts: list[Fact]) -> str:
    lines = [
        f"Dori: {drug.trade_name} ({drug.inn} {drug.strength}, {drug.form}), "
        f"ishlab chiqaruvchi: {drug.manufacturer.name}, {drug.manufacturer.country}.",
        "Faktlar:",
    ]
    for i, f in enumerate(facts, 1):
        extra = " (ishlab chiqaruvchi taqdim etgan)" if f.provided_by_manufacturer else ""
        lines.append(f"[{i}] {f.label}: {f.text}{extra} Holat: {f.status}.")
    return "\n".join(lines)


def _relevant(facts: list[Fact], topic: str) -> list[int]:
    order = {
        "sifat": ["gmp", "registry", "quality_alert"],
        "ekvivalentlik": ["evidence", "nti", "registry"],
        "haqiqiylik": ["marking", "quality_alert", "registry"],
        "narx": ["registry", "gmp"],
        "nojoya": ["quality_alert", "nti"],
        "boshqa": ["registry", "gmp", "quality_alert", "evidence"],
    }.get(topic, ["registry", "gmp"])
    return [i for key in order for i, f in enumerate(facts, 1) if f.key == key]


def _template_answer(drug: Drug, facts: list[Fact], topic: str) -> str:
    idx = _relevant(facts, topic)
    parts = []
    for i in idx[:4]:
        f = facts[i - 1]
        suffix = " Bu maʼlumotni ishlab chiqaruvchi taqdim etgan." if f.provided_by_manufacturer else ""
        body = f.text if f.text.endswith(".") else f.text + "."
        parts.append(f"{f.label} — {body}{suffix} [{i}]")
    if topic == "narx":
        parts.append(f"Bazadagi narx: {drug.price_uzs:,} soʻm ({drug.pack_size}).".replace(",", " "))
    if topic == "nojoya":
        parts.append("Nojoʻya taʼsirlar roʻyxati dori yoʻriqnomasida keltiriladi; savollar boʻlsa, shifokor yoki farmatsevtga murojaat qiling.")
    return " ".join(parts) or "Bu savol boʻyicha bazada fakt topilmadi."


def explain(drug: Drug, facts: list[Fact], question: str) -> dict:
    topic = classify_topic(question)
    if topic == "tibbiy":
        return {"answer": safety.REFERRAL, "sources": [], "blocked": True, "ai_used": False, "topic": topic}

    ai_used = False
    answer = None
    if settings.ai_enabled:
        try:
            msg = _get_client().messages.create(
                model=settings.anthropic_model,
                max_tokens=600,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"{_facts_block(drug, facts)}\n\nSavol: {question}"}],
            )
            answer = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            ai_used = True
        except Exception as e:  # tarmoq yoki kalit xatosi: demoni toʻxtatmaymiz
            log.warning("Claude API xatosi, shablon rejimiga oʻtildi: %s", e)
    if not answer:
        answer = _template_answer(drug, facts, topic)

    answer, _ = safety.filter_answer(answer)
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 0 < int(n) <= len(facts)})
    sources = [facts[i - 1] for i in cited]
    return {"answer": answer, "sources": sources, "blocked": False, "ai_used": ai_used, "topic": topic}


# ---------------------------------------------------------------- skanerlash

_GS1_GTIN = re.compile(r"(?:\(01\)|^01|\x1d01)(\d{14})")


def parse_marking_code(code: str) -> str | None:
    """Asl Belgisi / GS1 DataMatrix matnidan GTIN ni ajratadi."""
    code = code.strip()
    m = _GS1_GTIN.search(code)
    if m:
        return m.group(1)
    digits = re.sub(r"\D", "", code)
    if 8 <= len(digits) <= 14 and digits == code:
        return digits
    return None


def decode_datamatrix(image_bytes: bytes) -> str | None:
    """pylibdmtx oʻrnatilgan boʻlsa, suratdagi DataMatrix kodni oʻqiydi (ixtiyoriy)."""
    try:
        import io

        from PIL import Image
        from pylibdmtx.pylibdmtx import decode
    except Exception:
        return None
    try:
        res = decode(Image.open(io.BytesIO(image_bytes)), max_count=1, timeout=3000)
        return res[0].data.decode("utf-8", "ignore") if res else None
    except Exception:
        return None


VISION_PROMPT = """Rasmda dori qadogʻi bor. Qadoqdagi matndan quyidagilarni ajrat va FAQAT JSON qaytar:
{"trade_name": "...", "inn": "...", "strength": "...", "form": "...", "manufacturer": "..."}
inn — taʼsir qiluvchi modda (xalqaro nomi, lotin yozuvida). Topilmagan maydonga null yoz."""


def extract_from_image(image_bytes: bytes, media_type: str) -> dict | None:
    if not settings.ai_enabled:
        return None
    try:
        msg = _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                 "data": base64.b64encode(image_bytes).decode()}},
                    {"type": "text", "text": VISION_PROMPT},
                ],
            }],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else None
    except Exception as e:
        log.warning("Surat tanishda xato: %s", e)
        return None


# ---------------------------------------------------------------- quti tekshiruvini tushuntirish

VERDICT_SYSTEM = """Sen dorixonadagi xaridorga yordam beradigan yordamchisan. Senga dori qutisini \
tekshirish natijasi (qoidalar tizimi chiqargan xulosa va dalillar) beriladi.

Vazifang: natijani oddiy oʻzbek tilida (lotin), 2-4 qisqa jumlada tushuntirish.
Qoidalar:
1. Xulosani OʻZGARTIRMA va yumshatma. "danger" boʻlsa, xavfni aniq ayt.
2. Faqat berilgan dalillardan foydalan, oʻzingdan fakt qoʻshma.
3. Tibbiy maslahat, doza yoki davolash haqida gapirma.
4. Hech kimni jinoyatda ayblama: "boʻlishi mumkin", "belgisi" kabi soʻzlarni ishlat.
5. Oxirida xaridor nima qilishi kerakligini bitta jumlada ayt (berilgan maslahatlardan)."""


def _verdict_facts(res) -> str:
    lines = [f"Xulosa: {res.verdict}. Sarlavha: {res.headline}."]
    if res.drug:
        lines.append(f"Dori: {res.drug.trade_name} ({res.drug.inn} {res.drug.strength}).")
    for c in res.checks:
        lines.append(f"- [{c.status}] {c.title}: {c.text}")
    if res.advice:
        lines.append("Maslahatlar: " + " ".join(res.advice))
    return "\n".join(lines)


def _verdict_template(res) -> str:
    bad = [c for c in res.checks if c.status in ("danger", "warning")]
    if not bad and getattr(res, "source", "") == "crowd":
        np_ = getattr(res, "new_product", None) or {}
        text = ("Bu mahsulot bizning dori bazamizda hali yoʻq, shuning uchun uning yoʻlini (bojxona, dorixona, sotuv) "
                "tekshirib boʻlmadi. Kod toʻgʻri tuzilgan. ")
        text += ("Mahsulot bazaga qoʻshildi — inspektor uni rasmiy reestr bilan solishtiradi."
                 if np_ else "Rasmiy tekshiruv uchun Asl Belgisi ilovasidan ham foydalaning.")
        return text
    if not bad:
        good = [c for c in res.checks if c.status == "ok" and c.key in ("in_stock", "sale_registered", "customs", "produced")]
        text = "Quti roʻyxatdan oʻtgan, seriya raqami tizimda bor va qayta sotilmagan. " + " ".join(c.text for c in good[:2])
    else:
        titles = ", ".join(c.title.lower() for c in bad)
        text = f"Tekshiruvda {'muammo' if len(bad) == 1 else f'{len(bad)} ta muammo'} topildi: {titles}."
    if res.advice:
        text += " " + res.advice[0]
    return text.strip()


def explain_verdict(res) -> tuple[str, bool]:
    """(matn, ai_ishlatildimi). Xulosani emas, faqat tushuntirishni AI yozadi."""
    if settings.ai_enabled and res.verdict != "unknown":
        try:
            msg = _get_client().messages.create(
                model=settings.anthropic_model, max_tokens=400, system=VERDICT_SYSTEM,
                messages=[{"role": "user", "content": _verdict_facts(res)}],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            if text:
                return safety.filter_answer(text)[0], True
        except Exception as e:
            log.warning("Claude API xatosi (verdict): %s", e)
    return _verdict_template(res), False


# ---------------------------------------------------------------- suratdan kod oʻqish

CODE_VISION_PROMPT = """Rasmda dori qutisi. Kvadrat DataMatrix kod yonida odatda odam oʻqiy oladigan matn boʻladi:
GTIN (14 raqam), SN yoki seriya raqami (13 belgi), partiya (Lot/Серия) va yaroqlilik muddati.
Faqat JSON qaytar: {"gtin": "...", "serial": "...", "batch": "...", "expiry": "YYYY-MM-DD", "trade_name": "..."}
Topilmaganiga null yoz. Raqamlarni taxmin qilma: aniq koʻrinmasa null yoz."""


def read_code_from_image(image_bytes: bytes, media_type: str) -> dict | None:
    if not settings.ai_enabled:
        return None
    try:
        msg = _get_client().messages.create(
            model=settings.anthropic_model, max_tokens=300,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.b64encode(image_bytes).decode()}},
                {"type": "text", "text": CODE_VISION_PROMPT},
            ]}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else None
    except Exception as e:
        log.warning("Suratdan kod oʻqishda xato: %s", e)
        return None


# ---------------------------------------------------------------- bojxona qatorini reestrga moslash

MATCH_SYSTEM = """Bojxona deklaratsiyasidagi tovar tavsifini dori reestridagi nomzodlardan biriga moslashtir.
Taʼsir qiluvchi modda, doza va dori shakli toʻliq mos kelishi shart. Ishonching komil boʻlmasa, null qaytar.
Faqat JSON: {"drug_id": <son yoki null>, "reason": "qisqa izoh"}"""


def match_customs_line_ai(description: str, candidates: list[Drug]) -> tuple[int | None, str]:
    if not settings.ai_enabled or not candidates:
        return None, ""
    listing = "\n".join(f"{d.id}: {d.trade_name} — {d.inn} {d.strength} {d.form}, {d.manufacturer.name} "
                        f"({d.manufacturer.country})" for d in candidates)
    try:
        msg = _get_client().messages.create(
            model=settings.anthropic_model, max_tokens=200, system=MATCH_SYSTEM,
            messages=[{"role": "user", "content": f"Tavsif: {description}\n\nNomzodlar:\n{listing}"}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        data = json.loads(m.group(0)) if m else {}
        did = data.get("drug_id")
        if did in {d.id for d in candidates}:
            return did, data.get("reason", "")
    except Exception as e:
        log.warning("Bojxona moslashtirishda xato: %s", e)
    return None, ""


# ---------------------------------------------------------------- inspektor uchun xulosa

INSPECTOR_SYSTEM = """Sen farmatsevtika inspektoriga yordam beradigan tahlilchisan. Senga dorixona boʻyicha \
signallar va raqamlar beriladi. 3-5 jumlada oʻzbek tilida xulosa yoz: nima gʻayrioddiy, qaysi signal eng \
muhim va tekshiruvda nimaga eʼtibor berish kerak. Faqat berilgan raqamlardan foydalan. Hech kimni aybdor \
deb eʼlon qilma: bu tekshiruvni rejalashtirish uchun signal, isbot emas."""


def summarize_pharmacy(facts: str, fallback: str) -> tuple[str, bool]:
    if settings.ai_enabled:
        try:
            msg = _get_client().messages.create(
                model=settings.anthropic_model, max_tokens=500, system=INSPECTOR_SYSTEM,
                messages=[{"role": "user", "content": facts}],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
            if text:
                return text, True
        except Exception as e:
            log.warning("Claude API xatosi (inspektor): %s", e)
    return fallback, False


# ---------------------------------------------------------------- qadoq ekspertizasi (vision)

BOX_PROMPT = """Rasmda dori qutisi. Sen qadoq ekspertisan. Rasmdagi qutini sinchiklab koʻrib, FAQAT JSON qaytar:
{
 "printed_trade_name": "qutidagi savdo nomi yoki null",
 "printed_batch": "qutiga bosilgan seriya/partiya (Lot, Серия) yoki null",
 "printed_expiry": "yaroqlilik muddati YYYY-MM yoki YYYY-MM-DD yoki null",
 "tamper_signs": ["ochilganlik belgilari: yirtilgan himoya yorligʻi, yelim izi, qayta yopish, ezilgan chetlar ..."],
 "print_issues": ["bosma sifati muammolari: xira matn, rang farqi, imlo xatosi, notekis shrift ..."],
 "code_visible": true/false,
 "image_quality": "yaxshi | oʻrtacha | yomon",
 "summary_uz": "1-2 jumla oʻzbek tilida"
}
Faqat rasmda aniq koʻringan narsalarni yoz. Aniq koʻrinmasa, roʻyxatni boʻsh qoldir. Taxmin qilma."""


def inspect_box(image_bytes: bytes, media_type: str) -> dict | None:
    """Qutining suratini Claude vision bilan koʻzdan kechiradi. Kalit boʻlmasa None."""
    if not settings.ai_enabled:
        return None
    msg = _get_client().messages.create(
        model=settings.anthropic_model, max_tokens=700,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                         "data": base64.b64encode(image_bytes).decode()}},
            {"type": "text", "text": BOX_PROMPT},
        ]}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}
