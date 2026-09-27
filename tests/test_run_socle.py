import json

import yaml

from engine.contract import validate
from engine.run import add_summaries, run
from tests.helpers import DOM, G, NOW, mk_event, mk_item
from tests.test_run import fake_fetch, setup

UNI = {"id": "ia", "name": "Intelligence artificielle", "short": "IA", "color": "ia", "order": 1, "domains": ["ia"], "subthemes": []}
ENTITIES = [{"id": "company:openai", "name": "OpenAI", "aliases": ["openai"], "universes": ["ia"], "wikidata": "Q1"},
            {"id": "ai_model:gpt", "name": "GPT", "aliases": ["gpt-6"], "universes": ["ia"]}]
KEYS = ("quoi", "qui", "quand", "pourquoi", "retenir")


def setup_socle(tmp_path):
    setup(tmp_path)
    for rel, data in (("universes/ia.yml", UNI), ("entities/ia.yml", ENTITIES),
                      ("relations.yml", [["company:openai", "produit", "ai_model:gpt"]])):
        path = tmp_path / "config" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")


def no_facts(url, params=None):
    raise ConnectionError("Wikidata injoignable")


def data(tmp_path, name):
    return json.loads((tmp_path / "site" / "data" / name).read_text("utf-8"))


def test_run_publishes_universes_entities_band_and_today(tmp_path):
    setup_socle(tmp_path)
    report = run(tmp_path, now=NOW, fetch=fake_fetch, facts_fetch=no_facts)
    uni = data(tmp_path, "universes/ia.json")
    validate("universeFile", uni)
    ev = uni["events"][0]
    assert ev["universe"] == "ia" and ev["entity_ids"] == ["company:openai", "ai_model:gpt"] and "concerned" not in ev
    home = data(tmp_path, "home.json")
    validate("home", home)
    assert home["today"][0]["ids"] == [ev["id"]]
    page = data(tmp_path, "entities/company/openai.json")
    validate("entityFile", page)
    assert page["events"][0]["id"] == ev["id"] and page["relations"][0]["id"] == "ai_model:gpt"
    validate("entityIndex", data(tmp_path, "entities/index.json"))
    validate("band", data(tmp_path, "band.json"))
    health = data(tmp_path, "health.json")
    assert any(s["source"] == "facts:wikidata" and not s["ok"] for s in health["sources"]) and health["candidates"] == []
    assert report["entities"] == {"linked_pct": 100, "candidates": 0}


def test_llm_title_confirmed_entities_and_unknown_names(tmp_path):
    setup_socle(tmp_path)

    def call(prompt):
        ev_id = prompt.split("## ")[1].split("\n")[0]
        assert "Entités candidates : company:openai, ai_model:gpt" in prompt
        return json.dumps({ev_id: {**{k: f"llm {k}" for k in KEYS}, "titre": "OpenAI lance GPT-6",
                                   "entites": ["ai_model:gpt"], "inconnus": ["Sam Altman", "OpenAI"]}})

    run(tmp_path, now=NOW, fetch=fake_fetch, call=call, facts_fetch=no_facts)
    ev = data(tmp_path, "universes/ia.json")["events"][0]
    assert ev["title_fr"] == "OpenAI lance GPT-6" and ev["entity_ids"] == ["ai_model:gpt"]
    candidates = json.loads((tmp_path / "data" / "candidates.json").read_text("utf-8"))["candidates"]
    assert list(candidates) == ["sam altman"]                   # « OpenAI » est déjà dans le catalogue
    assert data(tmp_path, "health.json")["candidates"][0]["name"] == "Sam Altman"


def test_second_identical_run_rewrites_no_published_file(tmp_path):
    setup_socle(tmp_path)
    run(tmp_path, now=NOW, fetch=fake_fetch, facts_fetch=no_facts)
    files = sorted((tmp_path / "site" / "data").rglob("*.json"))
    before = {p: p.read_bytes() for p in files}
    run(tmp_path, now=NOW, fetch=fake_fetch, facts_fetch=no_facts)
    assert {p: p.read_bytes() for p in files} == before


def test_a_quota_failure_keeps_the_previous_llm_summary():
    e = {**mk_event([mk_item("a", "T")], id="ev_q"), "importance": 80, "level": 1, "reliability": "confirmé",
         "summary": {"quoi": "ancien"}, "summary_mode": "llm", "summary_fp": "vieux", "title_fr": "Ancien titre"}

    def quota(prompt):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    events, touched, errors = add_summaries([e], DOM, G, quota)
    assert events[0] == e and touched == set() and errors == ["quota"]


def test_countries_start_a_concerned_chain_only_for_economic_or_conflict_events():
    from engine.graph import adjacency, build_edges
    from engine.run import _with_concerned
    catalog = {"country:chine": {"name": "Chine", "type": "country"}, "commodity:terres-rares": {"name": "Terres rares", "type": "commodity"}}
    adj = adjacency(build_edges([("country:chine", "produit", "commodity:terres-rares")], [], []))
    g = {"links": {"country_start_kinds": ["sanctions", "conflict"]}}
    base = {"level": 1, "entity_ids": ["country:chine"]}
    assert "concerned" not in _with_concerned({**base, "kind": "diplomacy"}, adj, catalog, g)
    assert _with_concerned({**base, "kind": "sanctions"}, adj, catalog, g)["concerned"][0][0]["to"] == "commodity:terres-rares"


def test_events_without_an_llm_summary_are_summarised_before_older_ones():
    old = {**mk_event([mk_item("o", "Ancien")], id="ev_old"), "importance": 90, "level": 1, "reliability": "confirmé",
           "summary": {"quoi": "x"}, "summary_mode": "llm", "summary_fp": "v1"}
    new = {**mk_event([mk_item("n", "Nouveau")], id="ev_new"), "importance": 60, "level": 1, "reliability": "confirmé"}
    asked = []

    def call(prompt):
        asked.append(prompt.split("## ")[1].split("\n")[0])
        return json.dumps({asked[-1]: {k: "v" for k in KEYS}})

    add_summaries([old, new], DOM, {**G, "ai": {**G["ai"], "max_events_per_run": 1}}, call)
    assert asked == ["ev_new"]
