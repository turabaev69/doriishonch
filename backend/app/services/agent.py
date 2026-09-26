"""AI agentlar (Claude tool use).

Ikki agent:
  * xaridor yordamchisi — oʻzbek tilida savol-javob; kodni tekshiradi, dorini topadi, Ishonch kartasi,
    analoglar, quti tarixi (zanjir) va yaqin dorixonalarni vositalar (tools) orqali oladi;
  * inspektor copiloti — "Qaysi dorixonalarni birinchi tekshirish kerak?" kabi savollarga
    xavf signallari, ogohlantirishlar, zanjir statistikasi va bojxona belgilari asosida javob beradi.

Agent faqat vositalar qaytargan maʼlumotga tayanadi. Qaysi vositalar ishlatilgani javob bilan birga
qaytariladi (shaffoflik: hakam va foydalanuvchi AI nimaga asoslanganini koʻradi).
"""

import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from ..config import settings
from ..models import ConsumerScan, CustomsLine, LedgerBlock
from . import ai, catalog, codes, ledger, places, risk, safety, trace

log = logging.getLogger(__name__)
MAX_STEPS = 6


# ---------------------------------------------------------------- vositalar

def _brief(d) -> dict:
    return {"id": d.id, "trade_name": d.trade_name, "inn": d.inn, "strength": d.strength, "form": d.form,
            "manufacturer": d.manufacturer.name, "country": d.manufacturer.country,
            "local": d.manufacturer.is_local, "price_uzs": d.price_uzs,
            "dispense": getattr(d, "dispense_category", None)}


def t_verify_code(db: Session, ctx: dict, code: str = "", gtin: str = "", serial: str = "", mode: str = "before"):
    res = trace.verify(db, raw_code=code or None, gtin=gtin or None, serial=serial or None, mode=mode,
                       pharmacy_id=ctx.get("pharmacy_id"), device_id=ctx.get("device_id"), record=False)
    return {"verdict": res.verdict, "headline": res.headline, "source": res.source,
            "checks": [{"status": c.status, "title": c.title, "text": c.text} for c in res.checks],
            "advice": res.advice, "drug": _brief(res.drug) if res.drug else None}


def t_search_drug(db: Session, ctx: dict, query: str):
    return [_brief(d) for d in catalog.search(db, query, limit=6)]


def t_trust_card(db: Session, ctx: dict, drug_id: int):
    d = catalog.get_drug(db, int(drug_id))
    if not d:
        return {"error": "dori topilmadi"}
    return {"drug": _brief(d), "facts": [{"n": i + 1, "label": f.label, "status": f.status, "text": f.text,
                                          "by_manufacturer": f.provided_by_manufacturer, "source": f.source_url}
                                         for i, f in enumerate(catalog.trust_facts(d))]}


def t_analogs(db: Session, ctx: dict, drug_id: int):
    d = catalog.get_drug(db, int(drug_id))
    if not d:
        return {"error": "dori topilmadi"}
    return [{**_brief(a.drug), "price_diff_pct": a.price_diff_pct, "valid_gmp": a.has_valid_gmp,
             "quality_alerts": a.quality_alert_count} for a in catalog.analogs(db, d)]


def t_code_history(db: Session, ctx: dict, gtin: str, serial: str):
    return [{"block": b.id, "kind": b.kind, "at": b.created_at.isoformat(), "pharmacy": b.pharmacy.name if b.pharmacy else "",
             "region": b.region} for b in ledger.history(db, gtin, serial)]


def t_nearby(db: Session, ctx: dict, lat: float | None = None, lon: float | None = None):
    lat, lon = lat or ctx.get("lat"), lon or ctx.get("lon")
    if lat is None or lon is None:
        return {"error": "joylashuv nomaʼlum: foydalanuvchidan joylashuvga ruxsat soʻrang"}
    try:
        return [{"id": p.id, "name": p.name, "address": p.address, "distance_m": int(dist)}
                for p, dist in places.nearby(db, float(lat), float(lon))[:8]]
    except places.PlacesError as e:
        return {"error": str(e)}


def t_pharmacy_risks(db: Session, ctx: dict):
    return [{"id": r.pharmacy.id, "name": r.pharmacy.name, "region": r.pharmacy.region, "level": r.level,
             "ml_outlier": r.ml_outlier, "anomaly": r.anomaly, "reuse": r.reuse, "unregistered_sales": r.unregistered,
             "clone": r.clone, "sell_through": round(r.sell_through, 2), "reports": r.reports, "signals": r.signals}
            for r in risk.compute(db)]


