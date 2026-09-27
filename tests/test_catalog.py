import pytest
import yaml

from engine.catalog import check_universes, football_teams, load_catalog, load_relations, load_universes, slug
from engine.config import load_config

UNI = {"id": "ia", "name": "IA", "short": "IA", "color": "ia", "order": 1, "domains": ["ia"], "subthemes": []}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")


def test_slug_removes_accents_and_punctuation():
    assert slug("Équipe de France !") == "equipe-de-france"
    assert slug("S&P 500") == "s-p-500"


def test_repo_universes_are_ordered_and_cover_every_domain():
    cfg = load_config()
    assert list(cfg["universes"]) == ["finance", "ia", "geopolitique", "sport"]
    assert check_universes(cfg["universes"], cfg["domains"]) == []
    assert {"today", "links", "band"} <= set(cfg["global"])


def test_a_domain_in_two_universes_or_in_none_is_reported():
    unis = {"a": {**UNI, "id": "a", "domains": ["ia", "finance"]}, "b": {**UNI, "id": "b", "domains": ["ia"]}}
    errors = check_universes(unis, {"ia": {}, "finance": {}, "tennis": {}})
    assert any("deux univers" in e for e in errors) and any("tennis" in e for e in errors)


def test_catalog_rejects_bad_ids_duplicates_missing_aliases_unknown_universes_and_bad_qids(tmp_path):
    write(tmp_path / "config" / "entities" / "x.yml", [
        {"id": "company:ok", "name": "Ok", "aliases": ["ok"], "universes": ["ia"]},
        {"id": "company:ok", "name": "Ok", "aliases": ["ok2"], "universes": ["ia"]},
        {"id": "planet:mars", "name": "Mars", "aliases": ["mars"], "universes": ["ia"]},
        {"id": "company:sans-alias", "name": "X", "universes": ["ia"]},
        {"id": "company:ailleurs", "name": "Y", "aliases": ["y"], "universes": ["espace"]},
        {"id": "company:qid", "name": "Z", "aliases": ["z"], "universes": ["ia"], "wikidata": "142"},
    ])
    with pytest.raises(ValueError) as err:
        load_catalog(tmp_path, {"ia": UNI})
    msg = str(err.value)
    assert "double" in msg and "planet:mars" in msg and "sans-alias" in msg and "espace" in msg and "company:qid" in msg


def test_catalog_entries_receive_their_type(tmp_path):
    write(tmp_path / "config" / "entities" / "x.yml", [{"id": "company:ok", "name": "Ok", "aliases": ["ok"], "universes": ["ia"]}])
    assert load_catalog(tmp_path, {"ia": UNI})["company:ok"]["type"] == "company"


def test_relations_must_link_known_entities_with_a_known_verb(tmp_path):
    catalog = {"company:a": {}, "company:b": {}}
    write(tmp_path / "config" / "relations.yml", [["company:a", "fournit", "company:b"]])
    assert load_relations(tmp_path, catalog) == [("company:a", "fournit", "company:b")]
    write(tmp_path / "config" / "relations.yml", [["company:a", "aime", "company:b"], ["company:a", "fournit", "company:z"]])
    with pytest.raises(ValueError):
        load_relations(tmp_path, catalog)


def test_missing_folders_give_an_empty_configuration(tmp_path):
    assert load_universes(tmp_path) == {} and load_catalog(tmp_path, {}) == {} and load_relations(tmp_path, {}) == []


def test_football_teams_are_added_for_unknown_names_and_only_in_sport():
    football = {"competitions": [{"standings": [{"team": "Lille"}, {"team": "Real Sociedad"}]}]}
    catalog = {"team:lille": {"aliases": ["lille"]}}
    teams = football_teams(football, catalog, {"sport": {}})
    assert list(teams) == ["team:real-sociedad"]
    assert teams["team:real-sociedad"] == {"id": "team:real-sociedad", "name": "Real Sociedad", "type": "team",
                                          "aliases": ["real sociedad"], "universes": ["sport"], "link_in": ["sport"]}
    assert football_teams(football, catalog, {}) == {} and football_teams(None, catalog, {"sport": {}}) == {}
