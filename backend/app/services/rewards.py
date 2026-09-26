"""DoriIshonch ballari: xaridorlarni qutini tekshirishga jalb qilish.

Nima uchun: har bir xaridor skanerlashi — tizim uchun bepul "tekshiruv nuqtasi". Qancha koʻp odam
skanerlasa, qayta ishlatilgan quti va nusxalangan kodlar shuncha tez aniqlanadi.

Ball qoidalari (bir qurilma = bitta anonim hamyon, ism va telefon soʻralmaydi):
  scan      +10  roʻyxatdagi quti sotib olishdan oldin skanerlandi (har bir quti uchun bir marta)
  pharmacy  +5   dorixona koʻrsatilgan (maʼlumot qimmatliroq: xavf xaritasiga tushadi)
  purchase  +20  "Sotib oldim" — quti xaridorga bogʻlandi
  mission   +30  haftalik missiya: tekshiruvlar kam boʻlgan dorixonada skanerlash
  catch     +50  shubhali quti topildi — inspektor TASDIQLAGANDAN keyin hisoblanadi
  report    +20  inspektorga xabar — tasdiqlansa hisoblanadi, bounty +100 qoʻshiladi

Firibgarlikka qarshi:
  * bitta quti uchun bir qurilmaga bir marta; bitta qutiga 24 soatda koʻpi bilan 3 qurilma ball oladi
  * kunlik chegara (DAILY_CAP) — skaner/dorixona/xarid ballari uchun
  * soatiga VELOCITY_LIMIT dan koʻp skanerlash — hamyon tekshiruvga tushadi, ball berilmaydi
  * "qalbaki topdim" ballari faqat inspektor tasdigʻidan keyin (soxta kod terib ball yigʻib boʻlmaydi)
  * ball yechish (mukofot) productionda telefon tasdigʻi bilan (SMS OTP) — bu yerda demo
"""

from __future__ import annotations

import hashlib
import re
import secrets
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import ConsumerScan, Participant, PointEvent, Redemption, Wallet
from . import coverage, risk
from ..config import settings

POINTS = {"scan": 10, "pharmacy": 5, "purchase": 20, "mission": 30, "catch": 50, "report": 20, "bounty": 100}
DAILY_CAP = 150
VELOCITY_LIMIT = 40  # skanerlash / soat
BOX_DEVICES_PER_DAY = 3
CAPPED_KINDS = ("scan", "pharmacy", "purchase")
CATCH_KEYS = {"serial_unknown", "key_mismatch", "already_claimed", "double_claim", "unregistered", "withdrawn",
              "batch_alert", "expired", "already_sold", "clone", "no_customs", "price_too_low"}

LEVELS = [(0, "Yangi xaridor", "🌱"), (100, "Hushyor xaridor", "👀"), (300, "Faol tekshiruvchi", "🔎"),
          (700, "Dori himoyachisi", "🛡️"), (1500, "Dori posboni", "🏅")]

BADGES = {
    "first_scan": ("🎯", "Birinchi skaner", "Birinchi qutini tekshirdingiz"),
    "buyer": ("🛒", "Ongli xaridor", "Sotib olgan qutini zanjirga bogʻladingiz"),
    "explorer": ("🗺️", "Sayyoh", "3 ta turli dorixonada tekshirdingiz"),
    "regular": ("📅", "Odat", "5 xil kunda tekshirdingiz"),
    "missioner": ("🚩", "Missioner", "Birinchi missiyani bajardingiz"),
    "guardian": ("🛡️", "Posbon", "Topgan shubhali qutingiz inspektor tomonidan tasdiqlandi"),
}

CATALOG = [
    {"key": "bp_check", "title": "Bepul qon bosimini oʻlchash", "partner": "Hamkor dorixonalar (demo)",
     "points": 100, "icon": "🩺"},
    {"key": "discount5", "title": "Keyingi xaridga 5% chegirma", "partner": "Hamkor dorixonalar (demo)",
     "points": 150, "icon": "🏷️"},
    {"key": "mobile5k", "title": "Mobil hisobga 5 000 soʻm", "partner": "Mobil operator (demo)",
     "points": 300, "icon": "📱"},
    {"key": "vitamin", "title": "Vitamin C sovgʻa", "partner": "Hamkor ishlab chiqaruvchi (demo)",
     "points": 500, "icon": "🎁"},
]

MISSION_COUNT = 4


# ------------------------------------------------------------------ yordamchilar
def wallet(db: Session, device: str) -> Wallet:
    w = db.get(Wallet, device)
    if not w:
        w = Wallet(device_hash=device)
        db.add(w)
        db.flush()
    return w


