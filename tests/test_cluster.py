from datetime import timedelta

from engine.cluster import cluster
from engine.timeutil import iso
from tests.helpers import DOM, G, NOW, mk_event, mk_item

A = "OpenAI lance GPT-6 avec un contexte de deux millions de tokens"
B = "OpenAI dévoile GPT-6 : contexte de deux millions de tokens"
C = "GPT-6 d'OpenAI : deux millions de tokens de contexte, ce qui change"
OTHER = "Nvidia présente une nouvelle puce pour les centres de données"


def run(items, events=()):
    return cluster(items, list(events), DOM, G, NOW)


def test_many_articles_on_one_story_become_one_event():
    events, changed = run([mk_item("a", A), mk_item("b", B), mk_item("c", C)])
    assert len(events) == 1 and len(events[0]["items"]) == 3
    assert events[0]["entities"] == ["OpenAI"] and events[0]["kind"] == "model_release"
    assert changed == {events[0]["id"]}


def test_unrelated_stories_stay_separate():
    events, _ = run([mk_item("a", A), mk_item("b", OTHER)])
    assert len(events) == 2


def test_rerun_with_same_items_changes_nothing():
    items = [mk_item("a", A), mk_item("b", B)]
    first, _ = run(items)
    second, changed = run(items, first)
    assert changed == set() and second == first


def test_event_id_is_frozen_when_more_sources_join():
    first, _ = run([mk_item("a", A)])
    second, _ = run([mk_item("b", B)], first)
    assert len(second) == 1 and second[0]["id"] == first[0]["id"]


def test_new_origin_bumps_rev_but_same_origin_does_not():
    first, _ = run([mk_item("a", A), mk_item("b", B)])
    ev = first[0]
    same_origin = mk_item("d", "OpenAI lance GPT-6 et un contexte de deux millions de tokens", origin="origin-a")
    second, changed = run([same_origin], first)
    assert second[0]["rev"] == ev["rev"] and len(second[0]["items"]) == 3 and changed == {ev["id"]}
    new_origin = mk_item("e", "GPT-6 d'OpenAI : deux millions de tokens, le récit", origin="origin-new")
    third, _ = run([new_origin], second)
    assert third[0]["rev"] == ev["rev"] + 1


def test_better_tier_replaces_the_title():
    first, _ = run([mk_item("a", A, tier=3)])
    second, _ = run([mk_item("b", B, tier=1)], first)
    assert second[0]["title"] == B


def test_stale_event_is_not_reopened():
    old = mk_event([mk_item("a", A)], updated_at=iso(NOW - timedelta(hours=72)))
    events, _ = run([mk_item("b", B)], [old])
    assert len(events) == 2


def test_inputs_are_not_mutated():
    first, _ = run([mk_item("a", A)])
    snapshot = [dict(e, items=list(e["items"])) for e in first]
    run([mk_item("b", B)], first)
    assert first == snapshot


def test_no_new_items_returns_events_untouched():
    first, _ = run([mk_item("a", A)])
    again, changed = run([], first)
    assert again == first and changed == set()


def test_two_stories_sharing_only_big_names_do_not_merge():
    p = mk_item("p", "OpenAI et NVIDIA annoncent un partenariat sur les puces")
    q = mk_item("q", "OpenAI et NVIDIA visés par une plainte sur le droit d'auteur")
    events, _ = run([p, q])
    assert len(events) == 2
