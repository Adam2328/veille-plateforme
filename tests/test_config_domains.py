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


import datetime as dt

from engine.summarize import PROFILES


def test_finance_domain_is_configured_with_the_finance_profile_and_a_valid_agenda():
    cfg = load_config()
    fin = cfg["domains"]["finance"]
    assert fin["summary_profile"] == "finance"
    assert fin["order"] > cfg["domains"]["ia"]["order"]
    assert len({s["tier"] for s in fin["sources"]}) >= 3
    assert {"central_bank", "earnings"} <= set(fin["kinds"])
    assert fin["agenda_url"].startswith("https://") and fin["agenda_keywords"]
    for entry in fin["agenda"]:
        assert isinstance(entry["date"], (dt.date, str)) and entry["title"].strip()
        dt.date.fromisoformat(str(entry["date"]))


def test_every_summary_profile_used_by_a_domain_exists():
    for dom in load_config()["domains"].values():
        assert dom.get("summary_profile", "default") in PROFILES


def test_publishers_cover_the_main_financial_outlets():
    publishers = load_config()["global"]["publishers"]
    assert {"bloomberg", "wsj", "cnbc", "marketwatch", "financial times"} <= set(publishers)


def test_football_domain_is_configured_with_rumor_rules_and_noise_filters():
    cfg = load_config()
    fb = cfg["domains"]["football"]
    assert fb["order"] > cfg["domains"]["finance"]["order"] and fb["relevance"] is True
    assert {"transfer", "injury", "suspension", "result", "coach"} <= set(fb["kinds"])
    assert len({s["tier"] for s in fb["sources"]}) >= 3 and len(fb["sources"]) >= 12
    assert fb["rumor_markers"] and fb["confirm_markers"]
    assert not set(m.lower() for m in fb["rumor_markers"]) & set(m.lower() for m in fb["confirm_markers"])
    for word in ("pronostic", "bookmaker", "ea fc"):
        assert any(word in e.lower() for e in fb["exclude"]), word


def test_publishers_cover_the_main_football_outlets():
    publishers = load_config()["global"]["publishers"]
    assert {"rmc sport", "eurosport", "sky sports", "bbc sport", "espn", "marca"} <= set(publishers)
