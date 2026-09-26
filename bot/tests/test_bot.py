import pytest

from conftest import run
from core import (BTN_AI, BTN_CHAIN, BTN_DEMO, BTN_NEAR, BTN_SCAN, BTN_SEARCH, Brain, looks_like_code,
                  looks_like_question, verdict_text)

UID = 1001


def texts(replies):
    return "\n".join(r.text for r in replies)


def callbacks(replies):
    return [b.data for r in replies for row in (r.buttons or []) for b in row if b.data]


def test_heuristics():
    assert looks_like_code("(01)04780000000017(21)ABC123")
    assert looks_like_code("010478000000001721ABCDEF")
    assert not looks_like_code("Norvadin")
    assert looks_like_question("Paratsetamolning analogi bormi?")
    assert looks_like_question("qayerdan olsam boladi")
    assert not looks_like_question("Norvadin")


def test_start_menu_and_webapp(brain: Brain):
    out = run(brain.start(UID))
    assert out[0].menu and "DoriIshonch" in out[0].text
    assert out[1].buttons[0][0].webapp == "https://demo.trycloudflare.com"
    scan = run(brain.on_text(UID, BTN_SCAN))
    assert "GTIN" in scan[0].text and scan[0].buttons[0][0].webapp
    assert run(brain.on_text(UID, BTN_NEAR))[0].location_request


def test_http_web_url_has_no_webapp_button():
    import httpx
    b = Brain(httpx.AsyncClient(base_url="http://x"), "http://localhost:3000")
    assert b.webapp is None


def test_all_demo_scenarios_through_bot(brain: Brain):
    lst = run(brain.on_text(UID, BTN_DEMO))
    cbs = callbacks(lst)
    assert len(cbs) >= 10
    for i, cb in enumerate(cbs):
        replies, alert = run(brain.on_callback(UID, cb))
        assert alert is None, cb
        expected = brain.s(UID).demo[i]["expected"]
        icon = {"ok": "✅", "warning": "⚠️", "danger": "⛔"}.get(expected)
        if icon:
            assert replies[1].text.startswith(icon), (brain.s(UID).demo[i]["title"], replies[1].text[:80])


def test_verify_code_then_buy_then_reuse_detected(brain: Brain):
    lst = run(brain.demo_list(UID))
    demo = brain.s(UID).demo
    ok = next(d for d in demo if d["expected"] == "ok" and d["mode"] == "before")
    brain.s(UID).pharmacy_id = ok["pharmacy_id"]
    out = run(brain.on_text(UID, ok["code"]))
    assert "AI bahosi" in out[0].text
    cbs = callbacks(out)
    buy = next(c for c in cbs if c.startswith("buy:"))
    assert any(c.startswith("box:") for c in cbs) and any(c.startswith("hist:") for c in cbs)
    after, alert = run(brain.on_callback(UID, buy))
    assert alert is None and after
    # boshqa xaridor boshqa dorixonada shu kodni skanerlasa — qayta ishlatilgan quti signali
    # (2 soat ichida shu dorixonadagi qayta skan xaridorning oʻzi deb hisoblanadi)
    other = next(d["pharmacy_id"] for d in demo if d["pharmacy_id"] and d["pharmacy_id"] != ok["pharmacy_id"])
    brain.s(UID + 1).pharmacy_id = other
    again = run(brain.on_text(UID + 1, ok["code"]))
    assert again[0].text.startswith(("⛔", "⚠️")), again[0].text[:120]
    hist, _ = run(brain.on_callback(UID, next(c for c in cbs if c.startswith("hist:"))))
    assert "Zanjir tarixi" in hist[0].text and "Sotib olindi" in hist[0].text


def test_report_and_box_without_ai(brain: Brain):
    out = run(brain.on_text(UID, "(01)04780000009999(21)NOTEXIST00001"))
    cbs = callbacks(out)
    rep = next(c for c in cbs if c.startswith("report:"))
    ask, _ = run(brain.on_callback(UID, rep))
    done, _ = run(brain.on_callback(UID, callbacks(ask)[0]))
    assert "inspektor" in done[0].text.lower()
    box = next(c for c in cbs if c.startswith("box:"))
    ask, _ = run(brain.on_callback(UID, box))
    assert "suratga" in ask[0].text
    res = run(brain.on_photo(UID, b"\xff\xd8not-really-a-jpeg"))
    assert "Surat oʻqilmadi" in res[0].text  # buzilgan surat — tushunarli xabar
    assert brain.s(UID).box_for is None
    # Haqiqiy surat: Claude kalitsiz ham oʻz modelimiz (PackNet) javob beradi
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (320, 200), (200, 60, 60)).save(buf, "JPEG")
    run(brain.on_callback(UID, box))
    res = run(brain.on_photo(UID, buf.getvalue()))
    assert "Qadoq" in res[0].text or "Model" in res[0].text, res[0].text


def test_photo_without_code(brain: Brain):
    res = run(brain.on_photo(UID, b"\xff\xd8not-really-a-jpeg"))
    assert res and res[0].text