def _exists(db: Session, **kw) -> bool:
    q = db.query(PointEvent.id)
    for k, v in kw.items():
        q = q.filter(getattr(PointEvent, k) == v)
    return q.first() is not None


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def week_id(now: datetime) -> str:
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def display_name(w: Wallet | None, device: str) -> str:
    if w and w.nickname:
        return w.nickname
    return "Xaridor-" + device[:4].upper()


# ------------------------------------------------------------------ missiyalar
_cache: dict[str, tuple[datetime, list]] = {}
CACHE_TTL = timedelta(minutes=10)


def _picked(db: Session, now: datetime) -> list:
    wk = week_id(now)
    cache_key = f"{wk}:{settings.pharmacy_region}"
    hit = _cache.get(cache_key)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    rows = [row for row in risk.compute(db, now) if coverage.in_scope(row.pharmacy.region)]
    weight = {"yuqori": 3, "oʻrta": 2, "past": 0}

    def score(r):  # xavf + kam qamrov: scans/received qanchalik kam boʻlsa, shuncha muhim
        coverage = r.scans / r.received if r.received else 0
        return weight.get(r.level, 0) + max(0.0, 1.0 - coverage) + r.anomaly * 0.5
    picked = [r.pharmacy.id for r in sorted(rows, key=score, reverse=True)[:MISSION_COUNT]]
    _cache.clear()
    _cache[cache_key] = (now, picked)
    return picked


def missions(db: Session, now: datetime | None = None, device: str = "") -> list[dict]:
    """Haftalik missiyalar: xavf modeli va skanerlash qamrovi boʻyicha tanlangan dorixonalar.

    Maqsad — AI xavf signali bor, lekin xaridorlar tekshiruvi kam joylarga "sirli xaridor" oqimini yoʻnaltirish.
    Matn neytral: dorixona hech qachon "xavfli" deb koʻrsatilmaydi (tuhmat va ogohlantirib qoʻyishdan saqlanish).
    """
    now = now or datetime.utcnow()
    wk = week_id(now)
    week_start = _day_start(now - timedelta(days=now.weekday()))
    out = []
    for pid in _picked(db, now):
        p = db.get(Participant, pid)
        if not p:
            continue
        mid = f"{wk}:{p.id}"
        done = bool(device) and _exists(db, device_hash=device, kind="mission", ref=mid)
        scanners = (db.query(func.count(func.distinct(ConsumerScan.device_hash)))
                    .filter(ConsumerScan.pharmacy_id == p.id, ConsumerScan.at >= week_start,
                            ConsumerScan.device_hash != "").scalar() or 0)
        out.append({"id": mid, "pharmacy_id": p.id, "pharmacy": p.name, "region": p.region, "address": p.address,
                    "points": POINTS["mission"], "done": done, "scanners_this_week": scanners,
                    "title": f"{p.name} dorixonasida istalgan dori qutisini tekshiring",
                    "why": "Bu dorixonada xaridorlar tekshiruvi kam. Sizning skaneringiz bozorni tozalashga yordam beradi.",
                    "expires": (week_start + timedelta(days=7)).isoformat()})
    return out


def _mission_for(db: Session, pharmacy_id: int, now: datetime) -> str | None:
    return f"{week_id(now)}:{pharmacy_id}" if pharmacy_id in _picked(db, now) else None


