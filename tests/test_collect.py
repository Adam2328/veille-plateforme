from engine.collect import collect_rss, collect_source

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Alpha - The Verge</title><link>https://ex.com/a</link>
<pubDate>Sat, 26 Sep 2026 10:00:00 GMT</pubDate><description>&lt;p&gt;Hello&lt;/p&gt;</description></item>
<item><title>Sans lien</title></item>
<item><title>Beta</title><link>https://ex.com/b</link><pubDate>Sat, 26 Sep 2026 11:00:00 GMT</pubDate></item>
</channel></rss>"""
SRC = {"id": "s1", "name": "S", "tier": 2, "type": "rss", "url": "mem://1"}


def test_collect_rss_parses_entries_and_skips_those_without_link():
    raws, health = collect_rss(SRC, fetch=lambda url: RSS)
    assert [r["url"] for r in raws] == ["https://ex.com/a", "https://ex.com/b"]
    assert raws[0]["published_at"] == "2026-09-26T10:00:00+00:00"
    assert health == {"source": "s1", "ok": True, "count": 2, "error": None}


def test_publisher_suffix_is_split_from_the_title():
    raws, _ = collect_rss({**SRC, "publisher_suffix": True}, fetch=lambda url: RSS)
    assert (raws[0]["title"], raws[0]["publisher"]) == ("Alpha", "The Verge")
    assert "publisher" not in raws[1]


def test_network_failure_is_reported_not_raised():
    def boom(url):
        raise TimeoutError("délai dépassé")
    raws, health = collect_rss(SRC, fetch=boom)
    assert raws == [] and health["ok"] is False and "TimeoutError" in health["error"]


def test_corrupted_feed_is_reported_not_raised():
    raws, health = collect_rss(SRC, fetch=lambda url: b"ceci n'est pas du xml \x00\xff")
    assert raws == [] and health["ok"] is False


def test_empty_but_valid_feed_is_ok_with_zero_items():
    empty = b'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'
    raws, health = collect_rss(SRC, fetch=lambda url: empty)
    assert raws == [] and health["ok"] is True and health["count"] == 0


def test_limit_caps_the_number_of_entries():
    raws, _ = collect_rss(SRC, fetch=lambda url: RSS, limit=1)
    assert len(raws) == 1


def test_unknown_source_type_is_reported():
    raws, health = collect_source({**SRC, "type": "carrier-pigeon"})
    assert raws == [] and health["ok"] is False and "carrier-pigeon" in health["error"]
