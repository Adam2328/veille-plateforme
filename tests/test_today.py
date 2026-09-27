from datetime import timedelta

from engine.timeutil import iso
from engine.today import build_today, day_score
from tests.helpers import NOW

G = {"today": {"window_hours": 36, "floor": 2, "total": 7, "max_per_entity": 2, "novelty_bonus": 8, "evolution_bonus": 5}}
UNIS = {u: {"id": u, "name": u.upper(), "short": u, "color": u} for u in ("finance", "ia", "sport")}


def ev(id, universe, imp, ents=(), level=1, hours=2, rev=1, first_hours=None):
    return {"id": id, "universe": universe, "importance": imp, "level": level, "entity_ids": list(ents), "rev": rev,
            "updated_at": iso(NOW - timedelta(hours=hours)),
            "first_seen": iso(NOW - timedelta(hours=hours if first_hours is None else first_hours))}


def ids(result):
    return {r["id"]: r["ids"] for r in result}


def test_each_universe_gets_its_floor_then_the_best_scores_fill_the_total():
    evs = [ev("f1", "finance", 90), ev("f2", "finance", 85), ev("f3", "finance", 80), ev("f4", "finance", 79),
           ev("f5", "finance", 78), ev("i1", "ia", 50), ev("i2", "ia", 40), ev("s1", "sport", 30)]
    assert ids(build_today(evs, UNIS, G, NOW)) == {"finance": ["f1", "f2", "f3", "f4"], "ia": ["i1", "i2"], "sport": ["s1"]}


def test_at_most_two_events_per_lead_entity_and_old_or_level_zero_events_are_ignored():
    evs = [ev("a", "ia", 90, ["company:openai"]), ev("b", "ia", 89, ["company:openai"]), ev("c", "ia", 88, ["company:openai"]),
           ev("old", "ia", 99, hours=40), ev("l0", "ia", 99, level=0), ev("x", "espace", 99)]
    assert ids(build_today(evs, UNIS, G, NOW))["ia"] == ["a", "b"]


def test_novelty_and_evolution_bonuses():
    t = G["today"]
    assert day_score(ev("n", "ia", 50, first_hours=2), NOW, t) == 58
    assert day_score(ev("o", "ia", 50, hours=2, first_hours=30, rev=2), NOW, t) == 55
    assert day_score(ev("p", "ia", 50, hours=20, first_hours=30, rev=2), NOW, t) == 50


def test_universes_keep_their_order_and_metadata_even_when_empty():
    result = build_today([], UNIS, G, NOW)
    assert [r["id"] for r in result] == ["finance", "ia", "sport"]
    assert result[0] == {"id": "finance", "name": "FINANCE", "short": "finance", "color": "finance", "ids": []}