# ------------------------------------------------------------------ ball berish
def award(db: Session, res, now: datetime | None = None) -> dict:
    """trace.verify natijasi boʻyicha ball beradi. Qaytaradi: {earned, pending, messages, total, level}."""
    now = now or datetime.utcnow()
    out = {"earned": 0, "pending": 0, "messages": [], "total": 0, "level": LEVELS[0][1]}
    device = getattr(res, "device", "") or ""
    p = res.parsed
    if not device or not p or not p.gtin:
        return out
    w = wallet(db, device)
    if not w.flagged:
        hour = (db.query(func.count(ConsumerScan.id))
                .filter(ConsumerScan.device_hash == device, ConsumerScan.at >= now - timedelta(hours=1)).scalar())
        if hour > VELOCITY_LIMIT:
            w.flagged = True
    if w.flagged:
        out["messages"].append("Hamyoningizda gʻayrioddiy faollik: ballar vaqtincha toʻxtatildi.")
        _fill_totals(db, device, out)
        db.commit()
        return out

    today = (db.query(func.coalesce(func.sum(PointEvent.points), 0))
             .filter(PointEvent.device_hash == device, PointEvent.kind.in_(CAPPED_KINDS),
                     PointEvent.status == "credited", PointEvent.created_at >= _day_start(now)).scalar())
    scan = db.get(ConsumerScan, res.scan_id) if res.scan_id else None
    pharmacy_id = scan.pharmacy_id if scan else None
    valid_box = res.pack is not None or res.source == "asl_belgisi"
    serial = p.serial or ""

    def add(kind: str, label: str, status: str = "credited", ref: str = "") -> None:
        nonlocal today
        pts = POINTS[kind]
        if status == "credited" and kind in CAPPED_KINDS:
            pts = min(pts, max(0, DAILY_CAP - today))
            if pts <= 0:
                if not any("chegara" in m for m in out["messages"]):
                    out["messages"].append(f"Bugungi {DAILY_CAP} ball chegarasiga yetdingiz. Ertaga davom eting!")
                return
            today += pts
        db.add(PointEvent(device_hash=device, kind=kind, points=pts, status=status, gtin=p.gtin, serial=serial,
                          scan_id=res.scan_id, pharmacy_id=pharmacy_id, ref=ref, note=label, created_at=now))
        if status == "pending":
            out["pending"] += pts
            out["messages"].append(f"⏳ +{pts} {label} (inspektor tasdiqlasa)")
        else:
            out["earned"] += pts
            out["messages"].append(f"+{pts} {label}")

    if valid_box and serial:
        if res.mode == "before" and not _exists(db, device_hash=device, kind="scan", gtin=p.gtin, serial=serial):
            box_devices = (db.query(func.count(func.distinct(PointEvent.device_hash)))
                           .filter(PointEvent.kind == "scan", PointEvent.gtin == p.gtin, PointEvent.serial == serial,
                                   PointEvent.created_at >= now - timedelta(days=1)).scalar())
            if box_devices < BOX_DEVICES_PER_DAY:
                add("scan", "sotib olishdan oldin tekshirdingiz")
                if pharmacy_id:
                    add("pharmacy", "dorixona koʻrsatildi")
        if (res.mode == "after" and res.verdict != "danger"
                and not _exists(db, kind="purchase", gtin=p.gtin, serial=serial)):
            add("purchase", "xarid zanjirga yozildi")

    danger_keys = {c.key for c in res.checks if c.status in ("danger", "warning")} & CATCH_KEYS
    if res.verdict == "danger" and danger_keys and serial and not _exists(db, kind="catch", gtin=p.gtin, serial=serial):
        add("catch", "shubhali quti topdingiz", status="pending")

    if pharmacy_id and serial and res.verdict != "unknown":
        mid = _mission_for(db, pharmacy_id, now)
        if mid and not _exists(db, device_hash=device, kind="mission", ref=mid):
            add("mission", "missiya bajarildi 🚩", ref=mid)

    db.flush()
    _fill_totals(db, device, out)
    db.commit()
    return out


def on_report(db: Session, scan: ConsumerScan) -> int:
    """Inspektorga xabar: pending ball (tasdiqlansa hisoblanadi)."""
    if not scan.device_hash or _exists(db, device_hash=scan.device_hash, kind="report", scan_id=scan.id):
        return 0
    db.add(PointEvent(device_hash=scan.device_hash, kind="report", points=POINTS["report"], status="pending",
                      scan_id=scan.id, pharmacy_id=scan.pharmacy_id, note="inspektorga xabar"))
    return POINTS["report"]


def resolve(db: Session, scan: ConsumerScan, confirmed: bool) -> dict:
    """Inspektor qarori: tasdiqlansa pending ballar hisoblanadi va bounty qoʻshiladi."""
    scan.report_status = "tasdiqlandi" if confirmed else "rad_etildi"
    events = db.query(PointEvent).filter(PointEvent.scan_id == scan.id, PointEvent.status == "pending").all()
    # "catch" boshqa skanerda boʻlishi mumkin: shu quti boʻyicha barcha pending topilmalar
    p = scan.pack
    if p:
        events += (db.query(PointEvent).filter(PointEvent.kind == "catch", PointEvent.status == "pending",
                                               PointEvent.gtin == p.gtin, PointEvent.serial == p.serial).all())
    credited = 0
    for e in {e.id: e for e in events}.values():
        e.status = "credited" if confirmed else "rejected"
        credited += e.points if confirmed else 0
    if confirmed and scan.device_hash and scan.reported \
            and not _exists(db, device_hash=scan.device_hash, kind="bounty", scan_id=scan.id):
        db.add(PointEvent(device_hash=scan.device_hash, kind="bounty", points=POINTS["bounty"], scan_id=scan.id,
                          pharmacy_id=scan.pharmacy_id, note="tasdiqlangan xabar uchun mukofot"))
        credited += POINTS["bounty"]
    db.commit()
    return {"scan_id": scan.id, "status": scan.report_status, "credited": credited}


