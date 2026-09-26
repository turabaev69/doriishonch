import pytest

from app.services import ai, safety


@pytest.mark.parametrize("q", [
    "Kuniga necha tabletka ichay?",
    "Dozasi qancha?",
    "Qanday ichish kerak?",
    "Bolaga berish mumkinmi?",
    "Homiladorlikda ichsam boʻladimi?",
    "Menga qaysi dori kerak?",
    "Сколько раз в день принимать?",
    "Qon bosimimni qanday davolayman?",
])
def test_medical_questions_detected(q):
    assert safety.is_medical_question(q)


@pytest.mark.parametrize("q", [
    "Bu dori sifatlimi?",
    "GMP sertifikati bormi?",
    "Originaldan farqi nima?",
    "Qalbaki emasligini qanday bilaman?",
])
def test_normal_questions_pass(q):
    assert not safety.is_medical_question(q)


def test_filter_removes_dose_sentence():
    text, changed = safety.filter_answer("Dori roʻyxatdan oʻtgan [1]. Kuniga 2 marta iching.")
    assert changed
    assert "Kuniga 2" not in text
    assert "roʻyxatdan oʻtgan [1]" in text
    assert "shifokor" in text


def test_filter_removes_superlatives():
    text, changed = safety.filter_answer("Bu eng yaxshi dori. GMP sertifikati bor [2].")
    assert changed
    assert "eng yaxshi" not in text.lower()
    assert "GMP" in text


def test_filter_keeps_clean_text():
    src = "Dori davlat reestrida bor [1]. Ishlab chiqaruvchida GMP sertifikati bor [2]."
    text, changed = safety.filter_answer(src)
    assert not changed and text == src


def test_filter_all_removed_gives_referral():
    text, _ = safety.filter_answer("Kuniga 3 marta iching.")
    assert "shifokor" in text


@pytest.mark.parametrize("q,topic", [
    ("Originaldan farqi bormi?", "ekvivalentlik"),
    ("Qalbaki emasmi?", "haqiqiylik"),
    ("GMP sertifikati bormi?", "sifat"),
    ("Nega arzon?", "narx"),
    ("Dozasi qancha?", "tibbiy"),
])
def test_topic_classification(q, topic):
    assert ai.classify_topic(q) == topic


def test_parse_marking_code():
    assert ai.parse_marking_code("010478000000791921XYZ") == "04780000007919"
    assert ai.parse_marking_code("(01)04780000007919(21)XYZ") == "04780000007919"
    assert ai.parse_marking_code("hello") is None