def t_pharmacy_detail(db: Session, ctx: dict, pharmacy_id: int):
    r = next((x for x in risk.compute(db) if x.pharmacy.id == int(pharmacy_id)), None)
    return risk.facts_text(r) if r else {"error": "dorixona topilmadi"}


def t_recent_alerts(db: Session, ctx: dict, days: int = 7, region: str = "", limit: int = 30):
    since = datetime.utcnow() - timedelta(days=int(days))
    q = db.query(ConsumerScan).filter(ConsumerScan.verdict.in_(["danger", "warning"]), ConsumerScan.at >= since)
    if region:
        q = q.filter(ConsumerScan.region == region)
    rows = q.order_by(ConsumerScan.at.desc()).limit(min(int(limit), 100)).all()
    return [{"at": s.at.isoformat(), "verdict": s.verdict, "reasons": s.reasons.split("|") if s.reasons else [],
             "pharmacy": s.pharmacy.name if s.pharmacy else "", "region": s.region, "reported": s.reported,
             "note": s.report_note} for s in rows]


def t_ledger_stats(db: Session, ctx: dict, days: int = 30):
    since = datetime.utcnow() - timedelta(days=int(days))
    blocks = db.query(LedgerBlock).filter(LedgerBlock.created_at >= since).all()
    by_kind = Counter(b.kind for b in blocks)
    by_region = Counter(b.region or "nomaʼlum" for b in blocks)
    chain = ledger.verify_chain(db)
    return {"days": days, "blocks": len(blocks), "by_kind": dict(by_kind), "by_region": dict(by_region.most_common(10)),
            "chain_ok": chain.ok, "total_blocks": chain.blocks}


def t_customs_flags(db: Session, ctx: dict):
    rows = db.query(CustomsLine).filter(CustomsLine.flags != "").all()
    return [{"declaration": l.declaration.number, "importer": l.declaration.importer.name,
             "origin": l.declaration.origin_country, "description": l.description,
             "matched_drug": l.matched_drug.trade_name if l.matched_drug else None, "quantity": l.quantity,
             "flags": l.flags.split("|")} for l in rows]