# ------------------------------------------------------------------ hamyon
def _sums(db: Session, device: str) -> tuple[int, int, int]:
    rows = (db.query(PointEvent.status, PointEvent.points).filter(PointEvent.device_hash == device).all())
    balance = sum(pts for st, pts in rows if st == "credited")
    pending = sum(pts for st, pts in rows if st == "pending")
    lifetime = sum(pts for st, pts in rows if st == "credited" and pts > 0)
    return balance, pending, lifetime


def level_for(lifetime: int) -> dict:
    cur = LEVELS[0]
    nxt = None
    for i, lv in enumerate(LEVELS):
        if lifetime >= lv[0]:
            cur = lv
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    progress = 1.0 if not nxt else (lifetime - cur[0]) / (nxt[0] - cur[0])
    return {"name": cur[1], "icon": cur[2], "min": cur[0], "next_name": nxt[1] if nxt else None,
            "next_min": nxt[0] if nxt else None, "progress": round(progress, 3), "index": LEVELS.index(cur) + 1}


def _fill_totals(db: Session, device: str, out: dict) -> None:
    balance, _, lifetime = _sums(db, device)
    out["total"] = balance
    out["level"] = level_for(lifetime)["name"]


def badges(db: Session, device: str) -> list[dict]:
    kinds = Counter(k for (k,) in db.query(PointEvent.kind).filter(PointEvent.device_hash == device,
                                                                    PointEvent.status == "credited"))
    scans = db.query(ConsumerScan.pharmacy_id, ConsumerScan.at).filter(ConsumerScan.device_hash == device).all()
    pharmacies = {pid for pid, _ in scans if pid}
    days = {at.date() for _, at in scans}
    got = {"first_scan": kinds["scan"] > 0 or len(scans) > 0, "buyer": kinds["purchase"] > 0,
           "explorer": len(pharmacies) >= 3, "regular": len(days) >= 5, "missioner": kinds["mission"] > 0,
           "guardian": kinds["catch"] > 0 or kinds["bounty"] > 0}
    return [{"key": k, "icon": v[0], "title": v[1], "description": v[2], "earned": got[k]} for k, v in BADGES.items()]


def streak(db: Session, device: str, now: datetime) -> int:
    days = {at.date() for (at,) in db.query(ConsumerScan.at).filter(ConsumerScan.device_hash == device)}
    n, d = 0, now.date()
    if d not in days:
        d -= timedelta(days=1)
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


KIND_LABEL = {"scan": "Tekshiruv", "pharmacy": "Dorixona", "purchase": "Xarid", "mission": "Missiya",
              "catch": "Shubhali quti", "report": "Xabar", "bounty": "Mukofot (tasdiqlangan)", "redeem": "Almashtirildi",
              "bonus": "Bonus"}


