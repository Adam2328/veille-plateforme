from engine.normalize import clean, dedupe, item_id, normalize, origin_of, recent
from tests.helpers import NOW, mk_item

SRC = {"name": "Source A", "tier": 2, "origin": "source a", "domain": "ia"}
RAW = {"title": " <b>Titre</b> &amp; suite ", "url": "https://ex.com/A", "snippet": "<p>Bonjour  monde</p>",
       "published_at": "2026-09-26T10:00:00+00:00"}


def test_clean_strips_tags_entities_and_whitespace():
    assert clean(" <b>Titre</b> &amp; suite ") == "Titre & suite"
    assert clean(None) == ""


def test_item_id_is_stable_and_case_insensitive():
    assert item_id("https://ex.com/A") == item_id("HTTPS://EX.COM/a")
    assert item_id("https://ex.com/A").startswith("it_")


def test_normalize_builds_item_with_default_origin():
    it = normalize(RAW, SRC)
    assert it["title"] == "Titre & suite" and it["snippet"] == "Bonjour monde"
    assert it["origin"] == "source a" and it["tier"] == 2 and it["source"] == "Source A" and it["domain"] == "ia"


def test_attribution_makes_syndicated_copy_share_the_original_origin():
    assert origin_of("le blog", "Selon L'Équipe, un joueur blessé", "") == "l'équipe"
    assert origin_of("le blog", "Un joueur blessé", "D'après Financial Times, la banque parle") == "financial times"
    assert origin_of("le blog", "Un joueur blessé", "") == "le blog"


def test_attribution_keyword_must_be_a_whole_word():
    assert origin_of("le blog", "Octavia Spencer joue dans le film", "") == "le blog"


def test_publisher_from_aggregator_gets_publisher_name_origin_and_tier():
    agg = {"name": "Google Actualités", "tier": 4, "domain": "ia"}
    it = normalize({**RAW, "publisher": "The Verge"}, agg, {"the verge": 2})
    assert (it["source"], it["origin"], it["tier"]) == ("The Verge", "the verge", 2)
    unknown = normalize({**RAW, "publisher": "Blog Inconnu"}, agg, {"the verge": 2})
    assert unknown["tier"] == 4


def test_dedupe_drops_known_ids_duplicate_ids_and_duplicate_titles():
    a = mk_item("a", "Même titre !")
    b = mk_item("b", "même   titre")                    # autre id, même titre normalisé
    c = mk_item("c", "Autre titre")
    dup = {**c}
    known = mk_item("k", "Connu")
    assert [i["id"] for i in dedupe([a, b, c, dup, known], {"k"})] == ["a", "c"]


def test_recent_drops_items_older_than_the_window():
    fresh = mk_item("f", "x", minutes_ago=60)
    old = mk_item("o", "y", minutes_ago=37 * 60)
    assert [i["id"] for i in recent([fresh, old], NOW, 36)] == ["f"]
