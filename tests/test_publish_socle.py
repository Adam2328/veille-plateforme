import json
from datetime import timedelta

from engine.contract import validate
from engine.publish import build_home, build_universe, project, publish
from engine.search import _entry
from engine.timeutil import iso
from tests.helpers import DOM, G, NOW, mk_event, mk_item

UNI = {"id": "ia", "name": "Intelligence artificielle", "short": "IA", "color": "ia", "order": 2, "domains": ["ia"],
       "subthemes": [{"id": "modeles", "name": "Modèles", "kinds": ["model_release"]}]}
TODAY = {"window_hours": 36, "floor": 3, "total": 18, "max_per_entity": 2, "novelty_bonus": 8, "evolution_bonus": 5}


def pub(id, imp=80, level=1, **extra):
    e = mk_event([mk_item(f"{id}i", f"Titre {id}")], id=id)
    return {**e, "importance": imp, "level": level, "reliability": "confirmé", "reliability_reason": "r", **extra}


def cfg(universes=True):
    return {"global": {**G, "today": TODAY}, "domains": {"ia": DOM}, "universes": {"ia": UNI} if universes else {}}


def test_project_adds_the_new_optional_fields_only_when_set():
    p = project(pub("a", universe="ia", entity_ids=["company:openai"], title_fr="Titre FR", image="https://i/x.jpg",
                    concerned=[[{"from": "company:openai", "to": "ai_model:gpt", "label": "produit"}]], unknown=["X"]))
    validate("event", p)
    assert p["title_fr"] == "Titre FR" and p["entity_ids"] == ["company:openai"] and "unknown" not in p
    assert "title_fr" not in project(pub("b", title_fr=None))


def test_search_entries_carry_the_optional_fields():
    entry = _entry(pub("a", universe="ia", entity_ids=["company:openai"], title_fr="Titre FR"))
    validate("searchEntry", entry)
    assert entry["universe"] == "ia" and entry["title_fr"] == "Titre FR" and "image" not in entry


def test_home_carries_today_with_its_events():
    home = build_home(cfg(), {"ia": [pub("a", universe="ia"), pub("b", 60, level=2, universe="ia")]}, NOW)
    validate("home", home)
    assert home["today"] == [{"id": "ia", "name": "Intelligence artificielle", "short": "IA", "color": "ia", "ids": ["a", "b"]}]
    assert set(home["today"][0]["ids"]) <= set(home["events"])


def test_home_without_universes_has_no_today():
    assert "today" not in build_home(cfg(universes=False), {"ia": [pub("a")]}, NOW)


def test_universe_file_lists_recent_events_by_importance_and_is_published(tmp_path):
    old = pub("old", 99, updated_at=iso(NOW - timedelta(days=8)))
    f = build_universe(UNI, {"ia": DOM}, {"ia": [pub("a", 60, universe="ia"), pub("b", 90, universe="ia"), old, pub("z", 99, level=0)]}, NOW)
    validate("universeFile", f)
    assert [e["id"] for e in f["events"]] == ["b", "a"] and f["universe"]["subthemes"][0]["id"] == "modeles"
    assert f["domains"] == [{"id": "ia", "name": DOM["name"]}]
    publish(tmp_path, build_home(cfg(), {"ia": []}, NOW), [], [f])
    assert json.loads((tmp_path / "site" / "data" / "universes" / "ia.json").read_text("utf-8"))["events"][0]["id"] == "b"
