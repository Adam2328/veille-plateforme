from datetime import timedelta

from engine.band import build_band
from engine.contract import validate
from engine.timeutil import iso
from tests.helpers import NOW

G = {"band": {"quotes": ["^FCHI", "^TNX", "ABSENT"], "new_hours": 6, "max_new": 4, "agenda_days": 3, "max_agenda": 4, "max_matches": 6}}


def quote(symbol, name, group, change, pct):
    return {"symbol": symbol, "name": name, "group": group, "price": 1.0, "change": change, "change_pct": pct,
            "currency": "EUR", "as_of": iso(NOW), "stale": False}


def test_band_orders_news_agenda_matches_race_then_markets():
    home = {"events": {"n": {"id": "n", "level": 1, "universe": "ia", "title": "T", "title_fr": "Titre", "first_seen": iso(NOW - timedelta(hours=1))},
                       "old": {"id": "old", "level": 1, "universe": "ia", "title": "Vieux", "first_seen": iso(NOW - timedelta(hours=10))},
                       "l2": {"id": "l2", "level": 2, "universe": "ia", "title": "Moins", "first_seen": iso(NOW)}},
            "domains": [{"id": "finance", "upcoming": [{"date": "2026-09-28", "title": "Réunion BCE"}, {"date": "2026-10-20", "title": "Loin"}]},
                        {"id": "inconnu", "upcoming": [{"date": "2026-09-27", "title": "Hors univers"}]}]}
    football = {"fixtures": [{"home": "PSG", "away": "OM", "date": iso(NOW + timedelta(hours=8))},
                             {"home": "A", "away": "B", "date": iso(NOW + timedelta(days=4))}],
                "results": [{"home": "Lens", "away": "Lille", "date": iso(NOW - timedelta(hours=3)), "home_score": 2, "away_score": 1}]}
    f1 = {"next": {"name": "GP", "sessions": [{"name": "Qualifications", "start": iso(NOW + timedelta(days=1))},
                                              {"name": "Course", "start": iso(NOW + timedelta(days=2))}]}}
    quotes = {"quotes": [quote("^FCHI", "CAC 40", "Indices", 30.0, 0.4), quote("^TNX", "Taux US 10 ans", "Taux", -0.05, -1.2)]}
    band = build_band(quotes, football, f1, home, {"finance": "finance"}, G, NOW)
    validate("band", band)
    assert [(i["kind"], i["label"]) for i in band["items"]] == [
        ("new", "Titre"), ("agenda", "Réunion BCE"), ("match", "PSG – OM"), ("match", "Lens – Lille"),
        ("race", "GP"), ("quote", "CAC 40"), ("quote", "Taux US 10 ans")]
    items = band["items"]
    assert items[0]["href"] == "#/e/n" and items[3]["value"] == "2–1"
    assert (items[5]["delta"], items[5]["unit"]) == (0.4, "%") and (items[6]["delta"], items[6]["unit"]) == (-0.05, "pt")


def test_band_survives_missing_data():
    band = build_band(None, None, None, {"events": {}, "domains": []}, {}, G, NOW)
    validate("band", band)
    assert band["items"] == []