def _schema(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


Tool = tuple[str, str, dict, Callable]

CONSUMER_TOOLS: list[Tool] = [
    ("verify_code", "Dori qutisidagi DataMatrix kodni (yoki GTIN + seriya) tekshiradi: reestr, quti holati, sotilganmi, "
     "bojxona, DoriIshonch zanjiri. mode: before (sotib olishdan oldin) yoki after (sotib olgandan keyin).",
     _schema({"code": {"type": "string"}, "gtin": {"type": "string"}, "serial": {"type": "string"},
              "mode": {"type": "string", "enum": ["before", "after"]}}), t_verify_code),
    ("search_drug", "Dori nomi yoki taʼsir qiluvchi modda boʻyicha qidiradi.",
     _schema({"query": {"type": "string"}}, ["query"]), t_search_drug),
    ("trust_card", "Dori boʻyicha rasmiy faktlar: reestr, GMP, sifat ogohlantirishlari, markirovka, ekvivalentlik.",
     _schema({"drug_id": {"type": "integer"}}, ["drug_id"]), t_trust_card),
    ("find_analogs", "Taʼsir qiluvchi moddasi, dozasi va shakli bir xil analoglar (mahalliylari oldin), narx farqi bilan.",
     _schema({"drug_id": {"type": "integer"}}, ["drug_id"]), t_analogs),
    ("code_history", "Quti (GTIN + seriya) boʻyicha DoriIshonch zanjiridagi barcha skanerlash va xaridlar.",
     _schema({"gtin": {"type": "string"}, "serial": {"type": "string"}}, ["gtin", "serial"]), t_code_history),
    ("nearby_pharmacies", "Foydalanuvchi joylashuvi yaqinidagi haqiqiy dorixonalar (OpenStreetMap).",
     _schema({"lat": {"type": "number"}, "lon": {"type": "number"}}), t_nearby),
]

INSPECTOR_TOOLS: list[Tool] = [
    ("pharmacy_risks", "Barcha dorixonalar boʻyicha xavf darajasi, ML gʻayrioddiylik va signallar.", _schema({}), t_pharmacy_risks),
    ("pharmacy_detail", "Bitta dorixonaning batafsil koʻrsatkichlari.", _schema({"pharmacy_id": {"type": "integer"}}, ["pharmacy_id"]),
     t_pharmacy_detail),
    ("recent_alerts", "Soʻnggi xavfli/diqqat natijali xaridor skanerlashlari (hudud boʻyicha filtr mumkin).",
     _schema({"days": {"type": "integer"}, "region": {"type": "string"}, "limit": {"type": "integer"}}), t_recent_alerts),
    ("ledger_stats", "DoriIshonch zanjiri statistikasi: bloklar turi va hudud boʻyicha, zanjir butunligi.",
     _schema({"days": {"type": "integer"}}), t_ledger_stats),
    ("customs_flags", "Bojxona deklaratsiyalaridagi ogohlantirishlar (reestrda yoʻq, litsenziya, mamlakat mos emas).",
     _schema({}), t_customs_flags),
    ("code_history", "Quti boʻyicha zanjir tarixi.", _schema({"gtin": {"type": "string"}, "serial": {"type": "string"}},
                                                           ["gtin", "serial"]), t_code_history),
]

CONSUMER_SYSTEM = """Sen DoriIshonch AI yordamchisisan: dorixonadagi xaridorga dori va uning qutisi ishonchli \
ekanini tekshirishda yordam berasan. Oʻzbek tilida (lotin), qisqa va aniq javob ber.

Qoidalar:
1. Faktlarni FAQAT vositalar (tools) natijasidan ol. Taxmin qilma, oʻzingdan fakt qoʻshma.
2. Foydalanuvchi kod yuborsa yoki quti haqida soʻrasa, verify_code ni chaqir. Xulosani (verdict) oʻzgartirma.
3. Doza, qabul qilish tartibi, tashxis, davolash haqida maslahat BERMA: shifokor yoki farmatsevtga yoʻnaltir.
4. Dorilarni "eng yaxshi", "eng samarali" deb baholama; faqat faktlarni ayt.
5. Xavf boʻlsa, aniq ayt va nima qilishni ("sotib olmang", "xabar bering") tavsiya qil.
6. 6 jumladan oshmasin."""

INSPECTOR_SYSTEM = """Sen farmatsevtika inspektori uchun AI tahlilchisan (DoriIshonch). Oʻzbek tilida javob ber.

Qoidalar:
1. Raqamlarni FAQAT vositalardan ol. Har bir xulosani raqam bilan asosla.
2. Signallar qoidabuzarlik isboti emas: "tekshirish tavsiya etiladi" deb yoz, hech kimni aybdor deb eʼlon qilma.
3. Kerak boʻlsa, tekshiruv ustuvorligini roʻyxat qilib ber (dorixona, sabab, nimani tekshirish kerak).
4. 10 jumladan oshmasin."""


# ---------------------------------------------------------------- agent sikli

def _tool_specs(tools: list[Tool]) -> list[dict]:
    return [{"name": n, "description": d, "input_schema": s} for n, d, s, _ in tools]


def _short(result: Any) -> str:
    if isinstance(result, list):
        return f"{len(result)} ta natija"
    if isinstance(result, dict):
        if "error" in result:
            return f"xato: {result['error']}"
        if "verdict" in result:
            return f"xulosa: {result['verdict']} — {result.get('headline', '')}"
        return ", ".join(list(result.keys())[:4])
    return str(result)[:80]


def run(db: Session, messages: list[dict], tools: list[Tool], system: str, ctx: dict | None = None,
        client=None) -> dict:
    """Claude bilan tool-use sikli. {answer, steps, ai_used} qaytaradi."""
    ctx = ctx or {}
    client = client or ai._get_client()
    by_name = {n: f for n, _, _, f in tools}
    convo = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("content")]
    steps = []
    for _ in range(MAX_STEPS):
        resp = client.messages.create(model=settings.anthropic_model, max_tokens=1024, system=system,
                                      tools=_tool_specs(tools), messages=convo)
        blocks = list(resp.content)
        convo.append({"role": "assistant", "content": [_block_dict(b) for b in blocks]})
        if resp.stop_reason != "tool_use":
            text = "".join(getattr(b, "text", "") for b in blocks if getattr(b, "type", "") == "text").strip()
            return {"answer": text, "steps": steps, "ai_used": True}
        results = []
        for b in blocks:
            if getattr(b, "type", "") != "tool_use":
                continue
            fn = by_name.get(b.name)
            try:
                out = fn(db, ctx, **(b.input or {})) if fn else {"error": f"nomaʼlum vosita {b.name}"}
            except Exception as e:  # vosita xatosi agentni toʻxtatmasin
                log.warning("Vosita %s xatosi: %s", b.name, e)
                out = {"error": str(e)}
            steps.append({"tool": b.name, "input": b.input or {}, "summary": _short(out)})
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": json.dumps(out, ensure_ascii=False, default=str)[:12000]})
        convo.append({"role": "user", "content": results})
    return {"answer": "Savol juda murakkab boʻlib chiqdi. Iltimos, aniqroq soʻrang.", "steps": steps, "ai_used": True}


