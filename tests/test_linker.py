from engine.linker import build_matcher, event_text, final_ids, link
from tests.helpers import mk_event, mk_item

CATALOG = {
    "company:apple": {"aliases": ["=Apple", "iphone"]},
    "company:meta": {"aliases": ["=Meta", "meta ai"]},
    "tech:data-centers": {"aliases": ["data center", "data centers"]},
    "country:france": {"aliases": ["france"]},
    "team:lille": {"aliases": ["lille"], "link_in": ["sport"]},
}


def test_whole_words_only_and_case_sensitive_aliases():
    m = build_matcher(CATALOG)
    assert link("Apple sort un nouvel iPhone", m) == ["company:apple"]
    assert link("une recette d'apple pie", m) == []
    assert link("Le metaverse ne sauve pas Meta", m) == ["company:meta"]


def test_order_follows_the_first_mention():
    assert link("Des data centers en France pour Meta", build_matcher(CATALOG)) == ["tech:data-centers", "country:france", "company:meta"]


def test_the_longest_alias_wins_at_the_same_position():
    m = build_matcher({"tech:data": {"aliases": ["data"]}, "tech:data-centers": {"aliases": ["data centers"]}})
    assert link("Les data centers consomment", m) == ["tech:data-centers"]


def test_link_in_restricts_an_entity_to_its_universes():
    assert link("Lille bat Lens", build_matcher(CATALOG, "sport")) == ["team:lille"]
    assert link("Le maire de Lille", build_matcher(CATALOG, "geopolitique")) == []
    assert link("Le maire de Lille", build_matcher(CATALOG)) == ["team:lille"]      # sans univers : tout le catalogue


def test_empty_catalog_links_nothing():
    assert link("Apple", build_matcher({})) == []


def test_event_text_puts_the_event_title_first():
    ev = mk_event([mk_item("a", "La France et Apple", snippet="Meta aussi")], title="Apple en tête")
    assert link(event_text(ev), build_matcher(CATALOG)) == ["company:apple", "country:france", "company:meta"]


def test_final_ids_keeps_confirmed_and_never_offered_candidates_in_order():
    ev = {"candidates": ["a", "b", "c"], "llm_offered": ["a", "b"], "llm_entities": ["b"]}
    assert final_ids(ev) == ["b", "c"]
    assert final_ids({"candidates": ["a"]}) == ["a"]
    assert final_ids({}) == []


def test_link_domains_restricts_an_entity_to_its_domains():
    catalog = {"team:nice": {"aliases": ["=Nice"], "link_in": ["sport"], "link_domains": ["football"]}}
    assert link("Nice s'impose à domicile", build_matcher(catalog, "sport", "football")) == ["team:nice"]
    assert link("Finale à Nice pour les volleyeurs", build_matcher(catalog, "sport", "volley")) == []
