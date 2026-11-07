import os
import sys
from datetime import date

from paymatch.matcher import Claim, Incoming, add_workdays, match, workdays_between

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))
import demo_day  # noqa: E402

D = date(2026, 11, 6)


def by_invoice(results):
    return {r.claim.invoice: r for r in results}


def test_workdays():
    assert add_workdays(date(2026, 11, 6), 1) == date(2026, 11, 9)       # пятница → понедельник
    assert workdays_between(date(2026, 11, 6), date(2026, 11, 9)) == 1


def test_invoice_number_in_purpose():
    r = match([Claim("1", "И", "К", 1000, D, "qr", "A")], [Incoming("x", "bank", "A", D, 1000, purpose="Оплата по счету №1")], D)
    assert r[0].status == "ok" and r[0].matched == ["x"]


def test_found_elsewhere_is_flagged_not_lost():
    r = match([Claim("1", "И", "К", 1000, D, "cash", "Касса 1")], [Incoming("x", "bank", "A", D, 1000)], D)
    assert r[0].status == "elsewhere" and "не там, где указано" in r[0].note


def test_one_incoming_cannot_confirm_two_claims():
    claims = [Claim("1", "И", "К", 1000, D, "qr", "A"), Claim("2", "И", "К", 1000, D, "qr", "A")]
    r = by_invoice(match(claims, [Incoming("x", "bank", "A", D, 1000)], D))
    assert sorted(x.status for x in r.values()) == ["ok", "waiting"]


def test_outside_window_is_missing():
    old = date(2026, 10, 1)
    r = match([Claim("1", "И", "К", 1000, old, "qr", "A")], [Incoming("x", "bank", "A", D, 1000)], D)
    assert r[0].status == "missing"


def test_demo_day():
    r = by_invoice(demo_day.run())
    assert {k for k, v in r.items() if v.status == "acquiring"} == {"1195", "1199", "1205", "1206", "1208"}
    assert {k for k, v in r.items() if v.status == "ambiguous"} == {"1210", "1211", "1212"}
    assert {k for k, v in r.items() if v.status == "elsewhere"} == {"1203", "1213", "1217"}
    assert r["1216"].status == "waiting" and r["1180"].status == "missing"