def _block_dict(b) -> dict:
    t = getattr(b, "type", "")
    if t == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    return {"type": "text", "text": getattr(b, "text", "")}


# ---------------------------------------------------------------- tashqi funksiyalar

def consumer_chat(db: Session, messages: list[dict], ctx: dict) -> dict:
    last = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if safety.is_medical_question(last):
        return {"answer": safety.REFERRAL, "steps": [], "ai_used": False, "blocked": True}
    if settings.ai_enabled:
        try:
            out = run(db, messages, CONSUMER_TOOLS, CONSUMER_SYSTEM, ctx)
            out["answer"] = safety.filter_answer(out["answer"])[0] if out["answer"] else out["answer"]
            return out
        except Exception as e:
            log.warning("Agent xatosi: %s", e)
    return _consumer_fallback(db, last, ctx)


def inspector_chat(db: Session, messages: list[dict]) -> dict:
    if settings.ai_enabled:
        try:
            return run(db, messages, INSPECTOR_TOOLS, INSPECTOR_SYSTEM)
        except Exception as e:
            log.warning("Copilot xatosi: %s", e)
    rows = t_pharmacy_risks(db, {})
    top = [r for r in rows if r["level"] != "past"][:5]
    lines = ["AI kaliti ulanmagan, shuning uchun avtomatik xulosa:"]
    for r in top:
        lines.append(f"• {r['name']} ({r['region']}) — {r['level']}: {'; '.join(r['signals'][:2]) or 'ML gʻayrioddiylik'}")
    if not top:
        lines.append("Hozircha yuqori yoki oʻrta xavfli dorixona yoʻq.")
    return {"answer": "\n".join(lines), "steps": [{"tool": "pharmacy_risks", "input": {}, "summary": f"{len(rows)} ta natija"}],
            "ai_used": False}


def _consumer_fallback(db: Session, text: str, ctx: dict) -> dict:
    """AI kalitsiz: kodni yoki dori nomini taniydigan oddiy yordamchi."""
    p = codes.parse(text.strip())
    if p.gtin and p.serial:
        r = t_verify_code(db, ctx, code=text.strip())
        bad = [c["text"] for c in r["checks"] if c["status"] in ("danger", "warning")]
        answer = f"{r['headline']}. " + (" ".join(bad[:2]) if bad else "") + (f" {r['advice'][0]}" if r["advice"] else "")
        return {"answer": answer.strip(), "steps": [{"tool": "verify_code", "input": {"code": "…"}, "summary": _short(r)}],
                "ai_used": False}
    found = t_search_drug(db, ctx, text)
    if found:
        d = found[0]
        local = [a for a in t_analogs(db, ctx, d["id"]) if a["local"] and a["id"] != d["id"]]
        answer = (f"{d['trade_name']} — {d['inn']} {d['strength']}, {d['manufacturer']} ({d['country']}). "
                  + (f"Mahalliy analoglar: {', '.join(a['trade_name'] for a in local[:3])}. " if local else "")
                  + "Batafsil faktlar uchun dori sahifasini oching yoki qutini skanerlang.")
        return {"answer": answer, "steps": [{"tool": "search_drug", "input": {"query": text}, "summary": f"{len(found)} ta natija"}],
                "ai_used": False}
    return {"answer": "AI kaliti ulanmagan. Qutidagi kodni yuboring yoki dori nomini yozing: men uni tekshiraman.",
            "steps": [], "ai_used": False}
