import json
import pathlib
import subprocess

import pytest

from engine.contract import validate

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "site" / "tools" / "make-sample.mjs"


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    out = tmp_path_factory.mktemp("sample")
    subprocess.run(["node", str(SCRIPT), str(out)], check=True, capture_output=True)
    return out


def test_sample_home_matches_contract(data):
    home = json.loads((data / "home.json").read_text("utf-8"))
    validate("home", home)
    assert home["sample"] is True
    ids = {i for d in home["domains"] for n in "123" for i in d["levels"][n]}
    assert ids <= set(home["events"])          # aucune référence orpheline
    assert set(home["retain"]) <= set(home["events"])


def test_sample_covers_every_reliability_and_level(data):
    home = json.loads((data / "home.json").read_text("utf-8"))
    evs = home["events"].values()
    assert {e["reliability"] for e in evs} >= {"officiel", "confirmé", "rapporté", "en_développement", "rumeur"}
    assert {e["level"] for e in evs} == {1, 2, 3}


def test_sample_domain_files_match_contract(data):
    for name in ("ia", "finance", "football"):
        validate("domainFile", json.loads((data / "domains" / f"{name}.json").read_text("utf-8")))


def test_rumors_never_reach_level_one(data):
    home = json.loads((data / "home.json").read_text("utf-8"))
    assert all(e["level"] > 1 for e in home["events"].values() if e["reliability"] in ("rumeur", "non_confirmé"))


def test_sample_includes_layers_and_valid_quotes(data):
    home = json.loads((data / "home.json").read_text("utf-8"))
    assert any(e.get("layers") for e in home["events"].values())
    quotes = json.loads((data / "quotes.json").read_text("utf-8"))
    validate("quotes", quotes)
    assert any(q["stale"] for q in quotes["quotes"]) and any(q["group"] == "Taux" for q in quotes["quotes"])
