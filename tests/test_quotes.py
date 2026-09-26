from datetime import timedelta

from engine.contract import validate
from engine.quotes import collect_quotes
from engine.timeutil import iso
from tests.helpers import NOW

SPECS = [{"symbol": "^GSPC", "name": "S&P 500", "group": "Indices"},
         {"symbol": "EURUSD=X", "name": "EUR/USD", "group": "Devises"},
         {"symbol": "^TNX", "name": "Taux US 10 ans", "group": "Taux"}]


def relay(*rows):
    return {"derniere_maj": "2026-09-26 12:00:00",
            "indices": [{"nom": s, "valeur": v, "variation": p} for s, v, p in rows]}


ALL = relay(("^GSPC", 110.0, 10.0), ("EURUSD=X", 1.14, -0.5), ("^TNX", 5.18, 4.4))


def test_collect_builds_a_valid_file_from_one_relay_call():
    calls = []
    quotes, health = collect_quotes(SPECS, None, NOW, lambda url: calls.append(url) or ALL)
    validate("quotes", quotes)
    assert len(calls) == 1 and quotes["checked_at"] == iso(NOW)
    sp = quotes["quotes"][0]
    assert (sp["symbol"], sp["name"], sp["group"], sp["price"]) == ("^GSPC", "S&P 500", "Indices", 110.0)
    assert sp["change_pct"] == 10.0 and sp["change"] == 10.0 and sp["stale"] is False and sp["as_of"] == iso(NOW)
    assert [h["source"] for h in health] == ["quote-relay", "quote:^GSPC", "quote:EURUSD=X", "quote:^TNX"]
    assert all(h["ok"] for h in health)


def test_unchanged_values_keep_their_as_of_so_the_file_is_not_rewritten():
    first, _ = collect_quotes(SPECS, None, NOW, lambda url: ALL)
    later = NOW + timedelta(minutes=30)
    second, _ = collect_quotes(SPECS, first, later, lambda url: ALL)
    assert second["quotes"] == first["quotes"] and second["checked_at"] != first["checked_at"]
    moved = relay(("^GSPC", 111.0, 11.0), ("EURUSD=X", 1.14, -0.5), ("^TNX", 5.18, 4.4))
    third, _ = collect_quotes(SPECS, first, later, lambda url: moved)
    by = {q["symbol"]: q for q in third["quotes"]}
    assert by["^GSPC"]["as_of"] == iso(later) and by["^TNX"]["as_of"] == iso(NOW)


def test_symbols_are_url_encoded_in_the_relay_request():
    seen = []
    collect_quotes(SPECS, None, NOW, lambda url: seen.append(url) or ALL)
    assert "%5EGSPC" in seen[0] and "^" not in seen[0] and "EURUSD=X" in seen[0] and seen[0].count(",") == 2


def test_missing_value_keeps_the_previous_one_marked_stale():
    first, _ = collect_quotes(SPECS, None, NOW, lambda url: ALL)
    partial = relay(("^GSPC", 111.0, 1.0), ("EURUSD=X", None, None), ("^TNX", 5.2, 0.4))
    second, health = collect_quotes(SPECS, first, NOW, lambda url: partial)
    by = {q["symbol"]: q for q in second["quotes"]}
    assert by["EURUSD=X"]["stale"] is True and by["EURUSD=X"]["price"] == 1.14
    assert by["^GSPC"]["stale"] is False and by["^GSPC"]["price"] == 111.0
    assert {h["source"]: h["ok"] for h in health}["quote:EURUSD=X"] is False
    validate("quotes", second)


def test_missing_value_without_history_is_omitted():
    quotes, _ = collect_quotes(SPECS, None, NOW, lambda url: relay(("^GSPC", 110.0, 10.0)))
    assert [q["symbol"] for q in quotes["quotes"]] == ["^GSPC"]


def test_unreachable_relay_marks_everything_stale_and_reports_a_single_failure():
    first, _ = collect_quotes(SPECS, None, NOW, lambda url: ALL)

    def down(url):
        raise TimeoutError("le relais dort")

    second, health = collect_quotes(SPECS, first, NOW, down)
    assert all(q["stale"] for q in second["quotes"]) and len(second["quotes"]) == 3
    assert len(health) == 1 and health[0]["source"] == "quote-relay" and not health[0]["ok"] and "TimeoutError" in health[0]["error"]
    validate("quotes", second)
    empty, _ = collect_quotes(SPECS, None, NOW, down)
    assert empty["quotes"] == []


def test_malformed_relay_answers_are_handled_like_a_failure():
    for bad in ({}, {"indices": None}, {"indices": [1, 2]}, {"indices": [{"valeur": 1.0}]}, []):
        quotes, health = collect_quotes(SPECS, None, NOW, lambda url, b=bad: b)
        assert quotes["quotes"] == [], bad
        assert health[0]["source"] == "quote-relay"


def test_non_numeric_or_non_finite_values_are_treated_as_missing():
    junk = relay(("^GSPC", "110", 1.0), ("EURUSD=X", float("nan"), 1.0), ("^TNX", float("inf"), 1.0))
    quotes, _ = collect_quotes(SPECS, None, NOW, lambda url: junk)
    assert quotes["quotes"] == []


def test_missing_or_extreme_variation_gives_a_null_change_without_dividing_by_zero():
    rows = relay(("^GSPC", 110.0, None), ("EURUSD=X", 1.14, -100.0), ("^TNX", 5.18, "x"))
    quotes, _ = collect_quotes(SPECS, None, NOW, lambda url: rows)
    validate("quotes", quotes)
    assert [(q["change"], q["change_pct"]) for q in quotes["quotes"]] == [(None, None)] * 3


def test_names_and_groups_come_from_the_config_not_the_relay():
    renamed = [{**SPECS[0], "name": "Standard & Poor's", "group": "Actions US"}]
    quotes, _ = collect_quotes(renamed, None, NOW, lambda url: ALL)
    assert (quotes["quotes"][0]["name"], quotes["quotes"][0]["group"]) == ("Standard & Poor's", "Actions US")