def test_search_and_trust_card(brain: Brain):
    run(brain.on_text(UID, BTN_SEARCH))
    out = run(brain.on_text(UID, "Paratsetamol"))
    cbs = callbacks(out)
    assert cbs and cbs[0].startswith("drug:")
    card, _ = run(brain.on_callback(UID, cbs[0]))
    assert "Ishonch kartasi" in card[0].text
    assert "tibbiy" in card[0].text.lower() or "shifokor" in card[0].text.lower()


def test_ai_assistant_mode_keeps_history(brain: Brain):
    run(brain.on_text(UID, BTN_AI))
    a = run(brain.on_text(UID, "Paratsetamolning mahalliy analogi bormi?"))
    assert a[0].text.startswith("🤖")
    assert len(brain.s(UID).history) == 2
    # tibbiy savol bloklanadi
    b = run(brain.on_text(UID, "Bolamga paratsetamoldan qancha doza beray?"))
    assert "shifokor" in b[0].text.lower()
    run(brain.on_text(UID, "/stop"))
    assert brain.s(UID).mode == "" and brain.s(UID).history == []


def test_location_nearby(brain: Brain, monkeypatch):
    from app.models import Participant
    from app.services import places

    def fake_nearby(db, lat, lon, radius=1500):
        ph = db.query(Participant).filter(Participant.kind == "pharmacy").limit(2).all()
        return [(p, 120.0 + i * 900) for i, p in enumerate(ph)]

    monkeypatch.setattr(places, "nearby", fake_nearby)
    out = run(brain.on_location(UID, 41.31, 69.28))
    assert "Yaqin dorixonalar" in out[0].text and "1.0 km" in out[0].text
    pick = callbacks(out)[0]
    sel, _ = run(brain.on_callback(UID, pick))
    assert "Dorixona tanlandi" in sel[0].text and brain.s(UID).pharmacy_id
    assert run(brain.on_location(UID, 51.5, -0.1))[0].text  # Oʻzbekistondan tashqari — xato xabari


def test_chain(brain: Brain):
    out = run(brain.on_text(UID, BTN_CHAIN))
    assert "Zanjir butun" in out[0].text


def test_staff_login_and_inspector_tools(brain: Brain):
    bad = run(brain.on_text(UID, "/kirish inspektor xato"))
    assert bad[0].delete_user_message and "notoʻgʻri" in bad[0].text
    assert "inspektorlar uchun" in run(brain.on_text(UID, "/signallar"))[0].text
    ok = run(brain.on_text(UID, "/kirish inspektor inspektor123"))
    assert ok[0].delete_user_message and "Xush kelibsiz" in ok[0].text
    assert "signallar" in run(brain.on_text(UID, "/signallar"))[0].text.lower()
    assert "dorixonalar" in run(brain.on_text(UID, "/xavf"))[0].text
    run(brain.on_text(UID, "/copilot"))
    ans = run(brain.on_text(UID, "Qaysi dorixonani birinchi tekshiray?"))
    assert ans[0].text.startswith("🕵️")
    run(brain.on_text(UID, "/chiqish"))
    assert brain.s(UID).token == ""


def test_verdict_text_escapes_html():
    r = {"verdict": "danger", "headline": "<b>x</b>", "explanation": "a & b", "checks": [], "source": "local"}
    t = verdict_text(r)
    assert "&lt;b&gt;x&lt;/b&gt;" in t and "a &amp; b" in t


def test_points_flow_in_bot(brain: Brain):
    from core import BTN_POINTS
    uid = 7007
    demo = run(brain.demo_list(uid)) and brain.s(uid).demo
    ok = next(d for d in demo if d["expected"] == "ok" and d["mode"] == "before")
    brain.s(uid).pharmacy_id = ok["pharmacy_id"]
    out = run(brain.on_text(uid, ok["code"]))
    assert "ball" in out[0].text  # yangi quti yoki allaqachon ball olingan — xabar baribir koʻrinadi
    pts = run(brain.on_text(uid, BTN_POINTS))
    assert "ball" in pts[0].text and "ms:0" in callbacks(pts)
    ms, _ = run(brain.on_callback(uid, "ms:0"))
    assert "missiyalar" in ms[0].text.lower()
    lb, _ = run(brain.on_callback(uid, "lb:0"))
    assert "Reyting" in lb[0].text
    rw, _ = run(brain.on_callback(uid, "rw:0"))
    assert any(c.startswith("rd:") for c in callbacks(rw))
    _, alert = run(brain.on_callback(uid, callbacks(rw)[-1]))
    assert alert and "yetarli" in alert  # ball yetmaydi
    nick = run(brain.on_text(uid, "/taxallus Bot_Posbon"))
    assert "Bot_Posbon" in nick[0].text


def test_report_with_reason(brain: Brain):
    uid = 7008
    out = run(brain.on_text(uid, "(01)04780000009999(21)NOTEXIST00077"))
    rep = next(c for c in callbacks(out) if c.startswith("report:"))
    ask, _ = run(brain.on_callback(uid, rep))
    reasons = callbacks(ask)
    assert len(reasons) == 6 and reasons[0].startswith("rr:")
    done, alert = run(brain.on_callback(uid, reasons[2]))
    assert alert is None and "inspektor" in done[0].text.lower()
