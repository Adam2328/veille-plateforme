from datetime import timedelta

from engine.cluster import merge_events
from engine.store import append, load_recent
from engine.timeutil import iso
from tests.helpers import DOM, G, NOW, mk_event, mk_item

MERGE_G = {**G, "cluster": {**G["cluster"], "merge_threshold": 0.30}}   # seuil de test ; le seuil réel se calibre sur les données
COURT_A = ["Court rules Pentagon can blacklist Anthropic for refusing to enable Claude features",
           "Federal appeals court rules Pentagon blacklist of Anthropic was legal",
           "Anthropic loses appeals court bid to overturn Pentagon supply chain risk label"]
COURT_B = ["D.C. Circuit upholds Pentagon ban on Anthropic Claude over national security risk",
           "Appeals court upholds Pentagon ban on Anthropic",
           "US court sides with Pentagon in Anthropic AI ban"]
MONEY = ["Anthropic to pay Akamai billion over seven years in cloud deal",
         "Anthropic founders seek voting control ahead of IPO"]


def _ev(prefix, titles, **kw):
    items = [mk_item(f"{prefix}{n}", t, origin=f"{prefix}-origin-{n}") for n, t in enumerate(titles)]
    return mk_event(items, id=f"ev_{prefix}", entities=["Anthropic"], **kw)


def test_two_events_telling_the_same_story_are_merged_into_the_larger_one():
    a, b = _ev("a", COURT_A), _ev("b", COURT_B[:2])
    events, merges = merge_events([b, a], DOM, MERGE_G, NOW)
    assert [e["id"] for e in events] == ["ev_a"] and len(events[0]["items"]) == 5
    assert [(d["id"], sid) for d, sid in merges] == [("ev_b", "ev_a")]
    assert events[0]["rev"] == a["rev"] + 1                       # de nouvelles origines sont apparues


def test_different_stories_sharing_only_a_big_name_never_merge():
    events, merges = merge_events([_ev("a", COURT_A), _ev("m", MONEY)], DOM, MERGE_G, NOW)
    assert len(events) == 2 and merges == []


def test_each_event_takes_part_in_at_most_one_merge_per_run():
    a, b, c = _ev("a", COURT_A), _ev("b", COURT_B), _ev("c", COURT_A[:1] + COURT_B[:1])
    events, merges = merge_events([a, b, c], DOM, MERGE_G, NOW)
    assert len(events) == 2 and len(merges) == 1


def test_merge_is_disabled_without_a_threshold_and_ignores_other_domains_and_stale_events():
    a, b = _ev("a", COURT_A), _ev("b", COURT_B)
    no_threshold = {**G, "cluster": {k: v for k, v in G["cluster"].items() if k != "merge_threshold"}}
    assert merge_events([a, b], DOM, no_threshold, NOW)[1] == []
    assert merge_events([a, {**b, "domain": "finance"}], DOM, MERGE_G, NOW)[1] == []
    assert merge_events([a, {**b, "updated_at": iso(NOW - timedelta(hours=72))}], DOM, MERGE_G, NOW)[1] == []


def test_merge_does_not_mutate_its_inputs_and_is_stable_on_a_second_pass():
    a, b = _ev("a", COURT_A), _ev("b", COURT_B)
    snapshot = [dict(e, items=list(e["items"])) for e in (a, b)]
    events, _ = merge_events([a, b], DOM, MERGE_G, NOW)
    assert [a, b] == snapshot
    again, merges = merge_events(events, DOM, MERGE_G, NOW)
    assert merges == [] and again == events


def test_better_tier_after_a_merge_replaces_the_title():
    a = _ev("a", COURT_A)
    official = mk_event([mk_item("o1", COURT_B[0], tier=1, origin="pentagon"), mk_item("o2", COURT_B[1], origin="o-2")],
                        id="ev_o", entities=["Anthropic"])
    events, _ = merge_events([a, official], DOM, MERGE_G, NOW)
    assert len(events) == 1 and events[0]["title"] == COURT_B[0]


def test_merged_events_are_not_loaded_again(tmp_path):
    keep, gone = mk_event([mk_item("a", "x")], id="ev_keep"), mk_event([mk_item("b", "y")], id="ev_gone")
    append(tmp_path, [keep, gone], NOW)
    append(tmp_path, [{**gone, "merged_into": "ev_keep"}], NOW)
    assert [e["id"] for e in load_recent(tmp_path, NOW)] == ["ev_keep"]


def test_run_merges_tombstones_and_the_absorbed_event_does_not_come_back(tmp_path):
    import shutil

    import yaml

    from engine.config import ROOT
    from engine.run import run
    from tests.test_run import DOM as RUN_DOM

    (tmp_path / "config" / "domains").mkdir(parents=True)
    g = yaml.safe_load((ROOT / "config" / "global.yml").read_text("utf-8"))
    g["cluster"]["merge_threshold"] = 0.30
    (tmp_path / "config" / "global.yml").write_text(yaml.safe_dump(g, allow_unicode=True), "utf-8")
    (tmp_path / "config" / "domains" / "ia.yml").write_text(yaml.safe_dump(RUN_DOM, allow_unicode=True), "utf-8")
    append(tmp_path, [_ev("a", COURT_A), _ev("b", COURT_B[:2])], NOW)
    empty = lambda url: b"<rss version='2.0'><channel><title>t</title></channel></rss>"
    new = [mk_item("n", COURT_B[2], origin="n-origin")]
    import engine.run as r
    real_collect = r.collect_domain
    r.collect_domain = lambda dom, g, now, fetch: (new, [])
    try:
        run(tmp_path, now=NOW, fetch=empty)
    finally:
        r.collect_domain = real_collect
    ids = sorted(e["id"] for e in load_recent(tmp_path, NOW))
    assert len(ids) == 1 and ids[0] in ("ev_a", "ev_b")
    run(tmp_path, now=NOW, fetch=empty)
    assert sorted(e["id"] for e in load_recent(tmp_path, NOW)) == ids
    shutil.rmtree(tmp_path / "config")
