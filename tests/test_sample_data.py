import json
import pathlib

from engine.contract import validate

DATA = pathlib.Path(__file__).resolve().parent.parent / "site" / "data"


def test_sample_home_matches_contract():
    home = json.loads((DATA / "home.json").read_text("utf-8"))
    validate("home", home)
    assert home["sample"] is True
    ids = {i for d in home["domains"] for n in "123" for i in d["levels"][n]}
    assert ids <= set(home["events"])          # aucune référence orpheline
    assert set(home["retain"]) <= set(home["events"])


def test_sample_covers_every_reliability_and_level():
    home = json.loads((DATA / "home.json").read_text("utf-8"))
    evs = home["events"].values()
    assert {e["reliability"] for e in evs} >= {"officiel", "confirmé", "rapporté", "en_développement", "rumeur"}
    assert {e["level"] for e in evs} == {1, 2, 3}


def test_sample_domain_files_match_contract():
    for name in ("ia", "finance", "football"):
        validate("domainFile", json.loads((DATA / "domains" / f"{name}.json").read_text("utf-8")))


def test_rumors_never_reach_level_one():
    home = json.loads((DATA / "home.json").read_text("utf-8"))
    assert all(e["level"] > 1 for e in home["events"].values() if e["reliability"] in ("rumeur", "non_confirmé"))
