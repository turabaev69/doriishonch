"""Oʻz AI modellarimiz: skan xavf modeli va PackNet (qadoq surati)."""

import io
import json
import math
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.db import SessionLocal
from app.ml import packnet, risk_model
from app.ml.risk_features import FEATURES, FLAG_GROUPS
from app.models import ConsumerScan

SAMPLES = Path(__file__).resolve().parents[1] / "app/ml/samples"


@pytest.fixture(scope="module")
def demo(client):
    return {d["key"]: d for d in client.get("/demo/codes").json()}


def _verify(client, d, **kw):
    r = client.post("/verify", json={"code": d["code"], "mode": d["mode"], "pharmacy_id": d["pharmacy_id"], **kw})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- skan xavf modeli

def test_verify_returns_ai_risk(client, demo):
    body = _verify(client, demo["ok"])
    risk = body["ai_risk"]
    assert 0 <= risk["score"] <= 100 and risk["level"] in ("past", "oʻrta", "yuqori")
    assert risk["model"] == risk_model.VERSION
    assert body["verdict"] == "ok"  # model xulosani oʻzgartirmaydi


def test_risky_scenarios_score_higher_than_clean(client, demo):
    clean = _verify(client, demo["ok"])["ai_risk"]["score"]
    for key in ("fake", "reused", "bad_key"):
        risk = _verify(client, demo[key])["ai_risk"]
        assert risk["score"] > clean + 20, (key, risk)
        assert risk["reasons"], key


def test_low_price_raises_risk_with_reason(client, demo):
    d = demo["ok"]
    normal = _verify(client, d, price_paid=21000)["ai_risk"]
    cheap = _verify(client, d, price_paid=6000)["ai_risk"]
    assert cheap["score"] >= normal["score"]
    assert any("arzon" in r["text"] for r in cheap["reasons"])


def test_features_are_stored_with_scan(client, demo):
    body = _verify(client, demo["reused"])
    db = SessionLocal()
    try:
        scan = db.get(ConsumerScan, body["scan_id"])
        f = json.loads(scan.ml_features)
        assert list(f) == FEATURES
        assert f["f_reused"] == 1.0
        assert scan.ml_score == body["ai_risk"]["score"]
    finally:
        db.close()


def test_unreadable_code_has_no_ai_risk(client):
    body = client.post("/verify", json={"code": "salom"}).json()
    assert body["ai_risk"] is None


def test_model_is_monotonic_in_red_flags():
    m = risk_model.get()
    nan = float("nan")
    base = {k: nan for k in FEATURES}
    base.update({k: 0.0 for k in FLAG_GROUPS}, box_scans_30d=0, box_devices_30d=0, box_regions_3d=1,
                ph_bad_rate=0.04, ph_confirmed=0, ph_license_bad=0, batch_bad_rate=0.035, batch_reports=0,
                drug_price_log=4.5, drug_import=1, days_on_shelf=20, days_to_expiry=400, night=0, mode_after=0)
    s0 = m.score(base)["score"]
    for flag in FLAG_GROUPS:
        assert m.score({**base, flag: 1.0})["score"] >= s0, flag


def test_model_beats_rules_only_baseline():
    card = risk_model.get().card
    h = card["metrics"]["synthetic_holdout"]
    assert h["roc_auc"] > h["rules_only_roc_auc"]
    assert h["pr_auc"] > h["rules_only_pr_auc"]


def test_ml_status(client):
    s = client.get("/ml/status").json()
    assert s["risk"]["version"] == risk_model.VERSION
    assert "synthetic_holdout" in s["risk"]["metrics"]
    assert s["retrain_every"] > 0


def test_inspector_alerts_have_ai_score_and_sort(admin, client, demo):
    _verify(client, demo["fake"])
    rows = admin.get("/inspector/alerts", params={"sort": "ai", "limit": 30}).json()
    scores = [r["ml_score"] for r in rows if r["ml_score"] is not None]
    assert scores and scores == sorted(scores, reverse=True)


