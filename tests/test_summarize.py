import json

from engine.summarize import KEYS, extractive, fingerprint, summarize
from tests.helpers import mk_event, mk_item

GOOD = {k: f"valeur {k}" for k in KEYS}


def ev(id, *titles):
    items = [mk_item(f"{id}{n}", t, snippet="Première phrase utile. Deuxième phrase.") for n, t in enumerate(titles)]
    return mk_event(items, id=id, reliability="confirmé")


def test_valid_llm_answer_is_used():
    e = ev("ev_1", "Titre un")
    results, errors = summarize([e], lambda prompt: json.dumps({"ev_1": GOOD}))
    assert results["ev_1"] == (GOOD, "llm") and errors == []


def test_fenced_json_is_accepted():
    e = ev("ev_1", "Titre un")
    fence = "`" * 3
    results, _ = summarize([e], lambda prompt: f"{fence}json\n{json.dumps({'ev_1': GOOD})}\n{fence}")
    assert results["ev_1"][1] == "llm"


def test_invalid_json_is_retried_once_then_falls_back_to_extractive():
    calls = []
    def bad(prompt):
        calls.append(1)
        return "pas du json"
    results, errors = summarize([ev("ev_1", "Titre un")], bad)
    assert len(calls) == 2 and results["ev_1"][1] == "extractif" and len(errors) == 1


def test_partial_answer_only_falls_back_for_the_missing_events():
    a, b = ev("ev_a", "Titre a"), ev("ev_b", "Titre b")
    partial = json.dumps({"ev_a": GOOD, "ev_b": {"quoi": "seulement ça"}})
    results, _ = summarize([a, b], lambda prompt: partial)
    assert results["ev_a"][1] == "llm" and results["ev_b"][1] == "extractif"


def test_quota_stops_further_calls_and_falls_back_everywhere():
    calls = []
    def quota(prompt):
        calls.append(1)
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    results, errors = summarize([ev("ev_a", "A"), ev("ev_b", "B")], quota, batch_size=1)
    assert len(calls) == 1 and errors == ["quota"]
    assert {m for _, m in results.values()} == {"extractif"}


def test_no_call_means_extractive_only_and_no_error():
    results, errors = summarize([ev("ev_1", "Titre un")], None)
    assert results["ev_1"][1] == "extractif" and errors == []


def test_extractive_summary_is_complete_and_deterministic():
    e = ev("ev_1", "Titre un", "Titre deux")
    s = extractive(e)
    assert set(s) == set(KEYS) and all(s[k].strip() for k in KEYS)
    assert s["quoi"] == "Première phrase utile."
    assert s["retenir"] == "Titre un"
    assert extractive(e) == s


def test_fingerprint_ignores_order_and_changes_with_new_items():
    a, b = mk_item("a", "x"), mk_item("b", "y")
    assert fingerprint(mk_event([a, b])) == fingerprint(mk_event([b, a]))
    assert fingerprint(mk_event([a])) != fingerprint(mk_event([a, b]))


def test_prompt_gives_the_model_each_source_publication_date():
    seen = []
    summarize([ev("ev_1", "Titre un")], lambda prompt: seen.append(prompt) or json.dumps({"ev_1": GOOD}))
    assert "2026-09-26" in seen[0]


from engine.summarize import LAYER_KEYS, PROFILES, has_advice

FIN_LAYERS = {k: [f"{k} un", f"{k} deux"] for k in LAYER_KEYS}


def fin_answer(**over):
    return {"ev_1": {**GOOD, "layers": FIN_LAYERS, **over}}


def test_finance_profile_returns_layers_next_to_the_summary():
    results, errors = summarize([ev("ev_1", "Titre un")], lambda p: json.dumps(fin_answer()), profile="finance")
    summary, mode = results["ev_1"]
    assert mode == "llm" and errors == []
    assert {k: summary[k] for k in GOOD} == GOOD
    assert set(summary["layers"]) == set(LAYER_KEYS)


def test_default_profile_ignores_layers_and_finance_prompt_forbids_advice():
    seen = []
    results, _ = summarize([ev("ev_1", "Titre un")], lambda p: seen.append(p) or json.dumps(fin_answer()))
    assert "layers" not in results["ev_1"][0]
    assert "layers" not in seen[0]
    seen.clear()
    summarize([ev("ev_1", "Titre un")], lambda p: seen.append(p) or json.dumps(fin_answer()), profile="finance")
    assert "layers" in seen[0] and "INTERDIT" in seen[0]


def test_layers_are_capped_cleaned_and_optional():
    long = {**FIN_LAYERS, "faits": [" a ", "", "b", "c", "d", "e", 5]}
    results, _ = summarize([ev("ev_1", "T")], lambda p: json.dumps(fin_answer(layers=long)), profile="finance")
    assert results["ev_1"][0]["layers"]["faits"] == ["a", "b", "c", "d"]
    no_layers = {"ev_1": GOOD}
    results, _ = summarize([ev("ev_1", "T")], lambda p: json.dumps(no_layers), profile="finance")
    assert results["ev_1"][1] == "llm" and "layers" not in results["ev_1"][0]
    broken = fin_answer(layers={"faits": "pas une liste"})
    results, _ = summarize([ev("ev_1", "T")], lambda p: json.dumps(broken), profile="finance")
    assert results["ev_1"][1] == "llm" and "layers" not in results["ev_1"][0]


def test_advice_in_the_analysis_makes_the_event_fall_back_to_extractive():
    bad = {**FIN_LAYERS, "interpretation": ["Nous recommandons d'acheter le titre avant la publication."]}
    results, _ = summarize([ev("ev_1", "T")], lambda p: json.dumps(fin_answer(layers=bad)), profile="finance")
    assert results["ev_1"][1] == "extractif" and "layers" not in results["ev_1"][0]


def test_advice_in_the_summary_text_is_rejected_too():
    results, _ = summarize([ev("ev_1", "T")], lambda p: json.dumps(fin_answer(retenir="Achetez maintenant.")), profile="finance")
    assert results["ev_1"][1] == "extractif"


def test_reported_facts_are_not_mistaken_for_advice():
    fine = {**FIN_LAYERS, "faits": ["Goldman relève sa recommandation à l'achat sur Nvidia.", "Apple va vendre ses parts."],
            "analyse": ["Un analyste cité par la presse juge le titre attractif."]}
    assert has_advice(GOOD, fine) is False
    assert has_advice({**GOOD, "pourquoi": "Apple va vendre ses parts dans la coentreprise."}, None) is False


def test_advice_patterns_are_detected():
    for text in ("Il faut acheter Nvidia.", "Vendez avant la clôture.", "Nous recommandons de renforcer.",
                 "Une opportunité d'achat.", "Un bon point d'entrée.", "You should buy the dip.", "We recommend selling."):
        assert has_advice({**GOOD, "pourquoi": text}, None), text


def test_profiles_are_declared():
    assert PROFILES["default"]["layers"] is False and PROFILES["finance"]["layers"] is True