def summary(db: Session, device: str, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    w = db.get(Wallet, device)
    balance, pending, lifetime = _sums(db, device)
    today = (db.query(func.coalesce(func.sum(PointEvent.points), 0))
             .filter(PointEvent.device_hash == device, PointEvent.kind.in_(CAPPED_KINDS),
                     PointEvent.status == "credited", PointEvent.created_at >= _day_start(now)).scalar())
    hist = (db.query(PointEvent).filter(PointEvent.device_hash == device)
            .order_by(PointEvent.created_at.desc(), PointEvent.id.desc()).limit(30).all())
    reds = db.query(Redemption).filter(Redemption.device_hash == device).order_by(Redemption.id.desc()).all()
    return {
        "nickname": display_name(w, device), "has_nickname": bool(w and w.nickname), "flagged": bool(w and w.flagged),
        "points": balance, "pending": pending, "lifetime": lifetime, "level": level_for(lifetime),
        "today": {"earned": today, "cap": DAILY_CAP}, "streak": streak(db, device, now),
        "badges": badges(db, device), "rank": rank(db, device, now),
        "history": [{"id": e.id, "kind": e.kind, "label": KIND_LABEL.get(e.kind, e.kind), "points": e.points,
                     "status": e.status, "note": e.note, "at": e.created_at.isoformat()} for e in hist],
        "redemptions": [{"reward_key": r.reward_key, "title": next((c["title"] for c in CATALOG if c["key"] == r.reward_key),
                                                                   r.reward_key),
                         "code": r.code, "points": r.points, "at": r.created_at.isoformat()} for r in reds],
        "rules": [{"kind": k, "label": KIND_LABEL[k], "points": v} for k, v in POINTS.items()],
    }


def leaderboard(db: Session, now: datetime | None = None, days: int = 30, device: str = "", limit: int = 20) -> list[dict]:
    now = now or datetime.utcnow()
    rows = (db.query(PointEvent.device_hash, func.sum(PointEvent.points))
            .filter(PointEvent.status == "credited", PointEvent.points > 0,
                    PointEvent.created_at >= now - timedelta(days=days))
            .group_by(PointEvent.device_hash).order_by(func.sum(PointEvent.points).desc()).all())
    out = []
    for i, (dev, pts) in enumerate(rows, 1):
        if i > limit and dev != device:
            continue
        w = db.get(Wallet, dev)
        if w and w.flagged:
            continue
        regions = Counter(r for (r,) in db.query(ConsumerScan.region).filter(ConsumerScan.device_hash == dev) if r)
        out.append({"rank": i, "name": display_name(w, dev), "points": int(pts),
                    "region": regions.most_common(1)[0][0] if regions else "", "me": dev == device})
    return out


def rank(db: Session, device: str, now: datetime) -> int | None:
    for r in leaderboard(db, now, device=device, limit=10**6):
        if r["me"]:
            return r["rank"]
    return None


NICK_RE = re.compile(r"^[A-Za-z0-9_ʻʼ'\-. ]{2,20}$")
BANNED = ("admin", "inspektor", "doriishonch", "moderator")


def set_nickname(db: Session, device: str, nickname: str) -> str:
    nick = " ".join(nickname.split())
    if not NICK_RE.match(nick) or any(b in nick.lower() for b in BANNED):
        raise ValueError("Taxallus 2–20 belgi: harf, raqam, _ - . (ism-familiya yozmaslik tavsiya etiladi)")
    taken = db.query(Wallet).filter(func.lower(Wallet.nickname) == nick.lower(), Wallet.device_hash != device).first()
    if taken:
        raise ValueError("Bu taxallus band")
    wallet(db, device).nickname = nick
    db.commit()
    return nick


def redeem(db: Session, device: str, key: str) -> dict:
    item = next((c for c in CATALOG if c["key"] == key), None)
    if not item:
        raise ValueError("Bunday mukofot yoʻq")
    w = wallet(db, device)
    if w.flagged:
        raise ValueError("Hamyon tekshiruvda: mukofot vaqtincha mavjud emas")
    balance, _, _ = _sums(db, device)
    if balance < item["points"]:
        raise ValueError(f"Ball yetarli emas: kerak {item['points']}, sizda {balance}")
    code = "DI-" + secrets.token_hex(3).upper() + "-" + hashlib.sha256(device.encode()).hexdigest()[:4].upper()
    db.add(PointEvent(device_hash=device, kind="redeem", points=-item["points"], ref=key, note=item["title"]))
    db.add(Redemption(device_hash=device, reward_key=key, points=item["points"], code=code))
    db.commit()
    return {"code": code, "title": item["title"], "partner": item["partner"], "points": item["points"],
            "note": "Kodni hamkor dorixonada koʻrsating. (Demo: haqiqiy hamkorlar ulanmagan.)"}


def seed_demo(db: Session, now: datetime | None = None) -> None:
    """Reyting boʻsh koʻrinmasligi uchun demo hamyonlar (is_demo=True)."""
    now = now or datetime.utcnow()
    if db.query(Wallet).filter(Wallet.is_demo.is_(True)).count():
        return
    demo = [("Dilnoza_T", 640), ("Sardor.Med", 520), ("Jasur_07", 410), ("Malika", 355), ("Bekzod_S", 290),
            ("Nigora", 210), ("Aziz_Farm", 150), ("Umida", 95)]
    pharmacies = [p.id for p in db.query(Participant).filter(Participant.kind == "pharmacy").limit(8)]
    for i, (nick, pts) in enumerate(demo):
        dev = hashlib.sha256(f"demo-wallet-{i}".encode()).hexdigest()
        db.add(Wallet(device_hash=dev, nickname=nick, is_demo=True, created_at=now - timedelta(days=20)))
        left, day = pts, 0
        while left > 0:
            p = min(left, 30)
            db.add(PointEvent(device_hash=dev, kind="scan" if day % 4 else "mission", points=p, is_demo=True,
                              pharmacy_id=pharmacies[i % len(pharmacies)] if pharmacies else None,
                              note="demo", created_at=now - timedelta(days=day % 25, hours=i)))
            left -= p
            day += 1
    db.commit()
