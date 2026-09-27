from datetime import timedelta

from engine.contract import validate
from engine.search import build_index
from engine.timeutil import iso
from tests.helpers import NOW, mk_event, mk_item

DOMAINS = {"ia": {"id": "ia", "name": "IA"}, "football": {"id": "football", "name": "Football"}}
SUMMARY = {k: "v" for k in ("quoi", "qui", "quand", "pourquoi")}


def ev(id, level, hours_ago=1, domain="ia", **kw):
    e = mk_event([mk_item(f"{id}i", f"Titre {id}", tier=2)], id=id, domain=domain,
                 updated_at=iso(NOW - timedelta(hours=hours_ago)))
    return {**e, "level": level, "importance": 70, "reliability": "confirmé", "reliability_reason": "r",
            "summary": {**SUMMARY, "retenir": f"À retenir {id}"}, **kw}


def test_index_keeps_levels_one_and_two_for_30_days_and_level_three_for_7_days():
    events = [ev("a", 1), ev("b", 2, hours_ago=24 * 20), ev("c", 3, hours_ago=24 * 3), ev("d", 3, hours_ago=24 * 10),
              ev("e", 1, hours_ago=24 * 40), ev("f", 0)]
    idx = build_index(events, DOMAINS, NOW)
    validate("search", idx)
    assert [x["id"] for x in idx["events"]] == ["a", "c", "b"]          # du plus récent au plus ancien


def test_index_entries_are_compact_and_carry_what_the_site_needs():
    x = build_index([ev("a", 1, entities=["OpenAI"])], DOMAINS, NOW)["events"][0]
    assert x == {"id": "a", "domain": "ia", "title": "Titre a", "retenir": "À retenir a", "entities": ["OpenAI"],
                 "date": iso(NOW - timedelta(hours=1)), "level": 1, "reliability": "confirmé",
                 "source": "src-ai", "url": "https://example.com/ai"}


def test_event_without_summary_uses_the_best_source_title_and_unknown_domains_are_skipped():
    no_summary = ev("a", 3, summary=None)
    idx = build_index([no_summary, ev("z", 1, domain="inconnu")], DOMAINS, NOW)
    assert [x["id"] for x in idx["events"]] == ["a"] and idx["events"][0]["retenir"] == ""
    assert idx["domains"] == [{"id": "ia", "name": "IA"}, {"id": "football", "name": "Football"}]


def test_index_is_capped_to_keep_the_file_light():
    events = [ev(f"e{i}", 1, hours_ago=i / 10) for i in range(50)]
    assert len(build_index(events, DOMAINS, NOW, cap=20)["events"]) == 20


def test_run_publishes_a_valid_search_index(tmp_path):
    import json

    from engine.run import run
    from tests.test_run import fake_fetch, setup

    setup(tmp_path)
    run(tmp_path, now=NOW, fetch=fake_fetch)
    idx = json.loads((tmp_path / "site" / "data" / "search.json").read_text("utf-8"))
    validate("search", idx)
    assert len(idx["events"]) == 1 and idx["events"][0]["domain"] == "ia"
