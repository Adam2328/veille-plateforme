from engine.config import load_config

REQUIRED = {"id", "name", "accent", "order", "quota", "max_l1", "thresholds", "entities", "kinds", "sources"}


def test_every_configured_domain_is_well_formed():
    cfg = load_config()
    assert "ia" in cfg["domains"]
    for dom in cfg["domains"].values():
        assert REQUIRED <= set(dom), dom["id"]
        t = dom["thresholds"]
        assert t["l1"] > t["l2"] > t["l3"] > 0
        ids = [s["id"] for s in dom["sources"]]
        assert len(ids) == len(set(ids)), f"ids de source dupliqués dans {dom['id']}"
        assert all(s["tier"] in (1, 2, 3, 4, 5) and s["type"] == "rss" and s["url"].startswith("http") for s in dom["sources"])
        assert all(isinstance(a, list) and a for a in dom["entities"].values())
        assert all({"weight", "keywords"} <= set(k) for k in dom["kinds"].values())
