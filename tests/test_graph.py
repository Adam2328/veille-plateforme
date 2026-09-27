from engine.graph import adjacency, build_edges, concerned, cooccurrence

CAT = {i: {"name": n, "type": i.split(":")[0], **extra} for i, n, extra in [
    ("country:iran", "Iran", {}), ("commodity:petrole", "Pétrole", {}), ("sector:energie", "Énergie", {}),
    ("etf:xle", "XLE", {"ticker": "XLE"}), ("company:total", "TotalEnergies", {"ticker": "TTE"}), ("org:onu", "ONU", {})]}
REL = [("country:iran", "produit", "commodity:petrole"), ("sector:energie", "expose", "commodity:petrole"),
       ("etf:xle", "suit", "sector:energie"), ("company:total", "expose", "commodity:petrole"),
       ("country:iran", "membre_de", "org:onu")]


def test_cooccurrence_needs_three_shared_events():
    evs = [{"entity_ids": ["a", "b"]}] * 3 + [{"entity_ids": ["a", "c"]}] * 2 + [{}]
    assert cooccurrence(evs) == [{"src": "a", "verb": "lie_a", "dst": "b", "weight": 3, "origin": "cooccurrence"}]


def test_edges_are_deduplicated_and_readable_in_both_directions():
    edges = build_edges([*REL, REL[0]], [{"src": "org:onu", "verb": "membre_de", "dst": "country:iran", "weight": 1, "origin": "wikidata"}], [])
    assert len(edges) == len(REL) + 1
    adj = adjacency(edges)
    assert {"id": "country:iran", "verb": "produit", "label": "produit par", "weight": 1, "origin": "config"} in adj["commodity:petrole"]
    assert {"id": "commodity:petrole", "verb": "produit", "label": "produit", "weight": 1, "origin": "config"} in adj["country:iran"]


def test_concerned_follows_only_exposure_links_up_to_two_hops_and_ranks_tradable_assets_first():
    chains = concerned(["country:iran"], adjacency(build_edges(REL, [], [])), CAT)
    assert [[s["to"] for s in c] for c in chains] == [["commodity:petrole"], ["commodity:petrole", "company:total"],
                                                     ["commodity:petrole", "sector:energie"]]
    assert chains[1][1] == {"from": "commodity:petrole", "to": "company:total", "label": "influence"}


def test_an_event_about_oil_reaches_the_energy_etf():
    chains = concerned(["commodity:petrole"], adjacency(build_edges(REL, [], [])), CAT)
    assert ["sector:energie", "etf:xle"] in [[s["to"] for s in c] for c in chains]
    assert all(c[-1]["to"] != "commodity:petrole" for c in chains)          # jamais une entité de départ


def test_concerned_is_limited_and_ignores_unknown_entities():
    adj = adjacency(build_edges(REL, [{"src": "company:total", "verb": "expose", "dst": "company:inconnue", "weight": 1, "origin": "wikidata"}], []))
    chains = concerned(["commodity:petrole"], adj, CAT, limit=2)
    assert len(chains) == 2 and all(c[-1]["to"] in CAT for c in chains)
