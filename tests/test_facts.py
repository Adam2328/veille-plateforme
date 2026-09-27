import json
from datetime import timedelta

from engine.facts import collect_facts, load_facts, refresh_facts, with_gdp
from tests.helpers import NOW

CAT = {
    "country:france": {"type": "country", "wikidata": "Q142"},
    "person:emmanuel-macron": {"type": "person", "wikidata": "Q3052772"},
    "org:otan": {"type": "org", "wikidata": "Q7184"},
    "company:sans-qid": {"type": "company"},
    "company:disparue": {"type": "company", "wikidata": "Q999"},
}


def ref(q, rank="normal", end=False):
    claim = {"rank": rank, "mainsnak": {"snaktype": "value", "datavalue": {"type": "wikibase-entityid", "value": {"id": q}}}}
    return {**claim, "qualifiers": {"P582": [{}]}} if end else claim


def val(kind, value, rank="normal"):
    return {"rank": rank, "mainsnak": {"snaktype": "value", "datavalue": {"type": kind, "value": value}}}


def item(label, claims=None, desc=None):
    return {"labels": {"fr": {"value": label}}, "descriptions": {"fr": {"value": desc}} if desc else {}, "claims": claims or {}}


ENTITIES = {
    "Q142": item("France", desc="pays d'Europe de l'Ouest", claims={
        "P36": [ref("Q90")],
        "P1082": [val("quantity", {"amount": "+68400000"})],
        "P35": [ref("Q1", end=True), ref("Q3052772")],
        "P38": [ref("Q4916"), ref("Q181", rank="deprecated")],
        "P463": [ref("Q7184")],
        "P41": [val("string", "Flag of France.svg")],
        "P297": [val("string", "FR")],
        "P6": [{"rank": "normal", "mainsnak": {"snaktype": "somevalue"}}],
    }),
    "Q3052772": item("Emmanuel Macron", claims={"P569": [val("time", {"time": "+1977-12-21T00:00:00Z", "precision": 11})],
                                                "P27": [ref("Q142")]}),
    "Q7184": item("OTAN", claims={"P571": [val("time", {"time": "+1949-04-04T00:00:00Z", "precision": 9})]}),
    "Q90": item("Paris"), "Q4916": item("euro"), "Q1": item("Ancien président"), "Q181": item("franc"),
}


def fake(entities=ENTITIES, calls=None):
    def fetch(url, params=None):
        if calls is not None:
            calls.append(url)
        if "wikidata" in url:
            return {"entities": {i: entities.get(i, {"id": i, "missing": ""}) for i in params["ids"].split("|")}}
        raise ConnectionError(url)
    return fetch


def test_facts_are_labelled_formatted_current_and_linked():
    facts = collect_facts(CAT, fake())
    fr = facts["country:france"]
    assert fr["description"] == "pays d'Europe de l'Ouest" and fr["iso2"] == "FR"
    assert fr["image"] == "https://commons.wikimedia.org/wiki/Special:FilePath/Flag_of_France.svg?width=480"
    values = {f["label"]: f["value"] for f in fr["facts"]}
    assert values == {"Capitale": "Paris", "Population": "68,4 millions", "Chef de l'État": "Emmanuel Macron", "Monnaie": "euro"}
    assert {"src": "person:emmanuel-macron", "verb": "dirige", "dst": "country:france", "weight": 1, "origin": "wikidata"} in fr["edges"]
    assert {"src": "country:france", "verb": "membre_de", "dst": "org:otan", "weight": 1, "origin": "wikidata"} in fr["edges"]
    macron = {f["label"]: f["value"] for f in facts["person:emmanuel-macron"]["facts"]}
    assert macron == {"Naissance": "21 décembre 1977", "Nationalité": "France"}
    assert {f["label"]: f["value"] for f in facts["org:otan"]["facts"]} == {"Création": "1949"}
    assert "company:disparue" not in facts and "company:sans-qid" not in facts


def test_gdp_is_added_and_failures_are_reported():
    base = {"country:france": {"facts": [], "iso2": "FR", "edges": []}}

    def bank(url, params=None):
        assert params["mrnev"] == 1
        return [{"page": 1}, [{"value": 3.05e12, "date": "2024"}]]

    facts, errors = with_gdp(base, bank)
    assert facts["country:france"]["facts"] == [{"label": "PIB", "value": "3 050 Md$ (2024)"}] and errors == []
    facts, errors = with_gdp(base, fake())
    assert facts == base and len(errors) == 1


def test_refresh_is_weekly_and_keeps_the_old_facts_when_wikidata_fails(tmp_path):
    calls = []
    facts, health = refresh_facts(tmp_path, CAT, NOW, fake(calls=calls))
    assert "country:france" in facts and health["ok"] is False          # la Banque mondiale échoue ici (faux réseau)
    n = len(calls)
    assert refresh_facts(tmp_path, CAT, NOW + timedelta(days=1), fake(calls=calls))[0] == facts and len(calls) == n

    def down(url, params=None):
        raise ConnectionError("Wikidata injoignable")

    kept, health = refresh_facts(tmp_path, CAT, NOW + timedelta(days=8), down)
    assert kept == facts and health["ok"] is False and "injoignable" in health["error"]
    assert load_facts(tmp_path) == facts
    stored = json.loads((tmp_path / "data" / "facts" / "entities.json").read_text("utf-8"))
    assert stored["qids"] == ["Q142", "Q3052772", "Q7184", "Q999"]


def test_no_wikidata_id_means_no_network_call(tmp_path):
    def never(url, params=None):
        raise AssertionError("aucun appel attendu")
    assert refresh_facts(tmp_path, {"company:x": {"type": "company"}}, NOW, never) == ({}, None)


def test_gdp_stops_after_the_first_failure_so_a_slow_bank_cannot_block_the_cycle():
    calls = []

    def slow(url, params=None):
        calls.append(url)
        raise TimeoutError("Banque mondiale trop lente")

    base = {f"country:{c}": {"facts": [], "iso2": c.upper(), "edges": []} for c in ("fr", "de", "it")}
    facts, errors = with_gdp(base, slow)
    assert len(calls) == 1 and facts == base and len(errors) == 1


def test_a_wikidata_error_body_keeps_the_previous_facts(tmp_path):
    facts, _ = refresh_facts(tmp_path, CAT, NOW, fake())

    def error_body(url, params=None):
        return {"error": {"code": "maxlag", "info": "surcharge"}}

    kept, health = refresh_facts(tmp_path, CAT, NOW + timedelta(days=8), error_body)
    assert kept == facts and health["ok"] is False and "maxlag" in health["error"]


def test_an_unexpected_entity_key_is_skipped_instead_of_failing():
    entities = {**ENTITIES, "Q142": {**ENTITIES["Q142"]}}
    def redirected(url, params=None):
        data = fake(entities)(url, params)
        data["entities"]["Q999999"] = item("Cible d'une redirection")
        return data
    facts = collect_facts(CAT, redirected)
    assert "country:france" in facts
