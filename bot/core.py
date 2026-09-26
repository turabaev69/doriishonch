"""DoriIshonch Telegram botining mantiqi (aiogram ga bogʻliq emas, shuning uchun testlanadi).

Brain har bir hodisani (matn, surat, joylashuv, tugma) qabul qiladi va javoblar roʻyxatini qaytaradi.
bot.py esa ularni Telegram xabarlari va tugmalariga aylantiradi.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

import httpx

# ------------------------------------------------------------------ menyu tugmalari
BTN_SCAN = "📷 Qutini tekshirish"
BTN_AI = "🤖 AI yordamchi"
BTN_NEAR = "📍 Yaqin dorixonalar"
BTN_SEARCH = "💊 Dori qidirish"
BTN_CHAIN = "🔗 Zanjir"
BTN_DEMO = "🧪 Demo kodlar"
BTN_HELP = "❓ Yordam"
BTN_POINTS = "⭐ Ballarim"
MENU = [[BTN_SCAN, BTN_AI], [BTN_NEAR, BTN_SEARCH], [BTN_POINTS, BTN_CHAIN], [BTN_DEMO, BTN_HELP]]
REPORT_REASONS = [("fake", "Qalbaki deb oʻylayman"), ("reused", "Quti qayta ishlatilgan"), ("no_effect", "Dori taʼsir qilmadi"),
                  ("packaging", "Qadoq shubhali"), ("price", "Narx gʻalati"), ("other", "Boshqa")]

ICON = {"ok": "✅", "warn": "⚠️", "warning": "⚠️", "danger": "⛔", "missing": "▫️", "info": "ℹ️", "unknown": "❔"}
KIND = {"scan": "Skanerlandi", "purchase": "Sotib olindi", "disputed": "Bahsli xarid", "report": "Inspektorga xabar"}
TOOL = {"verify_code": "qutini tekshirdi", "search_drug": "dorini qidirdi", "trust_card": "Ishonch kartasini oʻqidi",
        "find_analogs": "analoglarni topdi", "code_history": "zanjir tarixini koʻrdi",
        "nearby_pharmacies": "yaqin dorixonalarni topdi", "pharmacy_risks": "dorixonalar xavfini koʻrdi",
        "pharmacy_detail": "dorixona tafsilotini koʻrdi", "recent_alerts": "signallarni koʻrdi",
        "ledger_stats": "zanjir statistikasini koʻrdi", "customs_flags": "bojxona signallarini koʻrdi"}
MAX_HISTORY = 12


@dataclass
class Btn:
    text: str
    data: str | None = None  # callback
    url: str | None = None
    webapp: str | None = None  # Telegram Mini App (faqat https)


@dataclass
class Reply:
    text: str
    buttons: list[list[Btn]] | None = None
    menu: bool = False  # asosiy menyu klaviaturasini qoʻshish
    location_request: bool = False  # "joylashuvni yuborish" tugmasi
    delete_user_message: bool = False  # parol yozilgan xabarni oʻchirish


@dataclass
class Session:
    mode: str = ""  # "" | ai | search | inspector
    history: list[dict] = field(default_factory=list)
    lat: float | None = None
    lon: float | None = None
    pharmacy_id: int | None = None
    pharmacy_name: str = ""
    codes: dict[int, str] = field(default_factory=dict)  # scan_id → toʻliq kod
    parsed: dict[int, tuple[str, str]] = field(default_factory=dict)  # scan_id → (gtin, serial)
    box_for: int | None = None  # qadoq surati kutilayotgan scan_id
    token: str = ""
    role: str = ""
    demo: list[dict] = field(default_factory=list)


def esc(s) -> str:
    return html.escape(str(s or ""))


def som(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " soʻm"


def looks_like_code(t: str) -> bool:
    t = t.strip().replace("\x1d", "")  # GS ajratgich (Pythonda \x1d "boʻsh joy" hisoblanadi)
    return t.startswith(("(01)", "]d2")) or bool(re.match(r"^01\d{14}.{0,40}?21\w", t))


def looks_like_question(t: str) -> bool:
    t = t.strip().lower()
    q = ("qanday", "nima", "qayer", "qachon", "nega", "mumkinmi", "kerakmi", "bormi", "qaysi", "qanaqa", "?")
    return t.endswith("?") or len(t.split()) >= 4 or any(w in t for w in q)


def km(m: int) -> str:
    return f"{m} m" if m < 1000 else f"{m / 1000:.1f} km"


# ------------------------------------------------------------------ formatlash
def verdict_text(r: dict, pharmacy: str = "") -> str:
    lines = [f"{ICON.get(r['verdict'], '')} <b>{esc(r['headline'])}</b>"]
    if r.get("drug"):
        d = r["drug"]
        lines.append(f"💊 {esc(d['trade_name'])} — {esc(d['inn'])} {esc(d['strength'])}, {esc(d['manufacturer']['name'])}")
    if r.get("pack"):
        p = r["pack"]
        lines.append(f"📦 Seriya {esc(p.get('batch'))} · muddati {esc(str(p.get('expiry') or '')[:7])} · {esc(p.get('status_label'))}")
    if pharmacy:
        lines.append(f"🏪 {esc(pharmacy)}")
    lines += ["", esc(r["explanation"])]
    bad = [c for c in r.get("checks", []) if c["status"] in ("danger", "warning")]
    if bad:
        lines.append("")
        lines += [f"{ICON[c['status']]} {esc(c['text'])}" for c in bad]
    risk = r.get("ai_risk")
    if risk:
        label = {"past": "past xavf", "oʻrta": "oʻrtacha xavf", "yuqori": "yuqori xavf"}.get(risk["level"], risk["level"])
        lines += ["", f"🧠 <b>AI bahosi:</b> {label} ({risk['score']}/100)"]
        if risk["level"] != "past":
            lines += [f"   • {esc(x['text'])}" for x in risk.get("reasons", [])[:3]]
    hist = (r.get("ledger") or {}).get("history") or []
    if len(hist) > 1:
        lines += ["", f"🔗 Bu quti DoriIshonch zanjirida {len(hist) - 1} marta oldin skanerlangan."]
    if r.get("chain"):
        lines += ["", "<b>Qutining yoʻli</b>"]
        lines += [f"• {esc(e['label'])}: {esc(e['participant'])}, {esc(e['region'])} ({esc(e['at'][:10])})"
                  for e in r["chain"]]
    if r.get("dispense") and r["dispense"].get("category") == "controlled":
        lines += ["", f"🔒 {esc(r['dispense']['note'])}"]
    if r.get("advice"):
        lines += ["", "<b>Maslahat</b>"] + [f"• {esc(a)}" for a in r["advice"][:3]]
    rw = r.get("reward") or {}
    if rw.get("earned") or rw.get("pending"):
        head = f"+{rw['earned']} ball" if rw.get("earned") else f"+{rw['pending']} ball kutilmoqda"
        lines += ["", f"⭐ <b>{head}</b> · jami {rw.get('total', 0)} · {esc(rw.get('level'))}"]
        lines += [f"   {esc(m)}" for m in rw.get("messages", [])[:3]]
    elif rw.get("messages"):
        lines += ["", f"⭐ {esc(rw['messages'][0])}"]
    src = {"asl_belgisi": "Asl Belgisi (rasmiy)", "crowd": "xaridorlar skanerlari", "local": "DoriIshonch bazasi"}
    lines += ["", f"<i>Manba: {src.get(r.get('source'), r.get('source') or '')}"
                  f"{' · AI tushuntirdi' if r.get('ai_used') else ''}</i>"]
    return "\n".join(lines)


def verdict_buttons(r: dict) -> list[list[Btn]]:
    rows: list[list[Btn]] = []
    sid = r.get("scan_id")
    if sid and r["verdict"] in ("ok", "warning"):
        rows.append([Btn("🛒 Sotib oldim — zanjirga yozish", f"buy:{sid}")])
    if sid:
        rows.append([Btn("📸 Qadoqni AI tekshirsin", f"box:{sid}")])
    if sid:
        rows.append([Btn("🚨 Inspektorga xabar berish" if r["verdict"] != "ok" else "📣 Muammo bormi? Xabar bering",
                         f"report:{sid}")])
    extra = []
    if r.get("drug"):
        extra.append(Btn("💊 Dori haqida", f"drug:{r['drug']['id']}"))
    if sid and (r.get("parsed") or {}).get("serial"):
        extra.append(Btn("🔗 Zanjir tarixi", f"hist:{sid}"))
    if extra:
        rows.append(extra)
    return rows


def drug_buttons(drugs: list[dict]) -> list[list[Btn]]:
    return [[Btn(f"{'🇺🇿' if d['manufacturer']['is_local'] else '🌍'} {d['trade_name']} {d['strength']} — "
                 f"{som(d['price_uzs'])}", f"drug:{d['id']}")] for d in drugs[:6]]


def trust_card_text(card: dict, analogs: dict) -> str:
    d = card["drug"]
    lines = [f"<b>{esc(d['trade_name'])}</b> — {esc(d['inn'])} {esc(d['strength'])}, {esc(d['form'])}",
             f"{esc(d['manufacturer']['name'])}, {esc(d['manufacturer']['country'])} · {som(d['price_uzs'])}"
             f"{' · 📝 retsept bilan' if d.get('prescription_only') else ''}", "", "<b>Ishonch kartasi</b>"]
    for f in card["facts"]:
        extra = " <i>(ishlab chiqaruvchi maʼlumoti)</i>" if f.get("provided_by_manufacturer") else ""
        lines.append(f"{ICON.get(f['status'], '•')} <b>{esc(f['label'])}</b>: {esc(f['text'])}{extra}")
    local = [a for a in analogs.get("analogs", []) if a["drug"]["manufacturer"]["is_local"]]
    if local and not d["manufacturer"]["is_local"]:
        lines += ["", "<b>Mahalliy analoglar</b> (bir xil taʼsir qiluvchi modda)"]
        lines += [f"🇺🇿 {esc(a['drug']['trade_name'])} — {som(a['drug']['price_uzs'])} ({a['price_diff_pct']}%)"
                  for a in local[:3]]
    lines += ["", f"<i>{esc(card['disclaimer'])}</i>"]
    return "\n".join(lines)


def box_text(b: dict) -> str:
    head = {"ok": "✅ Qadoqda shubhali belgi topilmadi", "warning": "⚠️ Qadoqda eʼtibor talab qiladigan belgilar bor",
            "unknown": "❔ Suratdan aniq xulosa chiqmadi"}.get(b["overall"], b["overall"])
    lines = [f"<b>{head}</b>", "", esc(b["summary"])]
    lines += [f"{ICON.get(c['status'], '•')} <b>{esc(c['title'])}</b>: {esc(c['text'])}" for c in b.get("checks", [])]
    lines += ["", "<i>Bu AI signali, yakuniy xulosa emas. Shubha boʻlsa, dorixonadan hujjat soʻrang yoki "
                  "inspektorga xabar bering.</i>"]
    return "\n".join(lines)


def chat_text(r: dict, title: str = "🤖") -> str:
    steps = [TOOL.get(s["tool"], s["tool"]) for s in r.get("steps", [])]
    tail = f"\n\n<i>AI: {esc(', '.join(dict.fromkeys(steps)))}</i>" if steps else ""
    return f"{title} {esc(r['answer'])}{tail}"


def help_text(web_url: str = "") -> str:
    lines = [
        "<b>DoriIshonch</b> — dori qutisi haqiqiyligini tekshiruvchi bot.",
        "",
        "📷 <b>Qutini tekshirish:</b> qutidagi kvadrat kod (DataMatrix) va yonidagi GTIN/SN yozuvlari koʻrinadigan "
        "surat yuboring yoki kod matnini yozing. Bot qutining qayerdan kelgani, bojxonadan oʻtgani va "
        "oldin sotilmaganini tekshiradi.",
        "🤖 <b>AI yordamchi:</b> savolingizni oddiy tilda yozing: <i>“Paratsetamolning mahalliy analogi bormi?”</i>",
        "📍 <b>Yaqin dorixonalar:</b> joylashuvingizni yuboring. Dorixonani tanlasangiz, tekshiruv shu dorixonaga bogʻlanadi.",
        "💊 <b>Dori qidirish:</b> dori nomi → Ishonch kartasi va analoglar.",
        "🔗 <b>Zanjir:</b> barcha skanerlashlar yozilgan hash-zanjir butunmi.",
        "",
        "⭐ <b>Ballar:</b> har bir tekshiruv +10, dorixona koʻrsatilsa +5, “Sotib oldim” +20, missiya +30. "
        "Shubhali qutini topsangiz — inspektor tasdiqlaganda +50 va xabar uchun +100.",
        "",
        "Buyruqlar: /start /yordam /ball /missiyalar /reyting /mukofotlar /taxallus /demo /zanjir /stop",
        "Xodimlar: /kirish login parol · /signallar · /xavf · /copilot · /chiqish",
        "",
        "⚠️ Bot tibbiy maslahat bermaydi: doza va davolash boʻyicha shifokorga murojaat qiling.",
    ]
    if web_url:
        lines.insert(-2, f"Veb-ilova: {web_url}")
    return "\n".join(lines)


# ------------------------------------------------------------------ bot miyasi
class Brain:
    def __init__(self, http: httpx.AsyncClient, web_url: str = ""):
        self.http = http
        self.web_url = web_url.rstrip("/")
        self.sessions: dict[int, Session] = {}

    def s(self, uid: int) -> Session:
        return self.sessions.setdefault(uid, Session())

    @staticmethod
    def device(uid: int) -> str:
        return f"telegram-{uid}"  # backend uni hash qilib saqlaydi

    @property
    def webapp(self) -> str | None:
        return self.web_url if self.web_url.startswith("https://") else None

    # ------------------------------------------------ yordamchi soʻrovlar
    async def _post(self, path: str, uid: int | None = None, **kw) -> httpx.Response:
        return await self.http.post(path, headers=self._auth(uid), **kw)

    async def _get(self, path: str, uid: int | None = None, **kw) -> httpx.Response:
        return await self.http.get(path, headers=self._auth(uid), **kw)

    def _auth(self, uid: int | None) -> dict:
        s = self.sessions.get(uid) if uid is not None else None
        return {"Authorization": f"Bearer {s.token}"} if s and s.token else {}

    @staticmethod
    def _detail(r: httpx.Response, default: str = "Xato yuz berdi") -> str:
        try:
            d = r.json().get("detail")
            return d if isinstance(d, str) else default
        except Exception:
            return default

    # ------------------------------------------------ hodisalar
    async def start(self, uid: int) -> list[Reply]:
        s = self.s(uid)
        s.mode = ""
        text = ("Assalomu alaykum! Men <b>DoriIshonch AI</b> botiman.\n\n"
                "Dorixonada qutini <b>sotib olishdan oldin</b> tekshiring: qutining kvadrat kodi suratini yuboring "
                "yoki kod matnini yozing. Qutining yoʻli, bojxona va “oldin sotilganmi” — bir necha soniyada.\n\n"
                "Pastdagi menyudan tanlang. Birinchi marta boʻlsa, 🧪 <b>Demo kodlar</b> ni bosib koʻring.")
        out = [Reply(text, menu=True)]
        if self.webapp:
            out.append(Reply("Kamera bilan jonli skanerlash uchun ilovani oching:",
                             [[Btn("📱 Skanerni ochish", webapp=self.webapp)]]))
        return out

    async def on_text(self, uid: int, text: str) -> list[Reply]:
        s = self.s(uid)
        t = text.strip()
        low = t.lower()
        if low.startswith("/"):
            return await self.command(uid, t)
        if t == BTN_SCAN:
            s.mode = ""
            msg = ("📷 Qutidagi kvadrat kodni (DataMatrix) suratga oling: kod va yonidagi <b>GTIN</b>, <b>SN</b> "
                   "yozuvlari aniq koʻrinsin. Yoki kod matnini yuboring, masalan <code>(01)04780000000017(21)ABC…</code>")
            if s.pharmacy_name:
                msg += f"\n\n🏪 Dorixona: {esc(s.pharmacy_name)}"
            btns = [[Btn("📱 Kamerada skanerlash", webapp=self.webapp)]] if self.webapp else None
            return [Reply(msg, btns)]
        if t == BTN_AI:
            s.mode, s.history = "ai", []
            return [Reply("🤖 AI yordamchi tayyor. Savolingizni yozing, masalan:\n"
                          "• <i>Bu dorining mahalliy analogi bormi: Norvadin?</i>\n"
                          "• <i>Qutini qayta ishlatish sxemasi nima?</i>\n"
                          "• <i>Yaqin atrofda qaysi dorixonalar bor?</i>\n\nChiqish: /stop")]
        if t == BTN_NEAR:
            return [Reply("📍 Joylashuvingizni yuboring (pastdagi tugma).", location_request=True)]
        if t == BTN_SEARCH:
            s.mode = "search"
            return [Reply("💊 Dori nomini yozing (masalan, <i>Paratsetamol</i> yoki <i>Norvadin</i>).")]
        if t == BTN_CHAIN:
            return await self.chain()
        if t == BTN_DEMO:
            return await self.demo_list(uid)
        if t == BTN_HELP:
            return [Reply(help_text(self.web_url), menu=True)]
        if t == BTN_POINTS:
            return await self.points(uid)

        if looks_like_code(t):
            return await self.verify(uid, code=t)
        if s.mode == "inspector":
            return await self.ask(uid, t, inspector=True)
        if s.mode == "ai":
            return await self.ask(uid, t)
        if s.mode == "search" or not looks_like_question(t):
            out = await self.search(t)
            if out:
                return out
        return await self.ask(uid, t)

    async def command(self, uid: int, t: str) -> list[Reply]:
        s = self.s(uid)
        cmd, *args = t.split()
        cmd = cmd.split("@")[0].lower()
        if cmd == "/start":
            return await self.start(uid)
        if cmd in ("/yordam", "/help"):
            return [Reply(help_text(self.web_url), menu=True)]
        if cmd == "/stop":
            s.mode, s.history = "", []
            return [Reply("Suhbat tugadi. Menyudan tanlang.", menu=True)]
        if cmd == "/demo":
            return await self.demo_list(uid)
        if cmd == "/zanjir":
            return await self.chain()
        if cmd == "/qidir":
            return await self.search(" ".join(args)) or [Reply("Hech narsa topilmadi.")]
        if cmd in ("/ball", "/ballar"):
            return await self.points(uid)
        if cmd in ("/missiyalar", "/missiya"):
            return await self.missions(uid)
        if cmd == "/reyting":
            return await self.leaderboard(uid)
        if cmd == "/mukofotlar":
            return await self.catalog(uid)
        if cmd == "/taxallus":
            if not args:
                return [Reply("Foydalanish: <code>/taxallus Hushyor_Aziz</code> (reytingda koʻrinadi, ism-familiya yozmang)")]
            r = await self._post("/rewards/nickname", json={"device_id": self.device(uid), "nickname": " ".join(args)})
            return [Reply(f"✅ Taxallus: <b>{esc(r.json()['nickname'])}</b>" if r.status_code == 200 else "❌ " + self._detail(r))]
        if cmd == "/kirish":
            return await self.login(uid, args)
        if cmd == "/chiqish":
            s.token, s.role, s.mode = "", "", ""
            return [Reply("Xodim hisobidan chiqildi.", menu=True)]
        if cmd in ("/signallar", "/xavf", "/copilot"):
            if s.role not in ("inspector", "admin"):
                return [Reply("Bu buyruq inspektorlar uchun. Avval: /kirish login parol")]
            if cmd == "/signallar":
                return await self.alerts(uid)
            if cmd == "/xavf":
                return await self.risky(uid)
            s.mode, s.history = "inspector", []
            return [Reply("🕵️ Inspektor copiloti tayyor. Masalan: <i>“Qaysi dorixonani birinchi tekshiray?”</i>\n"
                          "Chiqish: /stop")]
        return [Reply("Nomaʼlum buyruq. /yordam")]

    async def on_location(self, uid: int, lat: float, lon: float) -> list[Reply]:
        s = self.s(uid)
        s.lat, s.lon = lat, lon
        r = await self._get("/pharmacies/nearby", params={"lat": lat, "lon": lon})
        if r.status_code != 200:
            return [Reply(self._detail(r, "Dorixonalarni topib boʻlmadi."), menu=True)]
        rows = r.json()
        if not rows:
            return [Reply("Yaqin atrofda dorixona topilmadi.", menu=True)]
        lines = ["📍 <b>Yaqin dorixonalar</b>", ""]
        btns = []
        for x in rows[:6]:
            p = x["pharmacy"]
            lic = "" if p.get("license_ok", True) else " ⚠️ litsenziya muammosi"
            lines.append(f"🏪 <b>{esc(p['name'])}</b> — {km(x['distance_m'])}{lic}\n    {esc(p.get('address') or p['region'])}")
            btns.append([Btn(f"✅ {p['name'][:40]} — shu yerdaman", f"ph:{p['id']}")])
        lines += ["", "Qaysi dorixonada boʻlsangiz, tanlang: tekshiruvlar shu dorixonaga bogʻlanadi."]
        return [Reply("\n".join(lines), btns), Reply("Menyu:", menu=True)]

    async def on_photo(self, uid: int, data: bytes) -> list[Reply]:
        s = self.s(uid)
        files = {"file": ("photo.jpg", data, "image/jpeg")}
        if s.box_for is not None:
            sid = s.box_for
            s.box_for = None
            gtin, serial = s.parsed.get(sid, ("", ""))
            r = await self._post("/ai/inspect-box", files=files, data={"gtin": gtin, "serial": serial})
            if r.status_code != 200:
                return [Reply("📸 " + self._detail(r, "Qadoqni tahlil qilib boʻlmadi."))]
            return [Reply(box_text(r.json()))]
        form = {"mode": "before", "device_id": self.device(uid)}
        if s.pharmacy_id:
            form["pharmacy_id"] = str(s.pharmacy_id)
        r = await self._post("/verify/image", files=files, data=form)
        if r.status_code == 200:
            return self._verdict(uid, r.json())
        # Kod oʻqilmadi: hech boʻlmasa dorini aniqlaymiz
        sc = await self._post("/scan", files=files)
        res = sc.json() if sc.status_code == 200 else {}
        if res.get("matches"):
            return [Reply("Qutining kodi oʻqilmadi, lekin dori aniqlandi. Aynan shu qutini tekshirish uchun "
                          "kvadrat kod va yonidagi GTIN/SN yozuvlari aniq koʻrinadigan surat yuboring.",
                          drug_buttons(res["matches"]))]
        return [Reply("📷 " + self._detail(r, "Suratdan kod oʻqilmadi.") +
                      "\n\nMaslahat: kodni yaqinroqdan, yorugʻ joyda, qiyshaytirmasdan suratga oling yoki kod "
                      "matnini qoʻlda yozing.")]

    async def on_callback(self, uid: int, data: str) -> tuple[list[Reply], str | None]:
        s = self.s(uid)
        kind, _, val = data.partition(":")
        if kind == "buy":
            code = s.codes.get(int(val))
            if not code:
                return [], "Kodni qayta yuboring."
            return await self.verify(uid, code=code, mode="after"), None
        if kind == "report":
            btns = [[Btn(label, f"rr:{val}:{key}")] for key, label in REPORT_REASONS]
            return [Reply("📣 Nima boʻldi? Sababni tanlang (anonim). Inspektor tasdiqlasa: +20 ball va +100 mukofot.", btns)], None
        if kind == "rr":
            sid, _, reason = val.partition(":")
            r = await self._post("/reports", json={"scan_id": int(sid), "note": "Telegram bot orqali", "reason": reason})
            if r.status_code != 200:
                return [], self._detail(r)
            return [Reply("✅ " + esc(r.json().get("message", "Yuborildi")))], None
        if kind == "lb":
            return await self.leaderboard(uid), None
        if kind == "rw":
            return await self.catalog(uid), None
        if kind == "ms":
            return await self.missions(uid), None
        if kind == "rd":
            r = await self._post("/rewards/redeem", json={"device_id": self.device(uid), "reward_key": val})
            if r.status_code != 200:
                return [], self._detail(r)
            d = r.json()
            return [Reply(f"🎉 <b>{esc(d['title'])}</b>\nKod: <code>{esc(d['code'])}</code>\n<i>{esc(d['note'])}</i>")], None
        if kind == "box":
            s.box_for = int(val)
            return [Reply("📸 Qutining oldi yoki yon tomonini suratga olib yuboring: nom, seriya va muddat "
                          "yozuvlari koʻrinsin. AI ularni kod maʼlumoti bilan solishtiradi va ochilganlik "
                          "belgilarini qidiradi.")], None
        if kind == "drug":
            return await self.drug(int(val)), None
        if kind == "hist":
            gtin, serial = s.parsed.get(int(val), ("", ""))
            return await self.history(gtin, serial), None
        if kind == "ph":
            r = await self._get("/pharmacies")
            p = next((x for x in r.json() if x["id"] == int(val)), None) if r.status_code == 200 else None
            s.pharmacy_id, s.pharmacy_name = (p["id"], p["name"]) if p else (None, "")
            if not p:
                return [], "Dorixona topilmadi"
            return [Reply(f"🏪 Dorixona tanlandi: <b>{esc(p['name'])}</b>\nEndi qutining kodini yuboring.")], None
        if kind == "demo":
            if not s.demo:
                await self.demo_list(uid)
            d = s.demo[int(val)] if int(val) < len(s.demo) else None
            if not d:
                return [], "Demo topilmadi"
            if d.get("pharmacy_id"):
                s.pharmacy_id, s.pharmacy_name = d["pharmacy_id"], d.get("pharmacy_name", "")
            head = Reply(f"🧪 <b>{esc(d['title'])}</b>\nKod: <code>{esc(d['code_display'])}</code>")
            return [head] + await self.verify(uid, code=d["code"], mode=d.get("mode", "before")), None
        return [], None

    # ------------------------------------------------ amallar
    async def verify(self, uid: int, code: str, mode: str = "before") -> list[Reply]:
        s = self.s(uid)
        body = {"code": code, "mode": mode, "device_id": self.device(uid), "pharmacy_id": s.pharmacy_id}
        r = await self._post("/verify", json=body)
        if r.status_code != 200:
            return [Reply(self._detail(r, "Kodni tekshirib boʻlmadi."))]
        res = r.json()
        if res.get("scan_id"):
            s.codes[res["scan_id"]] = code
        return self._verdict(uid, res)

    def _verdict(self, uid: int, res: dict) -> list[Reply]:
        s = self.s(uid)
        sid = res.get("scan_id")
        p = res.get("parsed") or {}
        if sid and p.get("gtin"):
            s.parsed[sid] = (p["gtin"], p.get("serial") or "")
            if sid not in s.codes and p.get("serial"):
                s.codes[sid] = f"01{p['gtin']}21{p['serial']}"
        return [Reply(verdict_text(res, s.pharmacy_name), verdict_buttons(res) or None)]

    async def ask(self, uid: int, text: str, inspector: bool = False) -> list[Reply]:
        s = self.s(uid)
        s.history.append({"role": "user", "content": text[:2000]})
        s.history = s.history[-MAX_HISTORY:]
        body = {"messages": s.history, "device_id": self.device(uid), "pharmacy_id": s.pharmacy_id,
                "lat": s.lat, "lon": s.lon}
        r = await self._post("/ai/inspector" if inspector else "/ai/chat", uid=uid, json=body)
        if r.status_code != 200:
            s.history.pop()
            return [Reply(self._detail(r, "AI javob bera olmadi."))]
        res = r.json()
        s.history.append({"role": "assistant", "content": res["answer"]})
        return [Reply(chat_text(res, "🕵️" if inspector else "🤖"))]

    async def search(self, q: str) -> list[Reply]:
        if not q.strip():
            return []
        r = await self._get("/search", params={"q": q})
        results = r.json().get("results", []) if r.status_code == 200 else []
        if not results:
            return []
        return [Reply(f"🔎 “{esc(q)}” boʻyicha topildi:", drug_buttons(results))]

    async def drug(self, drug_id: int) -> list[Reply]:
        card = await self._get(f"/drugs/{drug_id}")
        if card.status_code != 200:
            return [Reply("Dori topilmadi.")]
        analogs = (await self._get(f"/drugs/{drug_id}/analogs")).json()
        kb = drug_buttons([a["drug"] for a in analogs.get("analogs", [])]) or None
        return [Reply(trust_card_text(card.json(), analogs), kb)]

    async def history(self, gtin: str, serial: str) -> list[Reply]:
        if not (gtin and serial):
            return [Reply("Bu kod uchun zanjir tarixi yoʻq.")]
        rows = (await self._get("/ledger/code", params={"gtin": gtin, "serial": serial})).json()
        if not rows:
            return [Reply("Zanjirda bu quti boʻyicha yozuv yoʻq.")]
        lines = [f"🔗 <b>Zanjir tarixi</b> · SN {esc(serial)}", ""]
        for b in rows[-10:]:
            lines.append(f"#{b['index']} {KIND.get(b['kind'], b['kind'])} · {esc(b['created_at'][:16].replace('T', ' '))}"
                         f"{' · ' + esc(b['pharmacy']) if b.get('pharmacy') else ''}\n    <code>{b['hash'][:16]}…</code>")
        return [Reply("\n".join(lines))]

    async def chain(self) -> list[Reply]:
        st = (await self._get("/ledger/verify")).json()
        latest = (await self._get("/ledger/latest", params={"limit": 5})).json()
        head = (f"✅ <b>Zanjir butun</b>: {st['blocks']} blok" if st["ok"]
                else f"⛔ <b>Zanjir buzilgan</b>: blok #{st['broken_at']} ({esc(st['reason'])})")
        lines = [head, f"<code>{esc(st['last_hash'])}</code>", "",
                 "Har bir skanerlash blok boʻlib yoziladi va oldingi blokning SHA-256 hashini saqlaydi. "
                 "Birorta yozuvni oʻzgartirish butun zanjirni buzadi.", "", "<b>Oxirgi bloklar</b>"]
        lines += [f"#{b['index']} {KIND.get(b['kind'], b['kind'])} · {esc(b['serial'])} · {esc(b.get('region'))}"
                  for b in latest]
        return [Reply("\n".join(lines))]

    async def demo_list(self, uid: int) -> list[Reply]:
        r = await self._get("/demo/codes")
        s = self.s(uid)
        s.demo = r.json() if r.status_code == 200 else []
        if not s.demo:
            return [Reply("Demo kodlar mavjud emas.")]
        btns = [[Btn(f"{ICON.get(d['expected'], '•')} {d['title'][:58]}", f"demo:{i}")] for i, d in enumerate(s.demo)]
        return [Reply("🧪 <b>Demo stsenariylar</b>\nHar birini bosing: bot haqiqiy tekshiruvni bajaradi "
                      "(asl quti, qayta ishlatilgan quti, bojxonadan oʻtmagan, klon kod va boshqalar).", btns)]

    async def points(self, uid: int) -> list[Reply]:
        r = await self._get("/rewards/me", params={"device_id": self.device(uid)})
        if r.status_code != 200:
            return [Reply(self._detail(r))]
        w = r.json()
        lv = w["level"]
        bar_n = int(round(lv["progress"] * 10))
        bar = "▰" * bar_n + "▱" * (10 - bar_n)
        nxt = f"{lv['next_name']} ({lv['next_min']})" if lv.get("next_name") else "eng yuqori daraja"
        rank = f"  · 🏆 #{w['rank']}" if w.get("rank") else ""
        lines = [f"⭐ <b>{w['points']} ball</b> · {esc(w['nickname'])}{rank}",
                 f"{lv['icon']} {esc(lv['name'])} → {esc(nxt)}", bar,
                 f"🔥 {w['streak']} kun ketma-ket · 📅 bugun {w['today']['earned']}/{w['today']['cap']} · ⏳ kutilmoqda {w['pending']}"]
        got = [f"{b['icon']} {esc(b['title'])}" for b in w["badges"] if b["earned"]]
        if got:
            lines += ["", "<b>Nishonlar:</b> " + ", ".join(got)]
        if w["history"]:
            lines += ["", "<b>Oxirgi ballar</b>"]
            for h in w["history"][:5]:
                mark = "⏳ " if h["status"] == "pending" else "✕ " if h["status"] == "rejected" else ""
                lines.append(f"{mark}{'+' if h['points'] > 0 else ''}{h['points']} — {esc(h['note'] or h['label'])}")
        if w.get("flagged"):
            lines += ["", "⚠️ Gʻayrioddiy faollik: ballar vaqtincha toʻxtatilgan."]
        btns = [[Btn("🚩 Missiyalar", "ms:0"), Btn("🏆 Reyting", "lb:0")], [Btn("🎁 Mukofotlar", "rw:0")]]
        return [Reply("\n".join(lines), btns)]

    async def missions(self, uid: int) -> list[Reply]:
        r = await self._get("/missions", params={"device_id": self.device(uid)})
        rows = r.json() if r.status_code == 200 else []
        if not rows:
            return [Reply("Hozircha missiya yoʻq.")]
        lines = ["🚩 <b>Haftalik missiyalar</b>", "Tekshiruvlar kam boʻlgan dorixonalarda istalgan qutini skanerlang.", ""]
        btns = []
        for m in rows:
            lines.append(f"{'✅' if m['done'] else '▫️'} <b>{esc(m['pharmacy'])}</b> — {esc(m['region'])} · +{m['points']} ball"
                         f"\n    {esc(m.get('address') or '')}")
            if not m["done"]:
                btns.append([Btn(f"🏪 {m['pharmacy'][:40]} — shu yerdaman", f"ph:{m['pharmacy_id']}")])
        return [Reply("\n".join(lines), btns or None)]

    async def leaderboard(self, uid: int) -> list[Reply]:
        rows = (await self._get("/rewards/leaderboard", params={"device_id": self.device(uid)})).json()
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = ["🏆 <b>Reyting · 30 kun</b>", ""]
        for x in [x for x in rows if x["rank"] <= 10 or x["me"]]:
            me = " ← siz" if x["me"] else ""
            lines.append(f"{medal.get(x['rank'], str(x['rank']) + '.')} {esc(x['name'])} — <b>{x['points']}</b>{me}")
        lines += ["", "Taxallus qoʻyish: /taxallus Hushyor_Aziz"]
        return [Reply("\n".join(lines))]

    async def catalog(self, uid: int) -> list[Reply]:
        items = (await self._get("/rewards/catalog")).json()["items"]
        lines = ["🎁 <b>Mukofotlar</b> (hamkorlar demo)", ""]
        lines += [f"{i['icon']} {esc(i['title'])} — <b>{i['points']}</b> ball · {esc(i['partner'])}" for i in items]
        return [Reply("\n".join(lines), [[Btn(f"{i['icon']} {i['points']} — {i['title'][:36]}", f"rd:{i['key']}")] for i in items])]

    async def login(self, uid: int, args: list[str]) -> list[Reply]:
        s = self.s(uid)
        if len(args) != 2:
            return [Reply("Foydalanish: <code>/kirish login parol</code>\n(Xabar darhol oʻchiriladi.)",
                          delete_user_message=bool(args))]
        r = await self._post("/auth/login", json={"username": args[0], "password": args[1]})
        if r.status_code != 200:
            return [Reply("❌ Login yoki parol notoʻgʻri.", delete_user_message=True)]
        d = r.json()
        s.token, s.role = d["token"], d["role"]
        extra = "\n/signallar — shubhali skanerlashlar\n/xavf — xavfli dorixonalar\n/copilot — AI inspektor yordamchisi" \
            if d["role"] in ("inspector", "admin") else ""
        return [Reply(f"✅ Xush kelibsiz, <b>{esc(d['display_name'])}</b> ({esc(d['role_label'])}).{extra}\n\n"
                      "🔒 Parolli xabaringiz xavfsizlik uchun oʻchirildi.", delete_user_message=True)]

    async def alerts(self, uid: int) -> list[Reply]:
        r = await self._get("/inspector/alerts", uid=uid, params={"limit": 10})
        if r.status_code != 200:
            return [Reply(self._detail(r))]
        rows = r.json()
        if not rows:
            return [Reply("Signal yoʻq.")]
        lines = ["🚨 <b>Oxirgi signallar</b> (isbot emas, tekshiruv uchun signal)", ""]
        for a in rows:
            lines.append(f"{ICON.get(a['verdict'], '•')} {esc(a['drug'])} · SN {esc(a['serial'])}\n"
                         f"    {esc(', '.join(a['reasons']))}\n    {esc(a['pharmacy'] or '—')}, {esc(a['region'])}"
                         f"{' · 📣 xaridor xabar berdi' if a['reported'] else ''}")
        return [Reply("\n".join(lines))]

    async def risky(self, uid: int) -> list[Reply]:
        r = await self._get("/inspector/pharmacies", uid=uid)
        if r.status_code != 200:
            return [Reply(self._detail(r))]
        rows = [x for x in r.json() if x["level"] in ("yuqori", "oʻrta")][:6] or r.json()[:3]
        level = {"yuqori": "🔴 yuqori", "oʻrta": "🟠 oʻrta", "past": "🟢 past"}
        lines = ["🏪 <b>Xavf signallari boʻyicha dorixonalar</b>", ""]
        for x in rows:
            p = x["pharmacy"]
            sig = "; ".join(x.get("signals", [])[:2])
            lines.append(f"{level.get(x['level'], x['level'])} <b>{esc(p['name'])}</b>, {esc(p['region'])}\n"
                         f"    {esc(sig)}{' · ML: gʻayrioddiy' if x.get('ml_outlier') else ''}")
        lines += ["", "<i>Signal — ayblov emas. /copilot dan “nima uchun?” deb soʻrang.</i>"]
        return [Reply("\n".join(lines))]