def test_resolved_reports_become_training_data(admin, client, demo):
    ids = []
    for key in ("fake", "reused", "ok"):
        sid = _verify(client, demo[key])["scan_id"]
        assert client.post("/reports", json={"scan_id": sid, "reason": "fake"}).status_code == 200
        ids.append((sid, key != "ok"))
    for sid, confirmed in ids:
        assert admin.post(f"/inspector/reports/{sid}/resolve", json={"confirmed": confirmed}).status_code == 200
    card = admin.post("/ml/retrain").json()
    assert card["n_real"] >= 3
    assert card["metrics"]["real_labeled"]["positives"] >= 2


def test_retrain_requires_staff(client):
    assert client.post("/ml/retrain").status_code == 401


# ---------------------------------------------------------------- PackNet

needs_weights = pytest.mark.skipif(not packnet.available(), reason="PackNet ogʻirliklari yoʻq")


def _png(color=(120, 160, 200), size=(300, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


@needs_weights
def test_packnet_numpy_forward_shapes():
    net = packnet.get()
    x = np.zeros((net.size, net.size, 3), dtype=np.float32)
    logits, fz = net.forward(x)
    assert logits.shape == (len(net.card["classes"]),) and math.isfinite(fz)


@needs_weights
def test_packnet_check_endpoint(client):
    r = client.post("/ml/packnet/check", files={"file": ("a.png", _png(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in ("asl", "farq", "boshqa", "tanilmadi")
    assert body["title"] and body["text"] and body["model"] == "packnet-v1"


def test_packnet_bad_image(client):
    if not packnet.available():
        pytest.skip("ogʻirliklar yoʻq")
    r = client.post("/ml/packnet/check", files={"file": ("a.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 422


@needs_weights
def test_inspect_box_works_without_claude_key(client):
    r = client.post("/ai/inspect-box", files={"file": ("a.png", _png(), "image/png")},
                    data={"gtin": "04780000007919"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ai_used"] is False and body["model"]["verdict"]


@needs_weights
def test_packnet_weights_served(client):
    r = client.get("/ml/packnet/weights")
    assert r.status_code == 200 and r.json()["card"]["version"] == "packnet-v1"


def test_interpret_rules():
    card = {"version": "t", "classes": [{"gtin": "01", "name": "A"}, {"gtin": "02", "name": "B"},
                                          {"gtin": "", "name": "boshqa"}],
            "other_index": 2, "thresholds": {"known_min": 0.6, "fake": 0.5}}
    p = lambda *v: np.array(v)  # noqa: E731
    assert packnet.interpret(card, p(0.9, 0.05, 0.05), 0.1, "01")["verdict"] == "asl"
    assert packnet.interpret(card, p(0.9, 0.05, 0.05), 0.8, "01")["verdict"] == "farq"
    assert packnet.interpret(card, p(0.05, 0.9, 0.05), 0.1, "01")["verdict"] == "boshqa"
    assert packnet.interpret(card, p(0.4, 0.3, 0.3), 0.1, "01")["verdict"] == "tanilmadi"
    assert packnet.interpret(card, p(0.1, 0.1, 0.8), 0.9, None)["verdict"] == "tanilmadi"
    # kod modelga notanish dori boʻlsa — faqat dizayn bahosi
    assert packnet.interpret(card, p(0.9, 0.05, 0.05), 0.1, "99")["verdict"] == "asl"


@needs_weights
@pytest.mark.parametrize("name,expected", [("norvadin-asl.jpg", "asl"), ("norvadin-qalbaki.jpg", "farq"),
                                           ("amoxibos-asl.jpg", "asl")])
def test_packnet_on_demo_photos(name, expected):
    path = SAMPLES / name
    if not path.exists():
        pytest.skip("demo suratlar yoʻq")
    gtin = "04780000007919" if name.startswith("norvadin") else "04780000190056"
    res = packnet.predict(path.read_bytes(), gtin)
    assert res["verdict"] == expected, res
