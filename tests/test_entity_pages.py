import json
from datetime import timedelta

from engine.contract import validate
from engine.entity_pages import build_entity_pages
from engine.graph import adjacency, build_edges
from engine.publish import publish_entities
from engine.timeutil import iso
from tests.helpers import NOW, mk_event, mk_item

CAT = {
    "company:openai": {"id": "company:openai", "name": "OpenAI", "type": "company", "aliases": ["openai"], "universes": ["ia"], "wikidata": "Q1"},
    "ai_model:gpt": {"id": "ai_model:gpt", "name": "GPT", "type": "ai_model", "aliases": ["=GPT", "chatgpt"], "universes": ["ia"], "quote": "GPT-X"},
}
QUOTES = {"quotes": [{"symbol": "GPT-X", "name": "x", "group": "g", "price": 1.5, "change": 0.1, "change_pct": 2.0,
                      "currency": "USD", "as_of": iso(NOW), "stale": False}]}


def ev(id, ids, hours=1, level=1):
    e = mk_event([mk_item(f"{id}i", f"Titre {id}")], id=id, updated_at=iso(NOW - timedelta(hours=hours)))
    return {**e, "importance": 70, "level": level, "reliability": "confirmé", "entity_ids": ids, "universe": "ia"}


def test_index_and_pages_gather_events_relations_facts_and_quote():
    adj = adjacency(build_edges([("company:openai", "produit", "ai_model:gpt")], [], []))
    facts = {"company:openai": {"description": "entreprise d'IA", "image": "https://commons.wikimedia.org/x.png",
                                "facts": [{"label": "Création", "value": "2015"}], "edges": []}}
    events = [ev("a", ["company:openai"], hours=5), ev("b", ["company:openai", "ai_model:gpt"], hours=1),
              ev("old", ["company:openai"], hours=24 * 40), ev("l0", ["company:openai"], level=0)]
    index, pages = build_entity_pages(CAT, facts, adj, events, QUOTES, NOW)
    validate("entityIndex", index)
    assert {e["id"]: e["n30"] for e in index["entities"]} == {"ai_model:gpt": 1, "company:openai": 2}
    assert next(e for e in index["entities"] if e["id"] == "ai_model:gpt")["aliases"] == ["GPT", "chatgpt"]
    assert next(e for e in index["entities"] if e["id"] == "company:openai")["image"] == "https://commons.wikimedia.org/x.png"
    page = pages["company:openai"]
    validate("entityFile", page)
    assert [e["id"] for e in page["events"]] == ["b", "a"]
    assert page["relations"] == [{"id": "ai_model:gpt", "name": "GPT", "type": "ai_model", "label": "produit", "origin": "config", "weight": 1}]
    assert page["description"] == "entreprise d'IA" and page["facts"][0]["value"] == "2015"
    assert page["entity"] == {"id": "company:openai", "name": "OpenAI", "type": "company", "type_label": "Entreprise", "universes": ["ia"], "wikidata": "Q1"}
    gpt = pages["ai_model:gpt"]
    validate("entityFile", gpt)
    assert gpt["quote"]["change_pct"] == 2.0 and gpt["relations"][0]["label"] == "produit par" and gpt["image"] is None


def test_cooccurrence_relations_come_after_written_ones_and_unknown_neighbours_are_dropped():
    edges = build_edges([("company:openai", "produit", "ai_model:gpt")],
                        [{"src": "company:openai", "verb": "lie_a", "dst": "company:inconnue", "weight": 9, "origin": "cooccurrence"}], [])
    _, pages = build_entity_pages(CAT, {}, adjacency(edges), [], None, NOW)
    assert [r["id"] for r in pages["company:openai"]["relations"]] == ["ai_model:gpt"]


def test_pages_are_written_by_type_and_slug(tmp_path):
    index, pages = build_entity_pages(CAT, {}, {}, [], None, NOW)
    publish_entities(tmp_path, index, pages)
    data = tmp_path / "site" / "data" / "entities"
    assert json.loads((data / "company" / "openai.json").read_text("utf-8"))["entity"]["name"] == "OpenAI"
    assert len(json.loads((data / "index.json").read_text("utf-8"))["entities"]) == 2
