from conftest import find_id

FORBIDDEN = ["ball", "reyting", "eng yaxshi", "score", "rating"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_search_by_trade_name_with_typo(client):
    r = client.get("/search", params={"q": "norvadn"})
    names = [d["trade_name"] for d in r.json()["results"]]
    assert "Norvadin" in names


def test_search_by_inn_returns_all_products(client):
    r = client.get("/search", params={"q": "amlodipin"})
    assert len(r.json()["results"]) >= 4


def test_search_by_gtin(client):
    r = client.get("/search", params={"q": "04780000007919"})
    assert r.json()["results"][0]["trade_name"] == "Norvadin"


def test_trust_card_has_sources_and_no_score(client):
    r = client.get(f"/drugs/{find_id(client, 'Amlozar')}")
    assert r.status_code == 200
    body = r.json()
    keys = {f["key"] for f in body["facts"]}
    assert {"registry", "gmp", "quality_alert", "marking", "evidence"} <= keys
    for f in body["facts"]:
        if f["status"] == "ok" and f["key"] in ("registry", "gmp"):
            assert f["source_url"] and f["updated_at"]
    text = r.text.lower()
    for word in FORBIDDEN:
        assert word not in text


def test_trust_card_shows_quality_alert(client):
    body = client.get(f"/drugs/{find_id(client, 'Diaform-O')}").json()
    assert any(f["key"] == "quality_alert" and f["status"] == "warn" for f in body["facts"])
    # Orol Demo Bio uchun GMP yoʻq
    assert any(f["key"] == "gmp" and f["status"] == "missing" for f in body["facts"])


def test_evidence_marked_as_provided_by_manufacturer(client):
    body = client.get(f"/drugs/{find_id(client, 'Amlozar')}").json()
    ev = [f for f in body["facts"] if f["key"] == "evidence" and f["status"] == "info"]
    assert ev and all(f["provided_by_manufacturer"] for f in ev)


def test_drug_404(client):
    assert client.get("/drugs/99999").status_code == 404


def test_analogs_same_inn_dose_form_local_first(client):
    base = find_id(client, "Norvadin")
    body = client.get(f"/drugs/{base}/analogs").json()
    analogs = body["analogs"]
    assert len(analogs) == 3
    assert all(a["drug"]["inn"] == "Amlodipin" and a["drug"]["strength"] == "5 mg" for a in analogs)
    locality = [a["drug"]["manufacturer"]["is_local"] for a in analogs]
    assert locality == sorted(locality, reverse=True)
    local = [a for a in analogs if a["drug"]["manufacturer"]["is_local"]]
    assert all(a["price_diff_uzs"] < 0 for a in local)


def test_analogs_nti_note(client):
    body = client.get(f"/drugs/{find_id(client, 'Thyrorhein')}/analogs").json()
    assert "shifokor nazoratida" in body["note"]


def test_explain_template_mode_cites_sources(client):
    r = client.post("/explain", json={"drug_id": find_id(client, "Amlozar"), "question": "Bu dori sifatli ishlab chiqarilganmi?"})
    body = r.json()
    assert r.status_code == 200
    assert not body["blocked"]
    assert body["sources"]
    assert "[" in body["answer"]


def test_explain_blocks_dose_question(client):
    r = client.post("/explain", json={"drug_id": find_id(client, "Amlozar"), "question": "Kuniga necha tabletka ichay?"})
    body = r.json()
    assert body["blocked"] is True
    assert "shifokor" in body["answer"]


def test_explain_empty_question(client):
    r = client.post("/explain", json={"drug_id": find_id(client, "Amlozar"), "question": "  "})
    assert r.status_code == 400


def test_scan_marking_code(client):
    code = "010478000000791921AB12CD34\x1d91EE07\x1d92abc"
    r = client.post("/scan", data={"code": code})
    body = r.json()
    assert body["method"] == "datamatrix"
    assert body["matches"][0]["trade_name"] == "Norvadin"


def test_scan_unknown_code(client):
    r = client.post("/scan", data={"code": "0109999999999999"})
    assert r.json()["matches"] == []


def test_scan_image_without_key_gives_note(client):
    r = client.post("/scan", files={"file": ("a.jpg", b"notanimage", "image/jpeg")})
    body = r.json()
    assert body["method"] == "none"
    assert "ANTHROPIC_API_KEY" in body["note"]


def test_scan_requires_input(client):
    assert client.post("/scan").status_code == 400


def test_manufacturers_local_first(client):
    ms = client.get("/manufacturers").json()
    assert ms[0]["is_local"] is True


def test_insights(client, admin):
    ms = client.get("/manufacturers").json()
    zar = next(m for m in ms if m["name"] == "Zarafshon Demo Farm")
    body = admin.get(f"/manufacturers/{zar['id']}/insights").json()
    assert body["total_views"] > 0
    assert body["topics"]
    assert all(not a["drug"]["manufacturer"]["is_local"] for a in body["competing_imports"])
    assert admin.get("/manufacturers/999/insights").status_code == 404
