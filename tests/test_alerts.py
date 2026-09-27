from datetime import timedelta

from engine.alerts import prune_sent, select_alerts, send_ntfy
from engine.timeutil import iso
from tests.helpers import NOW, mk_event, mk_item

G = {"alerts": {"max_per_day": 3, "recent_hours": 6, "site_url": "https://veille.example/"}}
DOMS = {"ia": {"id": "ia", "name": "IA", "thresholds": {"l1": 58}, "alert_kinds": ["model_release"]},
        "finance": {"id": "finance", "name": "Finance", "thresholds": {"l1": 53}, "alert_kinds": ["central_bank"], "alert_min": 60},
        "tennis": {"id": "tennis", "name": "Tennis", "thresholds": {"l1": 75}}}


def ev(id, domain="ia", importance=90, level=1, reliability="officiel", kind="model_release", hours_ago=1):
    e = mk_event([mk_item(f"{id}i", f"Titre {id}", tier=1)], id=id, domain=domain, kind=kind,
                 first_seen=iso(NOW - timedelta(hours=hours_ago)))
    return {**e, "importance": importance, "level": level, "reliability": reliability,
            "summary": {"retenir": f"À retenir {id}"}}


def ids(events, sent=None):
    return [e["id"] for e in select_alerts(events, DOMS, G, sent or {}, NOW)]


def test_only_major_confirmed_recent_events_of_listed_kinds_trigger_an_alert():
    events = [ev("ok"), ev("level2", level=2), ev("rumeur", reliability="rumeur"), ev("rapporte", reliability="rapporté"),
              ev("kind", kind="research"), ev("old", hours_ago=10), ev("low", importance=60)]
    assert ids(events) == ["ok"]


def test_default_minimum_is_the_level_one_threshold_plus_ten_and_can_be_overridden():
    assert ids([ev("a", importance=67)]) == [] and ids([ev("b", importance=68)]) == ["b"]          # IA : 58 + 10
    assert ids([ev("c", domain="finance", kind="central_bank", importance=61)]) == ["c"]           # alert_min explicite


def test_domains_without_alert_kinds_never_alert():
    assert ids([ev("t", domain="tennis", kind="final", importance=99)]) == []


def test_at_most_three_alerts_per_day_highest_importance_first_and_never_twice():
    events = [ev(f"e{i}", importance=80 + i) for i in range(5)]
    assert ids(events) == ["e4", "e3", "e2"]
    already = {"e4": iso(NOW - timedelta(hours=2)), "x": iso(NOW - timedelta(hours=3))}
    assert ids(events, already) == ["e3"]                                  # 2 déjà envoyées aujourd'hui
    assert ids(events, {"e4": iso(NOW - timedelta(days=2))}) == ["e3", "e2", "e1"]


def test_send_ntfy_posts_a_short_message_that_opens_the_event_page():
    calls = []
    send_ntfy("mon-canal", ev("a"), DOMS["ia"], G, post=lambda url, **kw: calls.append((url, kw)))
    url, kw = calls[0]
    assert url == "https://ntfy.sh/mon-canal"
    assert kw["headers"]["Click"] == "https://veille.example/#/e/a"
    assert kw["headers"]["Title"] == "Vigie - IA" and "Titre a" in kw["data"].decode("utf-8")
    assert "À retenir a" in kw["data"].decode("utf-8") and kw["timeout"] > 0


def test_non_ascii_titles_are_sent_as_utf8_body_not_as_headers():
    calls = []
    e = {**ev("a"), "title": "Décision de la BCE : taux inchangés"}
    send_ntfy("c", e, DOMS["ia"], G, post=lambda url, **kw: calls.append(kw))
    assert "Décision" in calls[0]["data"].decode("utf-8")
    assert all(v.isascii() for v in calls[0]["headers"].values())


def test_prune_sent_forgets_alerts_older_than_a_week():
    sent = {"old": iso(NOW - timedelta(days=8)), "new": iso(NOW - timedelta(days=1))}
    assert prune_sent(sent, NOW) == {"new": sent["new"]}


def test_run_sends_each_alert_once_and_never_without_a_topic(tmp_path):
    import json

    import yaml

    from engine.run import run
    from tests.test_run import DOM, NOW as RUN_NOW, fake_fetch, setup

    setup(tmp_path)
    dom = {**DOM, "alert_kinds": ["model_release"], "alert_min": 0,
           "sources": [{**DOM["sources"][0], "tier": 1}, DOM["sources"][1]]}      # source officielle
    (tmp_path / "config" / "domains" / "ia.yml").write_text(yaml.safe_dump(dom, allow_unicode=True), "utf-8")
    g = yaml.safe_load((tmp_path / "config" / "global.yml").read_text("utf-8"))
    g["alerts"] = {"max_per_day": 3, "recent_hours": 6, "site_url": "https://veille.example/"}
    (tmp_path / "config" / "global.yml").write_text(yaml.safe_dump(g, allow_unicode=True), "utf-8")
    posts = []
    run(tmp_path, now=RUN_NOW, fetch=fake_fetch, ntfy_topic=None, ntfy_post=lambda url, **kw: posts.append(url))
    assert posts == []
    report = run(tmp_path, now=RUN_NOW, fetch=fake_fetch, ntfy_topic="canal", ntfy_post=lambda url, **kw: posts.append(url))
    run(tmp_path, now=RUN_NOW, fetch=fake_fetch, ntfy_topic="canal", ntfy_post=lambda url, **kw: posts.append(url))
    sent = json.loads((tmp_path / "data" / "alerts.json").read_text("utf-8"))
    assert len(posts) == len(sent) == report["alerts"] == 1
    assert all(p == "https://ntfy.sh/canal" for p in posts)


def test_a_failed_send_is_reported_and_retried_next_cycle(tmp_path):
    import yaml

    from engine.run import run
    from tests.test_run import DOM, NOW as RUN_NOW, fake_fetch, setup

    setup(tmp_path)
    dom = {**DOM, "alert_kinds": ["model_release"], "alert_min": 0,
           "sources": [{**DOM["sources"][0], "tier": 1}, DOM["sources"][1]]}      # source officielle
    (tmp_path / "config" / "domains" / "ia.yml").write_text(yaml.safe_dump(dom, allow_unicode=True), "utf-8")
    g = yaml.safe_load((tmp_path / "config" / "global.yml").read_text("utf-8"))
    g["alerts"] = {"max_per_day": 3, "recent_hours": 6, "site_url": "https://veille.example/"}
    (tmp_path / "config" / "global.yml").write_text(yaml.safe_dump(g, allow_unicode=True), "utf-8")

    def down(url, **kw):
        raise ConnectionError("ntfy injoignable")

    report = run(tmp_path, now=RUN_NOW, fetch=fake_fetch, ntfy_topic="canal", ntfy_post=down)
    assert report["alerts"] == 0 and "alerts:ntfy" in report["sources_failed"]
    posts = []
    run(tmp_path, now=RUN_NOW, fetch=fake_fetch, ntfy_topic="canal", ntfy_post=lambda url, **kw: posts.append(url))
    assert posts
