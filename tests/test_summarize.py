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
